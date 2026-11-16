"""Remotive public API (optional, ``--include-remote``).

Remotive's terms allow use of the API with attribution and a link back to the job, so every
advert keeps ``source=Remotive`` and the job URL in the manifest. They also ask clients not to
call it too often: this module makes at most one call per category per run and refuses to run
more than four times in 24 hours (recorded in ``<out>/.cache/remotive_runs.json``).
"""

from __future__ import annotations

import html
import json
import time
from pathlib import Path
from urllib.parse import urlsplit

from corpus_collector.clean import clean_job_html
from corpus_collector.config import REMOTIVE_API, REMOTIVE_MAX_RUNS_PER_DAY
from corpus_collector.sources.common import JobAd

SOURCE = "Remotive"
DAY_SECONDS = 24 * 3600


class RemotiveLimitReached(Exception):
    """Four runs have already been made in the last 24 hours."""


def check_and_record_run(cache_dir: Path, now: float | None = None) -> None:
    """Record this run, or raise if the daily limit has been reached."""
    now = time.time() if now is None else now
    log = cache_dir / "remotive_runs.json"
    runs = json.loads(log.read_text("utf-8")) if log.exists() else []
    recent = [t for t in runs if now - t < DAY_SECONDS]
    if len(recent) >= REMOTIVE_MAX_RUNS_PER_DAY:
        raise RemotiveLimitReached(
            f"Remotive was already called {len(recent)} times in the last 24 hours."
        )
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps(recent + [now]), "utf-8")


def category_url(category: str) -> str:
    # The API takes the category as a query parameter; this is the documented public API,
    # not a crawled page, so the no-query-string crawling rule does not apply (see README).
    return f"{REMOTIVE_API}?category={category}"


def parse_jobs(payload: str) -> list[JobAd]:
    data = json.loads(payload)
    ads = []
    for job in data.get("jobs", []):
        url = job.get("url", "")
        title = html.unescape(job.get("title", "")).strip()
        if not url or not title:
            continue
        ads.append(
            JobAd(
                source=SOURCE,
                url=url,
                slug=urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1],
                title=title,
                company=html.unescape(job.get("company_name", "")).strip(),
                location=job.get("candidate_required_location", "") or "Remote",
                date_posted=(job.get("publication_date") or "")[:10],
                text=clean_job_html(job.get("description", ""), title),
            )
        )
    return ads
