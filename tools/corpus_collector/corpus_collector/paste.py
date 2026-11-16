"""Save a manually copied advert (Jobberman, LinkedIn, ...) with the same cleaning and naming.

Those sites are never scraped (Jobberman's robots.txt disallows job pages; LinkedIn's user
agreement forbids scraping). Open the advert in the browser, copy its text, then:

    python -m corpus_collector.paste --source jobberman --url <advert URL>
        [--title "..."] [--company "..."] [--location "..."] [--date 2026-09-20]
        [--family software_dev] [--file advert.txt] [--out <data folder>]

The text is read from the clipboard (or ``--file``). The title defaults to the first line.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from corpus_collector.classify import FAMILIES, classify_title
from corpus_collector.clean import clean_job_text, text_sha256, word_count
from corpus_collector.config import DEFAULT_OUT, MIN_WORDS
from corpus_collector.dedupe import Deduper
from corpus_collector.manifest import read_manifest, save_advert
from corpus_collector.sources.common import JobAd


def read_clipboard() -> str:
    import tkinter

    root = tkinter.Tk()
    root.withdraw()
    try:
        return root.clipboard_get()
    finally:
        root.destroy()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m corpus_collector.paste",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--source", required=True, help="e.g. jobberman, linkedin")
    parser.add_argument("--url", required=True, help="the advert's address (kept in the manifest)")
    parser.add_argument("--title")
    parser.add_argument("--company", default="")
    parser.add_argument("--location", default="")
    parser.add_argument("--date", default="", help="date posted, YYYY-MM-DD")
    parser.add_argument("--family", choices=sorted(FAMILIES), help="override the classifier")
    parser.add_argument("--file", type=Path, help="read the advert from a file instead")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    raw = args.file.read_text(encoding="utf-8") if args.file else read_clipboard()
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines:
        print("The clipboard is empty.", file=sys.stderr)
        return 1
    title = args.title or lines[0]
    body = "\n".join(lines[1:] if not args.title and lines[0] == title else lines)
    text = clean_job_text(body, title)
    family = args.family or classify_title(title)
    if family is None:
        print(f"'{title}' is not a computing role; use --family to override.", file=sys.stderr)
        return 1
    if word_count(text) < MIN_WORDS:
        print(
            f"Only {word_count(text)} words after cleaning (minimum {MIN_WORDS}).", file=sys.stderr
        )
        return 1
    deduper = Deduper.from_manifest(read_manifest(args.out))
    reason = deduper.reason(title, args.company, text_sha256(text))
    if reason:
        print(f"Not saved: {reason}.", file=sys.stderr)
        return 1
    ad = JobAd(args.source, args.url, "", title, args.company, args.location, args.date, text)
    path = save_advert(args.out, ad, family, date.today())
    print(f"Saved {path} ({word_count(text)} words, {family}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
