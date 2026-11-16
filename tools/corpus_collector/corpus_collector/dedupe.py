"""De-duplication of adverts across runs.

An advert is a duplicate when (1) the same normalised title and company is already saved,
(2) its normalised text has the same SHA-256, or (3) its MyJobMag slug differs from a saved one
only by a ``-N`` suffix (the site re-posts the same job as ``devops-manager-2``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_SUFFIX = re.compile(r"-\d+$")


def normalise_key(title: str, company: str) -> str:
    text = f"{title}|{company}".lower()
    return " ".join(re.sub(r"[^\w|]+", " ", text).split())


def slug_base(slug: str) -> str:
    return _SUFFIX.sub("", slug)


@dataclass
class Deduper:
    keys: set[str] = field(default_factory=set)
    hashes: set[str] = field(default_factory=set)
    slugs: set[str] = field(default_factory=set)

    @classmethod
    def from_manifest(cls, rows: list[dict[str, str]]) -> Deduper:
        deduper = cls()
        for row in rows:
            deduper.add(row["title"], row["company"], row["sha256"], _slug_from_url(row["url"]))
        return deduper

    def reason(
        self, title: str, company: str, sha: str | None = None, slug: str | None = None
    ) -> str | None:
        """Why this advert is a duplicate, or None. ``sha`` is unknown before fetching."""
        if slug and slug_base(slug) in self.slugs:
            return "duplicate slug"
        if normalise_key(title, company) in self.keys:
            return "duplicate title+company"
        if sha and sha in self.hashes:
            return "duplicate text"
        return None

    def add(self, title: str, company: str, sha: str, slug: str | None) -> None:
        self.keys.add(normalise_key(title, company))
        if sha:
            self.hashes.add(sha)
        if slug:
            self.slugs.add(slug_base(slug))


def _slug_from_url(url: str) -> str | None:
    match = re.search(r"myjobmag\.com/job/([a-z0-9-]+)", url or "")
    return match.group(1) if match else None
