"""Cleaning of job adverts into the plain text stored in the corpus.

Kept: the title, the summary/description, responsibilities and requirements/skills sections.
Removed: "Method of Application" (and everything after it), application instructions, benefits
and salary, company boilerplate ("About us"), navigation, buttons, related jobs and footers,
and personal data - email addresses, phone numbers and URLs (NDPA 2023). No source or URL header
is written into the text.

Output format: one line per heading, paragraph or bullet item. Headings end with ":", every
other line ends with a full stop, matching the ingestion cleaning (bullet items become separate
sentences).
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

from bs4 import BeautifulSoup, NavigableString, Tag

# Sections that end the useful part of an advert: nothing after them is kept.
STOP_HEADINGS = re.compile(
    r"^(method of application|how to apply|application (method|process|procedure|instructions?)"
    r"|to apply|interested (and qualified )?candidates?|apply (now|here|via|through)"
    r"|application closing|closing date|deadline)",
    re.I,
)
# Sections that are skipped (their content is not curriculum-relevant).
SKIP_HEADINGS = re.compile(
    r"^(benefits?|perks|what we offer|we offer|remuneration|compensation|salary|pay\b"
    r"|package|why (join|work)|about (us|the company|our company)|who we are|our culture"
    r"|equal opportunit|disclaimer|note:?$|age limit|age requirement)",
    re.I,
)
# "Label - value" metadata lines (job codes, grades, salaries, reporting lines, locations).
METADATA_LINE = re.compile(
    r"^(job code|job id|job ref(erence)?|ref(erence)?( no\.?| number)?|grade|level"
    r"|(annual |monthly )?(salary|remuneration)|division|department|unit|directorate"
    r"|line supervisor|reports? to|supervising|supervises|duty station|location|work location"
    r"|contract( type| duration)?|job type|employment type|closing date|deadline)\s*[-–:]\s*\S",
    re.I,
)
# Page furniture that sometimes survives inside the job body.
JUNK_LINES = re.compile(
    r"^(apply( now| for this job)?|save job|share( this job)?|report (this )?job|send this job"
    r"|related jobs|similar jobs|view jobs at|click here|subscribe|job alert)\b",
    re.I,
)

EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
# Bare domains only for TLDs that cannot be technology names ("ASP.NET", "Socket.io" survive).
URL = re.compile(
    r"\b(?:https?://|www\.)\S+|\b[\w-]+(?:\.[\w-]+)*\.(?:com|org|gov\.ng|edu\.ng|com\.ng|ng)"
    r"(?:/\S*)?(?![\w.])",
    re.I,
)
# Nigerian and international phone numbers: +234 803 000 0000, 0803-000-0000, (01) 234 5678 ...
PHONE = re.compile(r"(?<!\w)(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{1,4}\)?[\s.-]?){2,4}\d{3,4}(?!\w)")
BULLET = re.compile(r"^\s*(?:[•●▪■◦○‣∙·►➢✓✔*\-–—]|\(?\d{1,2}[.)]|\(?[a-zA-Z][.)])\s+")
TERMINAL = (".", "!", "?", ":")
BLOCKS = ("p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "div", "br", "tr")


def remove_personal_data(text: str) -> str:
    text = EMAIL.sub(" ", text)
    text = URL.sub(" ", text)
    text = PHONE.sub(lambda m: m.group(0) if _looks_like_year_or_number(m.group(0)) else " ", text)
    return text


def _looks_like_year_or_number(value: str) -> bool:
    """Keep numbers that are not phone numbers: years and year ranges ("2020-2030"), counts.

    Nigerian numbers have 11 digits (0803 000 0000), 13 with +234; landlines with area code 9+.
    """
    digits = re.sub(r"\D", "", value)
    return len(digits) < 9


def _tidy(line: str) -> str:
    line = unicodedata.normalize("NFKC", line)
    line = remove_personal_data(line)
    line = " ".join(line.split())
    return line.strip(" -–—•*|:;,")


def _is_heading(line: str, is_list_item: bool) -> bool:
    words = line.split()
    return (
        not is_list_item and 0 < len(words) <= 8 and not line.rstrip(":").endswith((".", "!", "?"))
    )


def _finish(line: str, heading: bool) -> str:
    line = line.rstrip(" ;,")
    if heading:
        return line.rstrip(":.") + ":"
    return line if line.endswith(TERMINAL) and not line.endswith(":") else line.rstrip(":") + "."


def _lines_from_html(element: Tag) -> list[tuple[str, bool]]:
    """(text, is_list_item) for every block of text in document order."""
    lines: list[tuple[str, bool]] = []
    for node in element.find_all(["li", "p", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "div"]):
        if node.find(BLOCKS[:-2]):  # a container: its children are visited separately
            direct = "".join(
                child if isinstance(child, NavigableString) else "" for child in node.children
            ).strip()
            if direct:
                lines.append((direct, node.name == "li"))
            continue
        text = node.get_text(" ", strip=True)
        if text:
            lines.append((text, node.name == "li"))
    return lines


def _lines_from_text(text: str) -> list[tuple[str, bool]]:
    lines = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        is_item = bool(BULLET.match(raw))
        lines.append((BULLET.sub("", raw).strip(), is_item))
    return lines


def _assemble(title: str, lines: list[tuple[str, bool]]) -> str:
    out = [_finish(_tidy(title), heading=False)] if title else []
    skipping = False
    for raw, is_item in lines:
        line = _tidy(raw)
        if not line or JUNK_LINES.match(line) or METADATA_LINE.match(line):
            continue
        if STOP_HEADINGS.match(line):
            break
        heading = _is_heading(line, is_item)
        if heading:
            skipping = bool(SKIP_HEADINGS.match(line))
            if skipping:
                continue
        elif skipping:
            continue
        if heading and line.lower().rstrip(":") == title.lower():
            continue  # the title repeated as the first heading
        out.append(_finish(line, heading))
    # Drop a trailing heading with no content under it.
    while out and out[-1].endswith(":"):
        out.pop()
    return "\n".join(out)


def clean_job_html(html_fragment: str | Tag, title: str) -> str:
    """Clean the job-description HTML (e.g. MyJobMag's ``.job-details``) into corpus text."""
    element = (
        html_fragment if isinstance(html_fragment, Tag) else BeautifulSoup(html_fragment, "lxml")
    )
    for tag in element.find_all(["script", "style", "noscript", "svg", "button", "form", "img"]):
        tag.decompose()
    return _assemble(title, _lines_from_html(element))


def clean_job_text(text: str, title: str = "") -> str:
    """Clean a pasted advert (plain text) the same way."""
    return _assemble(title, _lines_from_text(text))


def word_count(text: str) -> int:
    return len(text.split())


def normalised_for_hash(text: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", text.lower()).split())


def text_sha256(text: str) -> str:
    return hashlib.sha256(normalised_for_hash(text).encode("utf-8")).hexdigest()


def slugify(text: str, max_length: int = 60) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", text).lower()).strip("-")
    return slug[:max_length].rstrip("-") or "untitled"
