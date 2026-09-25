"""The corpus manifest (``<out>/manifest.csv``) and saving of adverts."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from corpus_collector.clean import slugify, text_sha256, word_count
from corpus_collector.config import MANIFEST_COLUMNS
from corpus_collector.sources.common import JobAd


def read_manifest(out: Path) -> list[dict[str, str]]:
    path = out / "manifest.csv"
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def append_row(out: Path, row: dict[str, str | int]) -> None:
    path = out / "manifest.csv"
    new = not path.exists()
    out.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS)
        if new:
            writer.writeheader()
        writer.writerow({column: row.get(column, "") for column in MANIFEST_COLUMNS})


def advert_filename(ad: JobAd, family: str) -> str:
    """``myjobmag_<family>_<title-slug>_<date_posted>.txt`` (prefix = the source)."""
    posted = ad.date_posted or "undated"
    return f"{slugify(ad.source, 20)}_{family}_{slugify(ad.title)}_{posted}.txt"


def unique_path(folder: Path, name: str) -> Path:
    path = folder / name
    counter = 2
    while path.exists():
        path = folder / f"{Path(name).stem}-{counter}.txt"
        counter += 1
    return path


def save_advert(out: Path, ad: JobAd, family: str, today: date | None = None) -> Path:
    """Write the advert under ``<out>/job_market/`` and add its manifest row."""
    folder = out / "job_market"
    folder.mkdir(parents=True, exist_ok=True)
    path = unique_path(folder, advert_filename(ad, family))
    path.write_text(ad.text + "\n", encoding="utf-8")
    append_row(
        out,
        {
            "file": path.relative_to(out).as_posix(),
            "source": ad.source,
            "url": ad.url,
            "title": ad.title,
            "company": ad.company,
            "location": ad.location,
            "date_posted": ad.date_posted,
            "date_collected": (today or date.today()).isoformat(),
            "role_family": family,
            "word_count": word_count(ad.text),
            "sha256": text_sha256(ad.text),
        },
    )
    return path
