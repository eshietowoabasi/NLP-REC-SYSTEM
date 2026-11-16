"""Shared data types of the sources."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListingItem:
    """A job seen on a listing page (before its own page is fetched)."""

    url: str
    slug: str
    title: str
    company: str
    date_text: str


@dataclass(frozen=True)
class JobAd:
    """A cleaned advert ready to be saved."""

    source: str
    url: str
    slug: str
    title: str
    company: str
    location: str
    date_posted: str  # ISO date (YYYY-MM-DD) or "" when unknown
    text: str
