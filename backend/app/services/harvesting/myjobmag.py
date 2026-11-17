"""Polite, programme-profile-driven MyJobMag collector.

Adverts are found in two ways, in this order: the listing for each job title in the programme's
search terms (``/jobs-by-title/nurse``), which holds only adverts with that title, then the
listing of each chosen job field (``/jobs-by-field/medical``), which mixes many professions and
is filtered by title. Every advert is fetched once, respecting robots.txt with a pause between
requests.
"""

from __future__ import annotations

import html
import json
import random
import re
import time
import urllib.robotparser
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.myjobmag.com"

USER_AGENT = "SkillBridge academic curriculum research " "(University of Uyo)"

MIN_WORDS = 80

FIELD_RE = re.compile(r"^[a-z0-9-]+$")

NON_SLUG_RE = re.compile(r"[^a-z0-9]+")

EMAIL_RE = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.I,
)

PHONE_RE = re.compile(r"(?:\+?234|0)[\s-]?[789][01]\d" r"(?:[\s-]?\d){7}")

URL_RE = re.compile(
    r"https?://\S+|www\.\S+",
    re.I,
)

STOP_HEADINGS = (
    "method of application",
    "how to apply",
    "application method",
    "application procedure",
)


@dataclass(frozen=True)
class JobAdvert:
    title: str
    company: str
    url: str
    location: str
    date_posted: str
    text: str


@dataclass
class Collection:
    adverts: list[JobAdvert]
    examined: int = 0
    skipped: int = 0


def normalise(value: str) -> str:
    return " ".join(value.lower().replace("–", "-").replace("—", "-").split())


def title_matches(
    title: str,
    search_terms: list[str],
) -> bool:
    text = normalise(title)

    return any(normalise(term) in text for term in search_terms if normalise(term))


def title_slug(term: str) -> str:
    """The MyJobMag title-listing slug of a search term: "Registered Nurse" → "registered-nurse"."""
    return NON_SLUG_RE.sub("-", normalise(term)).strip("-")


def listing_urls(kind: str, slug: str, pages: int) -> list[str]:
    """Listing pages of a job title (``kind="title"``) or field, first page first."""
    base = f"{BASE_URL}/jobs-by-{kind}/{slug}"
    return [base if page == 1 else f"{base}/{page}" for page in range(1, pages + 1)]


def split_title(value: str) -> tuple[str, str]:
    title, separator, company = value.rpartition(" at ")

    if not separator:
        return value.strip(), ""

    return title.strip(), company.strip()


def _clean_text(value: str) -> str:
    soup = BeautifulSoup(
        html.unescape(value),
        "lxml",
    )

    for element in soup(
        [
            "script",
            "style",
            "button",
            "form",
            "nav",
            "footer",
        ]
    ):
        element.decompose()

    lines = []

    for line in soup.get_text("\n").splitlines():
        line = " ".join(line.split()).strip()

        if not line:
            continue

        lowered = line.lower().rstrip(":")

        if any(lowered.startswith(heading) for heading in STOP_HEADINGS):
            break

        line = EMAIL_RE.sub("[email removed]", line)
        line = PHONE_RE.sub("[phone removed]", line)
        line = URL_RE.sub("[url removed]", line)

        lines.append(line)

    return "\n".join(lines).strip()


def _posting_from_soup(
    soup: BeautifulSoup,
) -> dict:
    for script in soup.find_all(
        "script",
        type="application/ld+json",
    ):
        try:
            data = json.loads(
                script.string or "",
                strict=False,
            )
        except (json.JSONDecodeError, TypeError):
            continue

        queue = data if isinstance(data, list) else [data]

        while queue:
            candidate = queue.pop(0)

            if not isinstance(candidate, dict):
                continue

            if candidate.get("@type") == "JobPosting":
                return candidate

            graph = candidate.get("@graph")

            if isinstance(graph, list):
                queue.extend(graph)

    return {}


def parse_listing(page_html: str):
    soup = BeautifulSoup(page_html, "lxml")

    seen = set()

    links = [entry.select_one("h2 a[href]") for entry in soup.select("li.job-info")]
    if not links:
        # Other listing layouts: any titled link to an advert.
        links = [link for link in soup.select("a[href]") if link.get_text(strip=True)]

    for link in links:
        if link is None:
            continue

        href = str(link.get("href") or "").split("#")[0]
        if href.startswith(BASE_URL):
            href = href[len(BASE_URL) :]

        if not href.startswith("/job/"):
            continue

        if href in seen:
            continue

        seen.add(href)

        title, company = split_title(link.get_text(" ", strip=True))

        yield (
            BASE_URL + href,
            title,
            company,
        )


