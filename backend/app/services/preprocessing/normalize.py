"""Unicode normalisation and noise/formatting cleanup (spec §8.1)."""
import re
import unicodedata

_CHAR_MAP = str.maketrans({
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"',
    "\u2013": "-", "\u2014": " - ", "\u2212": "-",
    "\u2022": " ", "\u25cf": " ", "\u25aa": " ", "\uf0b7": " ",  # bullets
    "\u00ad": "",  # soft hyphen
    "\u200b": "", "\ufeff": "",  # zero-width space, BOM
})

# "SECTION 4: MEMBERSHIP ......... 7" / "PREAMBLE<TAB>5": table-of-contents entries.
_TOC_LINE_RE = re.compile(r"^.{2,200}?(\t+|\s*\.{3,}\s*|\s{3,})\d{1,4}\s*$")
_URL_RE = re.compile(r"\b(?:https?://|www\.)\S+", re.I)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_HYPHEN_BREAK_RE = re.compile(r"(\w)-\n(\w)")


def normalize_unicode(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)  # also expands ligatures such as "ﬁ"
    text = text.translate(_CHAR_MAP)
    return _CONTROL_RE.sub("", text)


def is_toc_line(line: str) -> bool:
    return bool(_TOC_LINE_RE.match(line))


def clean_block(block: str) -> str:
    """Clean one paragraph/table row. Returns "" if the block is pure noise."""
    text = normalize_unicode(block)
    text = _HYPHEN_BREAK_RE.sub(r"\1\2", text)
    text = "\n".join(line for line in text.split("\n") if not is_toc_line(line))
    text = _URL_RE.sub(" ", text)
    text = _EMAIL_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Drop leftovers with no letters at all (page numbers, separators, bare list markers).
    return text if re.search(r"[^\W\d_]", text) else ""


def split_blocks(text: str) -> list[str]:
    return [b for b in re.split(r"\n\s*\n", text.replace("\r\n", "\n")) if b.strip()]


_CONTENTS_HEADING_RE = re.compile(r"^(table of contents|contents|arrangement of (sections|chapters))$", re.I)
_MAX_TOC_BLOCKS = 400


def drop_contents_listing(blocks: list[str]) -> list[str]:
    """Remove a table of contents that has no page numbers.

    After a "Contents"/"Arrangement of Sections" heading, the first entry (e.g.
    "PREAMBLE") reappears where the body starts; everything in between is the listing.
    """
    for i, block in enumerate(blocks[:-1]):
        if not _CONTENTS_HEADING_RE.match(block.strip()):
            continue
        first_entry = blocks[i + 1].strip().lower()
        if len(first_entry) > 120:
            return blocks
        for j in range(i + 2, min(len(blocks), i + 2 + _MAX_TOC_BLOCKS)):
            if blocks[j].strip().lower() == first_entry:
                return blocks[:i] + blocks[j:]
        # Heading with no recognisable listing (entries already removed as TOC lines).
        return blocks[:i] + blocks[i + 1:]
    return blocks


def clean_blocks(blocks: list[str]) -> list[str]:
    cleaned = [b for b in (clean_block(b) for b in blocks) if b]
    return drop_contents_listing(cleaned)
