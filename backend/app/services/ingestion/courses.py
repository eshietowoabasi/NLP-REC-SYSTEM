"""Splitting the NUC core curriculum into courses (for course-level overlap).

CCMAS documents describe each course under a header such as

    SEN 304: Software Testing & Quality Assurance (2 Units C: LH 15; PH 45)
    INS 202 Human-Computer Interface (HCI)  (2 Units C: LH 15; PH 45)
    MTH 101: Elementary Mathematics I (Algebra and Trigonometry) (2 Units C: LH 30)

followed by learning outcomes and course contents. A header is a course code (three capital
letters and three digits), an optional ":" or "-", a title, and the unit count in parentheses;
requiring the unit count keeps out course tables and passing mentions ("covered in PHY 101").
A course's text runs from its header to the next header (capped, so a programme table after
the last course of a section is not swallowed). Programmes share courses, so a code that
appears several times keeps its longest description.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from app.services.embeddings.encoder import Encoder

COURSE_HEADER = re.compile(
    r"\b(?P<prefix>[A-Z]{3})\s?(?P<number>\d{3})\s*[:\-–]?\s*"
    r"(?P<title>[^\n]{3,120}?)\s*\(\s*(?P<units>\d{1,2})\s*Units?\b",
)
MAX_COURSE_WORDS = 500
MIN_COURSE_WORDS = 15
CHUNK_WORDS = 200


@dataclass(frozen=True)
class CourseData:
    code: str  # "SEN 304"
    title: str
    units: int | None
    page_number: int | None
    text: str  # header + content, at most MAX_COURSE_WORDS words


@dataclass(frozen=True)
class CourseExclusions:
    """Courses left out of the overlap comparison (the ``nuc_course_exclusions`` setting).

    General studies, SIWES, project and seminar courses describe work experience or
    communication skills rather than subject content, so they attract generic themes.
    """

    code_prefixes: tuple[str, ...] = ()
    title_keywords: tuple[str, ...] = ()

    @classmethod
    def from_setting(cls, value: dict[str, list[str]] | None) -> CourseExclusions:
        value = value or {}
        return cls(
            code_prefixes=tuple(p.strip().upper() for p in value.get("code_prefixes", [])),
            title_keywords=tuple(k.strip().lower() for k in value.get("title_keywords", [])),
        )

    def excludes(self, code: str, title: str) -> bool:
        lowered = title.lower()
        return code.upper().startswith(self.code_prefixes) or any(
            keyword in lowered for keyword in self.title_keywords
        )


def _page_of(offset: int, page_starts: list[int]) -> int:
    page = 0
    for index, start in enumerate(page_starts):
        if start <= offset:
            page = index
        else:
            break
    return page + 1


def extract_courses(pages: list[str], page_numbers: bool = True) -> list[CourseData]:
    """The courses described in the (cleaned) pages of a NUC core document."""
    page_starts: list[int] = []
    parts: list[str] = []
    offset = 0
    for page in pages:
        page_starts.append(offset)
        parts.append(page)
        offset += len(page) + 2
    text = "\n\n".join(parts)
    headers = list(COURSE_HEADER.finditer(text))
    courses: dict[str, CourseData] = {}
    for index, match in enumerate(headers):
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        words = " ".join(text[match.start() : end].split()).split(" ")
        body = " ".join(words[:MAX_COURSE_WORDS])
        if len(words) < MIN_COURSE_WORDS:
            continue
        code = f"{match.group('prefix')} {match.group('number')}"
        course = CourseData(
            code=code,
            title=" ".join(match.group("title").split()).strip(" .:-–")[:255],
            units=int(match.group("units")),
            page_number=_page_of(match.start(), page_starts) if page_numbers else None,
            text=body,
        )
        previous = courses.get(code)
        if previous is None or len(course.text) > len(previous.text):
            courses[code] = course
    return sorted(courses.values(), key=lambda c: (c.page_number or 0, c.code))


def course_chunks(text: str, max_words: int = CHUNK_WORDS) -> list[str]:
    """Consecutive chunks of at most ``max_words`` words (SBERT reads ~256 word pieces)."""
    words = text.split()
    return [" ".join(words[i : i + max_words]) for i in range(0, len(words), max_words)]


def embed_courses(courses: list[CourseData], encoder: Encoder) -> NDArray[np.float32]:
    """One embedding per course: the L2-normalised mean of its chunks' embeddings."""
    if not courses:
        return np.zeros((0, 0), dtype=np.float32)
    chunks = [course_chunks(course.text) for course in courses]
    vectors = encoder.encode([chunk for course in chunks for chunk in course])
    result = []
    start = 0
    for course in chunks:
        mean = vectors[start : start + len(course)].mean(axis=0)
        start += len(course)
        norm = float(np.linalg.norm(mean))
        result.append(mean / norm if norm > 0 else mean)
    return np.asarray(result, dtype=np.float32)
