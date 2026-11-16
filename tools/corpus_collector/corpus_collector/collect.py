"""The collection run: walk the sources, filter, de-duplicate and (unless dry-run) save.

Usage (from tools/corpus_collector/):

    python -m corpus_collector --dry-run            # list what would be collected
    python -m corpus_collector                      # collect and save
    python -m corpus_collector --include-remote --target 60 --per-family 10
"""

from __future__ import annotations

import argparse
import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from corpus_collector.classify import FAMILIES, classify_title, is_denied
from corpus_collector.clean import text_sha256, word_count
from corpus_collector.config import (
    DEFAULT_MAX_REQUESTS,
    DEFAULT_OUT,
    DEFAULT_PAGES_PER_FIELD,
    DEFAULT_PER_FAMILY,
    DEFAULT_TARGET,
    FAMILY_FIELDS,
    FAMILY_MODE_GOAL,
    FAMILY_MODE_PAGES,
    MIN_WORDS,
    MYJOBMAG_FIELDS,
    MYJOBMAG_LISTING,
    REMOTIVE_CATEGORIES,
)
from corpus_collector.dedupe import Deduper
from corpus_collector.http import (
    DisallowedUrl,
    PoliteClient,
    StopCollecting,
    use_system_certificates,
)
from corpus_collector.manifest import advert_filename, read_manifest, save_advert
from corpus_collector.sources import myjobmag, remotive
from corpus_collector.sources.common import JobAd

logger = logging.getLogger("corpus_collector")


@dataclass
class Selection:
    """The adverts chosen in this run and why others were skipped."""

    target: int
    per_family: int
    existing_per_family: Counter[str] = field(default_factory=Counter)
    chosen: list[tuple[JobAd, str]] = field(default_factory=list)
    skipped: Counter[str] = field(default_factory=Counter)
    # Per-family caps that differ from ``per_family`` (``--cap product_agile=4``).
    caps: dict[str, int] = field(default_factory=dict)
    # Collect for this family only (``--only-family``); other titles are skipped.
    only_family: str | None = None

    def family_full(self, family: str) -> bool:
        taken = self.existing_per_family[family] + sum(1 for _, f in self.chosen if f == family)
        return taken >= self.caps.get(family, self.per_family)

    @property
    def done(self) -> bool:
        return len(self.chosen) >= self.target


def consider(ad: JobAd, family: str, selection: Selection, deduper: Deduper) -> bool:
    """Apply the word-count and duplicate-text filters; record the advert if it passes."""
    words = word_count(ad.text)
    if words < MIN_WORDS:
        selection.skipped[f"under {MIN_WORDS} words"] += 1
        return False
    sha = text_sha256(ad.text)
    reason = deduper.reason(ad.title, ad.company, sha, ad.slug if ad.source == "MyJobMag" else None)
    if reason:
        selection.skipped[reason] += 1
        return False
    deduper.add(ad.title, ad.company, sha, ad.slug if ad.source == "MyJobMag" else None)
    selection.chosen.append((ad, family))
    return True


def screen_title(
    title: str, company: str, slug: str | None, selection: Selection, deduper: Deduper
) -> str | None:
    """The family of a listed job worth fetching, or None (reason recorded)."""
    family = classify_title(title)
    if family is None:
        selection.skipped["not computing" if is_denied(title) else "no role family"] += 1
        return None
    if selection.only_family and family != selection.only_family:
        selection.skipped["other family"] += 1
        return None
    if selection.family_full(family):
        selection.skipped[f"family full ({family})"] += 1
        return None
    reason = deduper.reason(title, company, slug=slug)
    if reason:
        selection.skipped[reason] += 1
        return None
    return family


def _collect_listing(
    client: PoliteClient, selection: Selection, deduper: Deduper, listing_html: str
) -> None:
    """Screen every job on a MyJobMag listing page and fetch the promising ones."""
    for item in myjobmag.parse_listing(listing_html):
        if selection.done:
            return
        family = screen_title(item.title, item.company, item.slug, selection, deduper)
        if family is None:
            continue
        try:
            status, job_html = client.get(item.url)
        except DisallowedUrl:
            selection.skipped["disallowed by robots.txt"] += 1
            continue
        if status != 200:
            selection.skipped[f"job HTTP {status}"] += 1
            continue
        ad = myjobmag.parse_job(job_html, item.url, item.slug)
        if ad is None:
            selection.skipped["no job description"] += 1
            continue
        ad_family = classify_title(ad.title) or family
        if selection.only_family and ad_family != selection.only_family:
            selection.skipped["other family"] += 1
            continue
        consider(ad, ad_family, selection, deduper)


