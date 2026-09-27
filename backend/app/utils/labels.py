"""Plain-language labels shared by the API and the reports."""

from __future__ import annotations

from datetime import date

# What each category of document is called in a sentence ("a job advert").
DOCUMENT_TYPES = {
    "job_market": ("job advert", "job adverts"),
    "policy": ("policy document", "policy documents"),
    "institutional": ("university document", "university documents"),
    "academic": ("academic paper", "academic papers"),
    "nuc_core": ("NUC core curriculum", "NUC core curricula"),
}


def document_type(category: str, plural: bool = False) -> str:
    key = getattr(category, "value", category)
    singular, many = DOCUMENT_TYPES.get(str(key), ("document", "documents"))
    return many if plural else singular


def month_year(value: date | None) -> str | None:
    return value.strftime("%b %Y") if value else None


def document_label(
    title: str, category: str, source: str | None = None, published_on: date | None = None
) -> str:
    """ "Senior QA Engineer – Hydrogen, job advert (MyJobMag, Sep 2026)"."""
    details = ", ".join(part for part in (source, month_year(published_on)) if part)
    label = f"{title}, {document_type(category)}"
    return f"{label} ({details})" if details else label
