"""Add a document that is already in the data folder to the manifest (nothing is downloaded).

    python -m corpus_collector.register --file policy/<file>.pdf --source NITDA
        --url <original address> --title "..." [--company ...] [--date YYYY-MM-DD]

``sha256`` is the hash of the file's bytes; ``word_count`` is counted with PyMuPDF for PDFs.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import date
from pathlib import Path

from corpus_collector.config import DEFAULT_OUT
from corpus_collector.manifest import append_row, read_manifest


def count_words(path: Path) -> int | str:
    if path.suffix.lower() == ".pdf":
        try:
            import pymupdf
        except ImportError:
            return ""
        with pymupdf.open(path) as document:
            return sum(len(page.get_text().split()) for page in document)
    return len(path.read_text(encoding="utf-8", errors="replace").split())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m corpus_collector.register",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--file", required=True, help="path relative to the data folder")
    parser.add_argument("--source", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--company", default="")
    parser.add_argument("--location", default="")
    parser.add_argument("--date", default="", help="publication date, YYYY-MM-DD")
    parser.add_argument("--family", default="", help="role family (empty for non-adverts)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    path = args.out / args.file
    if not path.is_file():
        print(f"{path} does not exist.", file=sys.stderr)
        return 1
    relative = path.relative_to(args.out).as_posix()
    if any(row["file"] == relative for row in read_manifest(args.out)):
        print(f"{relative} is already in the manifest.")
        return 0
    append_row(
        args.out,
        {
            "file": relative,
            "source": args.source,
            "url": args.url,
            "title": args.title,
            "company": args.company,
            "location": args.location,
            "date_posted": args.date,
            "date_collected": date.today().isoformat(),
            "role_family": args.family,
            "word_count": count_words(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        },
    )
    print(f"Registered {relative}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