def _get_listing(client: PoliteClient, selection: Selection, url: str) -> str | None:
    try:
        status, body = client.get(url)
    except DisallowedUrl:
        selection.skipped["disallowed by robots.txt"] += 1
        return None
    if status != 200:
        selection.skipped[f"listing HTTP {status}"] += 1
        return None
    return body


def collect_myjobmag(
    client: PoliteClient,
    selection: Selection,
    deduper: Deduper,
    fields: tuple[str, ...],
    pages: int,
) -> None:
    for page in range(1, pages + 1):
        for job_field in fields:
            if selection.done:
                return
            body = _get_listing(
                client, selection, MYJOBMAG_LISTING.format(field=job_field, page=page)
            )
            if body is not None:
                _collect_listing(client, selection, deduper, body)


def collect_jobtitle_pages(
    client: PoliteClient, selection: Selection, deduper: Deduper, max_pages: int
) -> None:
    """Visit MyJobMag job-title pages whose title belongs to ``selection.only_family``.

    The sitemap lists every job title the site has used (tens of thousands); only titles that
    the classifier puts in the requested family are visited, newest first (sitemap order), and
    at most ``max_pages`` of them: pages of expired titles show unrelated recent jobs, so the
    rest of the request budget is kept for the field listings.
    """
    sitemap = _get_listing(client, selection, myjobmag.JOBTITLE_SITEMAP)
    if sitemap is None:
        return
    visited = 0
    for url, title in myjobmag.jobtitle_pages(sitemap):
        if selection.done or visited >= max_pages:
            return
        if classify_title(title) != selection.only_family:
            continue
        visited += 1
        body = _get_listing(client, selection, url)
        if body is not None:
            _collect_listing(client, selection, deduper, body)


def collect_remotive(
    client: PoliteClient, selection: Selection, deduper: Deduper, cache_dir: Path
) -> None:
    remotive.check_and_record_run(cache_dir)
    for category in REMOTIVE_CATEGORIES:  # one call per category per run
        if selection.done:
            return
        status, body = client.get_api(remotive.category_url(category))
        if status != 200:
            selection.skipped[f"Remotive HTTP {status}"] += 1
            continue
        for ad in remotive.parse_jobs(body):
            if selection.done:
                return
            family = screen_title(ad.title, ad.company, None, selection, deduper)
            if family is not None:
                consider(ad, family, selection, deduper)


def print_summary(selection: Selection, client: PoliteClient, dry_run: bool, out: Path) -> None:
    verb = "Would save" if dry_run else "Saved"
    print(f"\n{verb} {len(selection.chosen)} adverts (target {selection.target}):\n")
    print(f"{'#':>3}  {'family':<19} {'words':>5}  {'posted':<10}  title — company")
    for number, (ad, family) in enumerate(selection.chosen, start=1):
        print(
            f"{number:>3}  {family:<19} {word_count(ad.text):>5}  {ad.date_posted or '—':<10}  "
            f"{ad.title} — {ad.company or '?'} [{ad.source}]"
        )
    print("\nPer family (this run + already in the manifest):")
    counts = Counter(family for _, family in selection.chosen)
    for family in sorted(set(counts) | set(selection.existing_per_family)):
        print(
            f"  {family:<19} {counts[family]:>3} new  "
            f"{selection.existing_per_family[family]:>3} existing"
        )
    print("\nSkipped:")
    for reason, count in selection.skipped.most_common():
        print(f"  {reason:<32} {count:>4}")
    print(
        f"\nRequests: {client.requests_made} network (limit {client.max_requests}), "
        f"{client.cache_hits} from the cache.  Output folder: {out}"
    )