def parse_job_page(
    page_html: str,
    url: str,
) -> JobAdvert | None:
    soup = BeautifulSoup(page_html, "lxml")

    posting = _posting_from_soup(soup)

    heading = soup.find("h1")

    fallback_title = heading.get_text(" ", strip=True) if heading else ""

    title, fallback_company = split_title(fallback_title)

    title = html.unescape(str(posting.get("title") or title)).strip()

    organisation = posting.get("hiringOrganization") or {}

    company = fallback_company

    if isinstance(organisation, dict):
        company = html.unescape(str(organisation.get("name") or company)).strip()

    description = str(posting.get("description") or "")

    if not description:
        details = soup.select_one(".job-details")

        if details is not None:
            description = str(details)

    if not title or not description:
        return None

    cleaned = _clean_text(description)

    if len(cleaned.split()) < MIN_WORDS:
        return None

    location = ""

    raw_locations = posting.get("jobLocation") or []

    if not isinstance(raw_locations, list):
        raw_locations = [raw_locations]

    for raw_location in raw_locations:
        if not isinstance(raw_location, dict):
            continue

        address = raw_location.get("address") or {}

        if not isinstance(address, dict):
            continue

        parts = [
            address.get("addressLocality"),
            address.get("addressRegion"),
        ]

        location = ", ".join(str(part) for part in parts if part)

        if location:
            break

    date_posted = str(posting.get("datePosted") or "")[:10]

    body = "\n".join(
        part
        for part in (
            f"Job title: {title}",
            f"Employer: {company}" if company else "",
            f"Location: {location}" if location else "",
            "",
            cleaned,
        )
        if part != ""
    )

    return JobAdvert(
        title=title,
        company=company,
        url=url,
        location=location,
        date_posted=date_posted,
        text=body,
    )


class MyJobMagClient:
    def __init__(self):
        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": ("text/html,application/xhtml+xml"),
            }
        )

        robots_response = self.session.get(
            f"{BASE_URL}/robots.txt",
            timeout=20,
        )

        robots_response.raise_for_status()

        self.robots = urllib.robotparser.RobotFileParser()

        self.robots.parse(robots_response.text.splitlines())

    def get(self, url: str) -> str:
        if not self.robots.can_fetch(
            USER_AGENT,
            url,
        ):
            raise PermissionError(f"robots.txt does not allow {url}")

        time.sleep(random.uniform(2.0, 3.5))

        response = self.session.get(
            url,
            timeout=25,
        )

        if response.status_code == 404:
            raise LookupError(f"{url} does not exist")

        if response.status_code in {
            403,
            429,
        }:
            raise RuntimeError(
                "The job source asked SkillBridge " "to stop collecting temporarily."
            )

        response.raise_for_status()

        return response.text


def collect_jobs(
    search_terms: list[str],
    field_slugs: list[str],
    target_count: int,
    pages_per_field: int,
) -> Collection:
    """Collect up to ``target_count`` adverts whose title matches a search term.

    ``pages_per_field`` listing pages are read for each search term's title listing and then
    for each field; fields are optional. A title with no listing (404) is skipped.
    """
    terms = [normalise(term) for term in search_terms if normalise(term)]

    fields = [
        field.strip().lower() for field in field_slugs if FIELD_RE.fullmatch(field.strip().lower())
    ]

    if not terms:
        raise ValueError("Add at least one job-search term.")

    sources: list[tuple[str, str]] = []
    for kind, slugs in (("title", [title_slug(term) for term in terms]), ("field", fields)):
        for slug in slugs:
            if slug and (kind, slug) not in sources:
                sources.append((kind, slug))

    client = MyJobMagClient()

    result = Collection(adverts=[])

    seen_urls: set[str] = set()

    for kind, slug in sources:
        for listing_url in listing_urls(kind, slug, pages_per_field):
            if len(result.adverts) >= target_count:
                return result

            try:
                listing_html = client.get(listing_url)
            except LookupError:
                break  # no such title listing, or no more pages
            except PermissionError:
                result.skipped += 1
                continue

            found_any = False
            for (
                url,
                listed_title,
                _company,
            ) in parse_listing(listing_html):
                found_any = True
                if len(result.adverts) >= target_count:
                    return result

                result.examined += 1

                if url in seen_urls:
                    result.skipped += 1
                    continue

                seen_urls.add(url)

                if not title_matches(
                    listed_title,
                    terms,
                ):
                    result.skipped += 1
                    continue

                try:
                    job_html = client.get(url)
                except (PermissionError, LookupError):
                    result.skipped += 1
                    continue

                advert = parse_job_page(
                    job_html,
                    url,
                )

                if advert is None:
                    result.skipped += 1
                    continue

                if not title_matches(
                    advert.title,
                    terms,
                ):
                    result.skipped += 1
                    continue

                result.adverts.append(advert)

            if not found_any:
                break  # an empty page: the listing has ended

    return result
