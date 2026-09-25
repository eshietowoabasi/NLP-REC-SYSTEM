"""Unit tests of the cleaner, classifier, de-duplication, robots rules and parsers.

All fixtures are SYNTHETIC (invented adverts with the structure of the real pages).
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pytest

from corpus_collector.classify import classify_title
from corpus_collector.clean import clean_job_text, remove_personal_data, text_sha256, word_count
from corpus_collector.collect import Selection, consider, parse_cap, screen_title
from corpus_collector.dedupe import Deduper, slug_base
from corpus_collector.http import DisallowedUrl, PoliteClient, StopCollecting
from corpus_collector.manifest import read_manifest, save_advert
from corpus_collector.robots import RobotsRules
from corpus_collector.sources import myjobmag, remotive
from corpus_collector.sources.common import JobAd

FIXTURES = Path(__file__).parent / "fixtures"
MYJOBMAG_ROBOTS = """User-agent: *
Disallow: /search/jobs?*
Disallow: /*?
Disallow: /apply-now/
Disallow: /job-application/
Disallow: /&page=
"""


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ------------------------------------------------------------------------- cleaner


@pytest.fixture
def cleaned() -> str:
    ad = myjobmag.parse_job(fixture("job_page.html"), "https://www.myjobmag.com/job/x", "x")
    assert ad is not None
    return ad.text


def test_cleaner_keeps_the_advert_sections_as_lines(cleaned: str) -> None:
    lines = cleaned.splitlines()
    assert lines[0] == "Backend Engineer."
    assert "Job Summary:" in lines
    assert "Key Responsibilities:" in lines
    assert "Requirements:" in lines
    assert "Design, build and maintain RESTful APIs in Python and Django." in lines
    assert "Write unit and integration tests and review pull requests." in lines
    assert all(line.endswith((".", ":")) for line in lines)


def test_cleaner_drops_application_benefits_page_furniture_and_personal_data(cleaned: str) -> None:
    lowered = cleaned.lower()
    for removed in (
        "method of application",
        "send your cv",
        "benefits",
        "health insurance",
        "apply now",
        "related jobs",
        "copyright",
        "home",
    ):
        assert removed not in lowered
    assert "@" not in cleaned and "https" not in cleaned and "803" not in cleaned
    assert cleaned.count("Backend Engineer") == 1  # title not repeated as a heading
    assert "ASP.NET or Node.js" in cleaned  # technology names survive URL removal


def test_metadata_lines_and_age_limits_are_dropped() -> None:
    raw = (
        "Job Code - 20003709\nGrade - P3/P4\nAnnual Salary - UA 40,000\n"
        "Line Supervisor - Principal Officer\nRole Overview\nManage the IT help desk.\n"
        "Age Limit\nCandidates must be under 50.\nCompetencies\nKnowledge of networks."
    )

    text = clean_job_text(raw, "IT Officer")

    assert text.splitlines() == [
        "IT Officer.",
        "Role Overview:",
        "Manage the IT help desk.",
        "Competencies:",
        "Knowledge of networks.",
    ]


def test_personal_data_removal_keeps_years_and_numbers() -> None:
    text = remove_personal_data("Call 0803-123-4567 or +234 1 234 5678; policy 2020-2030, 3 years.")
    assert "0803" not in text and "234 5678" not in text
    assert "2020-2030" in text and "3 years" in text


def test_pasted_text_gets_the_same_cleaning() -> None:
    raw = (
        "Summary\nWe need an analyst.\n• Build dashboards in Power BI\n- Write SQL\n"
        "How to apply\nEmail us"
    )
    text = clean_job_text(raw, "Data Analyst")
    assert text.splitlines() == [
        "Data Analyst.",
        "Summary:",
        "We need an analyst.",
        "Build dashboards in Power BI.",
        "Write SQL.",
    ]


# ------------------------------------------------------------------------ classifier


@pytest.mark.parametrize(
    ("title", "family"),
    [
        ("Senior Backend Engineer (Python)", "software_dev"),
        ("Flutter Developer", "software_dev"),
        ("Data Analyst", "data_ai"),
        ("Machine Learning Engineer", "data_ai"),
        ("Information Security Officer", "cybersecurity"),
        ("SOC Analyst", "cybersecurity"),
        ("DevOps Engineer", "cloud_devops"),
        ("Site Reliability Engineer", "cloud_devops"),
        ("Network Engineer", "networking_systems"),
        ("IT Support Officer", "it_support"),
        ("Database Administrator", "database"),
        ("QA Engineer", "qa"),
        ("UI/UX Designer", "ui_ux"),
        ("Product Manager", "product_agile"),
        ("Scrum Master", "product_agile"),
        ("Tech Support Officer", "it_support"),
        ("Information Technology Lead", "it_support"),
        ("Volunteer - IT & Digital Support", "it_support"),
        ("Senior IT Software Developer", "software_dev"),
        ("Unix Engineer", "networking_systems"),
        ("Project Execution Engineer (Unix & Database)", "database"),
        ("Solution Architect", "software_dev"),
        ("IT Sales Executive", None),
        ("Delivery Driver", None),
        ("Business Developer", None),
        ("Real Estate Developer", None),
        ("Security Officer", None),
        ("Accountant", None),
        ("Civil Engineer", None),
        ("Customer Service Representative", None),
    ],
)
def test_titles_are_classified_into_role_families(title: str, family: str | None) -> None:
    assert classify_title(title) == family


# --------------------------------------------------------------------- de-duplication


def test_duplicates_by_title_company_text_and_slug_suffix() -> None:
    deduper = Deduper()
    deduper.add("Backend Engineer", "Example Fintech Ltd", "abc", "backend-engineer-example")

    assert deduper.reason("backend  engineer", "EXAMPLE FINTECH LTD.") == "duplicate title+company"
    assert deduper.reason("Other", "Other", sha="abc") == "duplicate text"
    assert deduper.reason("Other", "Other", slug="backend-engineer-example-2") == "duplicate slug"
    assert deduper.reason("Other", "Other", sha="xyz", slug="another-job") is None
    assert slug_base("devops-manager-12") == "devops-manager"


def test_text_hash_ignores_case_punctuation_and_spacing() -> None:
    assert text_sha256("Build APIs, write tests.") == text_sha256("build   apis write tests")


def test_deduper_is_rebuilt_from_the_manifest(tmp_path: Path) -> None:
    ad = JobAd(
        "MyJobMag",
        "https://www.myjobmag.com/job/qa-engineer-acme",
        "qa-engineer-acme",
        "QA Engineer",
        "Acme",
        "Lagos",
        "2026-09-20",
        "Test software. " * 80,
    )
    path = save_advert(tmp_path, ad, "qa")

    rows = read_manifest(tmp_path)
    deduper = Deduper.from_manifest(rows)

    assert path.name == "myjobmag_qa_qa-engineer_2026-09-20.txt"
    assert rows[0]["file"] == "job_market/myjobmag_qa_qa-engineer_2026-09-20.txt"
    assert rows[0]["word_count"] == "160"
    assert deduper.reason("Other", "Other", slug="qa-engineer-acme-3") == "duplicate slug"
    assert "myjobmag.com" not in path.read_text(encoding="utf-8")  # no source header


def test_selection_filters_short_adverts_and_caps_families() -> None:
    selection = Selection(target=10, per_family=1, existing_per_family=Counter())
    deduper = Deduper()
    long_ad = JobAd("MyJobMag", "u1", "a", "QA Engineer", "A", "", "", "Test software. " * 80)
    short_ad = JobAd("MyJobMag", "u2", "b", "QA Analyst", "B", "", "", "Too short.")

    assert consider(short_ad, "qa", selection, deduper) is False
    assert consider(long_ad, "qa", selection, deduper) is True
    assert screen_title("QA Tester", "C", None, selection, deduper) is None
    assert selection.skipped == Counter({"under 150 words": 1, "family full (qa)": 1})
    assert word_count(long_ad.text) == 160


def test_one_family_can_have_its_own_cap() -> None:
    selection = Selection(target=10, per_family=8, caps=dict([parse_cap("product_agile=1")]))
    deduper = Deduper()
    ad = JobAd("MyJobMag", "u", "pm", "Product Manager", "A", "", "", "Own the roadmap. " * 60)

    assert consider(ad, "product_agile", selection, deduper)
    assert selection.family_full("product_agile")
    assert not selection.family_full("qa")
    with pytest.raises(argparse.ArgumentTypeError):
        parse_cap("marketing=3")


# ----------------------------------------------------------------- robots and HTTP


def test_robots_wildcards_that_robotparser_ignores_are_obeyed() -> None:
    rules = RobotsRules.parse(MYJOBMAG_ROBOTS, "NLP-RS academic research")

    assert rules.allowed("https://www.myjobmag.com/jobs-by-field/engineering/2")
    assert rules.allowed("https://www.myjobmag.com/job/devops-manager")
    assert not rules.allowed("https://www.myjobmag.com/apply-now/123")
    assert not rules.allowed("https://www.myjobmag.com/search/jobs?q=python")
    assert not rules.allowed("https://www.myjobmag.com/jobs?page=2")
    # Even with query strings allowed (APIs), Disallow: /*? still applies on this site.
    assert not rules.allowed("https://www.myjobmag.com/jobs?page=2", allow_query=True)


class FakeResponse:
    def __init__(self, status: int, text: str) -> None:
        self.status_code, self.text = status, text


class FakeSession:
    def __init__(self, pages: dict[str, tuple[int, str]]) -> None:
        self.pages, self.calls, self.headers = pages, [], {}

    def get(self, url: str, timeout: int) -> FakeResponse:
        self.calls.append(url)
        return FakeResponse(*self.pages.get(url, (404, "")))


def client_for(tmp_path: Path, pages: dict[str, tuple[int, str]], max_requests: int = 10):
    session = FakeSession(pages)
    sleeps: list[float] = []
    client = PoliteClient(tmp_path, max_requests, sleep=sleeps.append, session=session)
    return client, session, sleeps


def test_client_checks_robots_waits_and_caches(tmp_path: Path) -> None:
    site = "https://www.myjobmag.com"
    client, session, sleeps = client_for(
        tmp_path, {f"{site}/robots.txt": (200, MYJOBMAG_ROBOTS), f"{site}/job/a": (200, "A")}
    )

    assert client.get(f"{site}/job/a") == (200, "A")
    assert client.get(f"{site}/job/a") == (200, "A")  # from the cache
    with pytest.raises(DisallowedUrl):
        client.get(f"{site}/apply-now/1")

    assert session.calls == [f"{site}/robots.txt", f"{site}/job/a"]
    assert all(3 <= pause <= 5 for pause in sleeps) and len(sleeps) == 2
    assert client.cache_hits == 1


def test_client_stops_on_429_and_at_the_request_budget(tmp_path: Path) -> None:
    site = "https://www.myjobmag.com"
    client, _, _ = client_for(
        tmp_path,
        {f"{site}/robots.txt": (200, ""), f"{site}/job/a": (429, ""), f"{site}/job/b": (200, "")},
        max_requests=2,
    )
    with pytest.raises(StopCollecting, match="429"):
        client.get(f"{site}/job/a")
    with pytest.raises(StopCollecting, match="budget"):
        client.get(f"{site}/job/b")


# --------------------------------------------------------------------------- parsers


def test_listing_parser_reads_titles_companies_and_slugs_once() -> None:
    items = myjobmag.parse_listing(fixture("listing_page.html"))

    assert [(i.slug, i.title, i.company) for i in items] == [
        ("backend-engineer-example-fintech", "Backend Engineer", "Example Fintech Ltd"),
        ("delivery-driver-acme", "Delivery Driver", "Acme Logistics"),
    ]
    assert items[0].url == "https://www.myjobmag.com/job/backend-engineer-example-fintech"


def test_job_parser_uses_the_json_ld_metadata() -> None:
    ad = myjobmag.parse_job(fixture("job_page.html"), "https://www.myjobmag.com/job/x", "x")

    assert (ad.title, ad.company, ad.location, ad.date_posted) == (
        "Backend Engineer",
        "Example Fintech Ltd",
        "Lagos, Lagos",
        "2026-09-20",
    )


def test_remotive_payload_and_daily_run_limit(tmp_path: Path) -> None:
    payload = json.dumps(
        {
            "jobs": [
                {
                    "url": "https://remotive.com/remote-jobs/software-dev/python-dev-123",
                    "title": "Python Developer",
                    "company_name": "Remote Co",
                    "publication_date": "2026-09-18T08:00:00",
                    "candidate_required_location": "Worldwide",
                    "description": "<p>Summary</p><ul><li>Build APIs</li></ul>",
                }
            ]
        }
    )

    (ad,) = remotive.parse_jobs(payload)
    assert (ad.source, ad.slug, ad.date_posted, ad.location) == (
        "Remotive",
        "python-dev-123",
        "2026-09-18",
        "Worldwide",
    )
    assert ad.text.splitlines() == ["Python Developer.", "Summary:", "Build APIs."]
    for _ in range(4):
        remotive.check_and_record_run(tmp_path, now=1000.0)
    with pytest.raises(remotive.RemotiveLimitReached):
        remotive.check_and_record_run(tmp_path, now=2000.0)
    remotive.check_and_record_run(tmp_path, now=1000.0 + 25 * 3600)  # a day later: allowed
