"""Light cleaning of extracted text.

This is the branch of preprocessing that keeps the original wording and casing (used for NER,
SBERT, BERTopic and evidence display). It only removes layout noise:

1. Unicode NFKC normalisation (ligatures, full-width characters, non-breaking spaces).
2. Words hyphenated across line breaks are rejoined ("manage-\\nment" → "management").
3. Headers/footers repeated on more than half of the pages are removed (documents with 3+ pages).
4. Page-number lines, URLs and email addresses are removed.
5. Bullet markers are removed; bullet items and short headings get a full stop so that they
   become separate sentences instead of merging into one run-on sentence.
6. Lines are joined into paragraphs and whitespace is collapsed.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

HEADER_FOOTER_MIN_PAGES = 3
# Only short lines among the first/last few lines of a page can be headers or footers, so
# repeated body text is never removed.
HEADER_FOOTER_LINES = 2
HEADER_FOOTER_MAX_WORDS = 12

_HYPHEN_BREAK = re.compile(r"(\w)-[ \t]*\n[ \t]*([a-z])")
_PAGE_NUMBER = re.compile(
    r"^\s*[-–—]?\s*(page\s*)?\d{1,4}(\s*(of|/)\s*\d{1,4})?\s*[-–—]?\s*$", re.I
)
_URL = re.compile(r"\b(?:https?://|www\.)\S+", re.I)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
_BULLET = re.compile(r"^\s*(?:[•●▪■◦○‣∙·►➢✓✔*\-–—]|\(?\d{1,2}[.)]|\(?[a-zA-Z][.)])\s+")
_TERMINAL = (".", "!", "?", ":", ";")
_SPACES = re.compile(r"[ \t ]+")


def _line_key(line: str) -> str:
    """Comparison key for header/footer detection: digits ignored ("Page 3" == "Page 4")."""
    return re.sub(r"\d+", "#", _SPACES.sub(" ", line.strip().lower()))


def remove_headers_footers(pages: list[str]) -> list[str]:
    """Drop lines that repeat at the top or bottom of more than half of the pages."""
    if len(pages) < HEADER_FOOTER_MIN_PAGES:
        return pages
    page_lines = [page.splitlines() for page in pages]
    counts: Counter[str] = Counter()
    for lines in page_lines:
        non_empty = [line for line in lines if line.strip()]
        edges = non_empty[:HEADER_FOOTER_LINES] + non_empty[-HEADER_FOOTER_LINES:]
        counts.update(
            {_line_key(line) for line in edges if len(line.split()) <= HEADER_FOOTER_MAX_WORDS}
        )
    repeated = {key for key, count in counts.items() if count > len(pages) / 2}
    if not repeated:
        return pages
    return ["\n".join(ln for ln in lines if _line_key(ln) not in repeated) for lines in page_lines]


def _is_heading(line: str, next_line: str | None) -> bool:
    """A short capitalised line without punctuation, followed by another capitalised line."""
    words = line.split()
    return (
        0 < len(words) <= 6
        and line[0].isupper()
        and not line.endswith(_TERMINAL)
        and next_line is not None
        and next_line[:1].isupper()
    )


def _clean_page(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = _HYPHEN_BREAK.sub(r"\1\2", text)
    text = _URL.sub(" ", text)
    text = _EMAIL.sub(" ", text)

    lines = [_SPACES.sub(" ", line).strip() for line in text.splitlines()]
    paragraphs: list[str] = []
    current: list[str] = []
    for index, line in enumerate(lines):
        if not line or _PAGE_NUMBER.match(line):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        is_bullet = bool(_BULLET.match(line))
        if is_bullet:
            line = _BULLET.sub("", line)
            if not line:
                continue
        next_line = next((candidate for candidate in lines[index + 1 :] if candidate), None)
        if next_line is not None:
            next_line = _BULLET.sub("", next_line)
        if (is_bullet or _is_heading(line, next_line)) and not line.endswith(_TERMINAL):
            line += "."
        current.append(line)
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)


def clean_pages(pages: list[str]) -> list[str]:
    """Apply light cleaning to every page (see the module docstring for the steps)."""
    normalised = [unicodedata.normalize("NFKC", page) for page in pages]
    return [_clean_page(page) for page in remove_headers_footers(normalised)]


def count_words(text: str) -> int:
    return len(text.split())
