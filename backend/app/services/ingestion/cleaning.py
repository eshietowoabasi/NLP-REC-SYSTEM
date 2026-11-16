"""Light cleaning of extracted text.

This is the branch of preprocessing that keeps the original wording and casing (used for NER,
SBERT, BERTopic and evidence display). It only removes layout noise:

1. Unicode NFKC normalisation (ligatures, full-width characters, non-breaking spaces).
2. Words hyphenated across line breaks are rejoined ("manage-\\nment" → "management").
3. Headers/footers repeated on more than half of the pages are removed (documents with 3+ pages).
4. Page-number lines, table-of-contents dot leaders, URLs and email addresses are removed.
5. Bullet markers are removed. A bullet item ends (and gets a full stop) where the next bullet
   starts, at a paragraph boundary, or before a line that starts with a capital letter unless
   the item's line ends with a connector word; so items, including ones wrapped over several
   lines, become separate sentences instead of one run-on sentence.
6. Short headings get a full stop. A line is only a heading at a paragraph boundary (start of
   the page, after a page-number line, or after a line ending a sentence) and never when it
   ends with a connector word such as "and" or "of": in justified PDF text a line break
   often falls mid-sentence ("... Communications and Digital" / "Economy is ...").
7. Lines are joined into paragraphs and whitespace is collapsed.
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
# A bullet marker followed by the item text, or alone on its line (the item text follows).
_BULLET = re.compile(r"^\s*(?:[•●▪■◦○‣∙·►➢✓✔*\-–—]|\(?\d{1,2}[.)]|\(?[a-zA-Z][.)])(?:\s+|$)")
_TERMINAL = (".", "!", "?", ":", ";")
# Table-of-contents leaders and the page number after them: "Foreword........7".
_DOT_LEADER = re.compile(r"(?:[ \t]*\.){4,}[ \t]*\d{0,4}")
# A line ending with one of these continues on the next line; it is never a heading.
_CONNECTORS = frozenset(
    {"a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of", "on", "or", "the"}
    | {"to", "with", "&", ",", "-", "–", "(", "/"}
)
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


def _ends_with_connector(line: str) -> bool:
    last = line.rsplit(None, 1)[-1].lower() if line.split() else ""
    return last in _CONNECTORS or line[-1:] in _CONNECTORS


def _is_heading(line: str, next_line: str | None, at_boundary: bool) -> bool:
    """A short capitalised line at a paragraph boundary, followed by a capitalised line."""
    words = line.split()
    return (
        at_boundary
        and 0 < len(words) <= 6
        and line[0].isupper()
        and not line.endswith(_TERMINAL)
        and not _ends_with_connector(line)
        and next_line is not None
        and next_line[:1].isupper()
    )


def _continues(previous: str, line: str) -> bool:
    """Whether ``line`` continues a bullet item wrapped from ``previous`` (not a new text).

    It does when ``previous`` ends with a connector word, when ``line`` starts in lower case,
    or when ``previous`` has only one or two words (justified PDF text often breaks list items
    one word per line: "Guidelines" / "for" / "Nigerian" / "Content").
    """
    return _ends_with_connector(previous) or not line[:1].isupper() or len(previous.split()) <= 2


def _terminate(lines: list[str]) -> None:
    """End the last line of ``lines`` with a full stop unless it already ends a sentence."""
    if lines and not lines[-1].endswith(_TERMINAL):
        lines[-1] += "."


def _clean_page(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = _HYPHEN_BREAK.sub(r"\1\2", text)
    text = _URL.sub(" ", text)
    text = _EMAIL.sub(" ", text)
    text = _DOT_LEADER.sub(" ", text)

    lines = [_SPACES.sub(" ", line).strip() for line in text.splitlines()]
    paragraphs: list[str] = []
    current: list[str] = []
    in_bullet = False  # the last line belongs to a bullet item that has not ended yet
    at_boundary = True  # the next line starts a new sentence or paragraph
    item_follows = False  # a bullet marker stood alone on the previous line

    def close_paragraph() -> None:
        nonlocal current, in_bullet
        if in_bullet:
            _terminate(current)
        if current:
            paragraphs.append(" ".join(current))
        current, in_bullet = [], False

    for index, line in enumerate(lines):
        if not line or _PAGE_NUMBER.match(line):
            close_paragraph()
            at_boundary = True
            continue
        if _BULLET.match(line):
            if in_bullet:
                _terminate(current)  # the previous item ends where this one starts
            in_bullet, at_boundary = True, True
            line = _BULLET.sub("", line)
            if not line:  # the marker was alone on its line; the item text follows
                item_follows = True
                continue
        elif item_follows:
            pass  # first line of the item whose marker stood alone on the previous line
        elif in_bullet and current and not _continues(current[-1], line):
            _terminate(current)  # the item ended on the previous line
            in_bullet, at_boundary = False, True
        next_line = next((candidate for candidate in lines[index + 1 :] if candidate), None)
        if next_line is not None:
            next_line = _BULLET.sub("", next_line)
        if _is_heading(line, next_line, at_boundary) and not in_bullet:
            line += "."
        current.append(line)
        at_boundary = line.endswith(_TERMINAL)
        item_follows = False
    close_paragraph()
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)


def clean_pages(pages: list[str]) -> list[str]:
    """Apply light cleaning to every page (see the module docstring for the steps)."""
    normalised = [unicodedata.normalize("NFKC", page) for page in pages]
    return [_clean_page(page) for page in remove_headers_footers(normalised)]


def count_words(text: str) -> int:
    return len(text.split())
