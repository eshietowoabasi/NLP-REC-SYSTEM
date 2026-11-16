"""Collector settings: sources, politeness limits and defaults."""

from __future__ import annotations

from pathlib import Path

USER_AGENT = "NLP-RS academic research (University of Uyo final-year project)"

DEFAULT_OUT = Path(r"C:\Users\Owoabasi\Documents\nlp-rs-data")

# Politeness
MIN_DELAY_SECONDS = 3.0
MAX_DELAY_SECONDS = 5.0
DEFAULT_MAX_REQUESTS = 150
REQUEST_TIMEOUT_SECONDS = 30

# Selection
DEFAULT_TARGET = 50
DEFAULT_PER_FAMILY = 8
MIN_WORDS = 150

# MyJobMag
MYJOBMAG_BASE = "https://www.myjobmag.com"
MYJOBMAG_FIELDS = (
    "information-technology",
    "research-data-analysis",
    "ux-design-architecture",
    "product-management",
    "engineering",
)
MYJOBMAG_LISTING = MYJOBMAG_BASE + "/jobs-by-field/{field}/{page}"
DEFAULT_PAGES_PER_FIELD = 3

# --only-family mode: read deeper, in the fields where that family's adverts appear.
FAMILY_MODE_PAGES = 15
FAMILY_MODE_GOAL = 6
FAMILY_FIELDS = {"cybersecurity": ("information-technology", "engineering")}

# Remotive public API (optional): at most one call per category per run, 4 runs a day.
REMOTIVE_API = "https://remotive.com/api/remote-jobs"
REMOTIVE_CATEGORIES = ("software-dev", "data", "devops", "qa", "design", "product")
REMOTIVE_MAX_RUNS_PER_DAY = 4

MANIFEST_COLUMNS = (
    "file",
    "source",
    "url",
    "title",
    "company",
    "location",
    "date_posted",
    "date_collected",
    "role_family",
    "word_count",
    "sha256",
)