def parse_cap(value: str) -> tuple[str, int]:
    """``product_agile=4`` -> ("product_agile", 4)."""
    family, sep, number = value.partition("=")
    if not sep or family not in FAMILIES or not number.isdigit():
        raise argparse.ArgumentTypeError(
            f"use FAMILY=N with a family from: {', '.join(sorted(FAMILIES))}"
        )
    return family, int(number)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m corpus_collector",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="data folder")
    parser.add_argument("--dry-run", action="store_true", help="list, do not save adverts")
    parser.add_argument("--target", type=int, default=DEFAULT_TARGET)
    parser.add_argument("--per-family", type=int, default=DEFAULT_PER_FAMILY)
    parser.add_argument(
        "--cap",
        action="append",
        default=[],
        type=parse_cap,
        metavar="FAMILY=N",
        help="a different cap for one family, e.g. --cap product_agile=4 (repeatable)",
    )
    parser.add_argument("--max-requests", type=int, default=DEFAULT_MAX_REQUESTS)
    parser.add_argument(
        "--pages",
        type=int,
        help=f"listing pages per MyJobMag field (default {DEFAULT_PAGES_PER_FIELD}, "
        f"or {FAMILY_MODE_PAGES} with --only-family)",
    )
    parser.add_argument("--fields", nargs="+", help="MyJobMag fields to read")
    parser.add_argument(
        "--only-family",
        choices=sorted(FAMILIES),
        help="collect for one family only: job-title pages first, then deeper listings; "
        "ignores --target and stops at --family-goal",
    )
    parser.add_argument(
        "--family-goal",
        type=int,
        default=FAMILY_MODE_GOAL,
        help="with --only-family: total adverts wanted in that family, including those "
        f"already in the manifest (default {FAMILY_MODE_GOAL})",
    )
    parser.add_argument(
        "--max-title-pages",
        type=int,
        default=40,
        help="with --only-family: job-title pages to visit at most (default 40)",
    )
    parser.add_argument("--include-remote", action="store_true", help="also use the Remotive API")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING, format="%(message)s"
    )

    use_system_certificates()
    cache_dir = args.out / ".cache"
    client = PoliteClient(cache_dir, args.max_requests)
    manifest = read_manifest(args.out)
    deduper = Deduper.from_manifest(manifest)
    existing = Counter(row["role_family"] for row in manifest if row.get("role_family"))
    selection = Selection(args.target, args.per_family, existing, caps=dict(args.cap))
    if args.only_family:
        family = args.only_family
        selection.only_family = family
        selection.caps[family] = args.family_goal
        selection.target = max(args.family_goal - existing[family], 0)
        pages = args.pages or FAMILY_MODE_PAGES
        fields = tuple(args.fields or FAMILY_FIELDS.get(family, MYJOBMAG_FIELDS))
        print(
            f"Collecting {family} only: {existing[family]} in the manifest, goal "
            f"{args.family_goal}, so up to {selection.target} new adverts."
        )
    else:
        pages = args.pages or DEFAULT_PAGES_PER_FIELD
        fields = tuple(args.fields or MYJOBMAG_FIELDS)
    try:
        if args.only_family and not selection.done:
            collect_jobtitle_pages(client, selection, deduper, args.max_title_pages)
        if not selection.done:
            collect_myjobmag(client, selection, deduper, fields, pages)
        if args.include_remote and not selection.done:
            collect_remotive(client, selection, deduper, cache_dir)
    except StopCollecting as stop:
        print(f"\nStopped early: {stop}")
    except remotive.RemotiveLimitReached as limit:
        print(f"\nRemotive skipped: {limit}")

    if not args.dry_run:
        for ad, family in selection.chosen:
            save_advert(args.out, ad, family)
    else:
        for ad, family in selection.chosen:
            logger.info("would write job_market/%s", advert_filename(ad, family))
    print_summary(selection, client, args.dry_run, args.out)
    if args.only_family:
        total = existing[args.only_family] + len(selection.chosen)
        print(f"\n{args.only_family}: {total} adverts in total after this run.")
        if total < BACKUP_THRESHOLD:
            print(
                f"Fewer than {BACKUP_THRESHOLD}: MyJobMag has run out; a backup source is needed."
            )
    return 0


BACKUP_THRESHOLD = 4
