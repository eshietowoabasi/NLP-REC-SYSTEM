"""MyJobMag: listing pages by job field and individual job pages.

Listing pages (``/jobs-by-field/<field>/<page>``) show each job's title ("Title at Company"),
link (``/job/<slug>``) and date. Job pages hold the description in ``.job-details`` and a
schema.org ``JobPosting`` (JSON-LD) with the title, company, location and ``datePosted``.
"""

from __future__ import annotations

import html
import json
import re
from datetime import datetime

from bs4 import BeautifulSoup

from corpus_collector.clean import clean_job_html
from corpus_collector.config import MYJOBMAG_BASE
from corpus_collector.sources.common import JobAd, ListingItem

SOURCE = "MyJobMag"
_JOB_PATH = re.compile(r"^/job/([a-z0-9-]+)/?$")


JOBTITLE_SITEMAP = MYJOBMAG_BASE + "/sitemap-jobtitle.xml"
_JOBTITLE_URL = re.compile(r"^https://www\.myjobmag\.com/jobs-by-title/([a-z0-9-]+)$")


def jobtitle_pages(sitemap_xml: str) -> list[tuple[str, str]]:
    """(url, title) of every job-title page in the sitemap, in sitemap order.

    The title is the slug with hyphens as spaces ("soc-analyst-ii" -> "soc analyst ii"),
    good enough for the role-family classifier.
    """
    pages = []
    for url in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sitemap_xml):
        match = _JOBTITLE_URL.match(url)
        if match:
            pages.append((url, match.group(1).replace("-", " ")))
    return pages


def split_title(text: str) -> tuple[str, str]:
    """ "Devops Manager at Aloft LLC" -> ("Devops Manager", "Aloft LLC")."""
    title, sep, company = text.rpartition(" at ")
    return (title.strip(), company.strip()) if sep else (text.strip(), "")


def parse_listing(page_html: str) -> list[ListingItem]:
    """Jobs on a listing page, in page order, without duplicates."""
    soup = BeautifulSoup(page_html, "lxml")
    items: list[ListingItem] = []
    seen: set[str] = set()
    for entry in soup.select("li.job-info"):
        link = entry.select_one("h2 a[href]")
        if link is None:
            continue
        match = _JOB_PATH.match(link["href"].split("#")[0])
        if match is None or match.group(1) in seen:
            continue
        seen.add(match.group(1))
        title, company = split_title(link.get_text(" ", strip=True))
        date = entry.select_one("#job-date, .job-date")
        items.append(
            ListingItem(
                url=MYJOBMAG_BASE + link["href"].split("#")[0],
                slug=match.group(1),
                title=title,
                company=company,
                date_text=date.get_text(" ", strip=True) if date else "",
            )
        )
    return items


def _job_posting(soup: BeautifulSoup) -> dict:
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "", strict=False)
        except json.JSONDecodeError:
            continue
        for candidate in data if isinstance(data, list) else [data]:
            if isinstance(candidate, dict) and candidate.get("@type") == "JobPosting":
                return candidate
    return {}


def _iso_date(value: str) -> str:
    if not value:
        return ""
    for parse in (
        lambda v: datetime.fromisoformat(v.replace("Z", "+00:00")),
        lambda v: datetime.strptime(v, "%b %d, %Y"),
    ):
        try:
            return parse(value.strip()).date().isoformat()
        except ValueError:
            continue
    return ""


def _location(posting: dict) -> str:
    locations = posting.get("jobLocation") or []
    for location in locations if isinstance(locations, list) else [locations]:
        address = location.get("address", {}) if isinstance(location, dict) else {}
        parts = [address.get("addressLocality"), address.get("addressRegion")]
        text = ", ".join(html.unescape(p) for p in parts if p)
        if text:
            return text
    return ""


def parse_job(page_html: str, url: str, slug: str) -> JobAd | None:
    """The cleaned advert of a job page, or None if the page has no job description."""
    soup = BeautifulSoup(page_html, "lxml")
    posting = _job_posting(soup)
    heading = soup.find("h1")
    title, company = split_title(heading.get_text(" ", strip=True)) if heading else ("", "")
    title = html.unescape(posting.get("title") or title)
    organisation = posting.get("hiringOrganization") or {}
    if isinstance(organisation, dict) and organisation.get("name"):
        company = html.unescape(organisation["name"])
    details = soup.select_one(".job-details")
    if details is None and posting.get("description"):
        details = BeautifulSoup(html.unescape(posting["description"]), "lxml")
    if details is None or not title:
        return None
    posted = _iso_date(posting.get("datePosted", ""))
    if not posted:
        node = soup.select_one("#posted-date")
        posted = _iso_date(node.get_text(" ", strip=True).replace("Posted:", "")) if node else ""
    return JobAd(
        source=SOURCE,
        url=url,
        slug=slug,
        title=title,
        company=company,
        location=_location(posting),
        date_posted=posted,
        text=clean_job_html(details, title),
    )
