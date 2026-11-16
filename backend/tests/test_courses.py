"""Splitting a NUC core into courses (SYNTHETIC text laid out like CCMAS course descriptions)."""

from __future__ import annotations

import numpy as np

from app.services.ingestion.courses import (
    MAX_COURSE_WORDS,
    CourseData,
    CourseExclusions,
    course_chunks,
    embed_courses,
    extract_courses,
)

CONTENT = "Learning outcomes and course contents about the subject of this course. " * 4


def test_headers_with_units_start_courses_and_record_their_page() -> None:
    pages = [
        "Programme overview. Students take the courses in the table below.\n"
        f"SEN 304: Software Testing & Quality Assurance (2 Units C: LH 15; PH 45)\n{CONTENT}",
        f"INS 202 Human-Computer Interface (HCI)  (2 Units C: LH 15; PH 45)\n{CONTENT}\n"
        "MTH 101 - Elementary Mathematics I (Algebra and Trigonometry) (3 Units C: LH 45)\n"
        f"{CONTENT}",
    ]

    courses = extract_courses(pages)

    assert [(c.code, c.title, c.units, c.page_number) for c in courses] == [
        ("SEN 304", "Software Testing & Quality Assurance", 2, 1),
        ("INS 202", "Human-Computer Interface (HCI)", 2, 2),
        ("MTH 101", "Elementary Mathematics I (Algebra and Trigonometry)", 3, 2),
    ]
    # A course's text runs from its header to the next header.
    assert courses[1].text.startswith("INS 202") and "MTH 101" not in courses[1].text


def test_mentions_without_units_are_not_courses_and_tiny_ones_are_dropped() -> None:
    pages = [
        "This builds on PHY 101 and CSC 201 covered earlier.\n"
        "CSC 299: Seminar (1 Unit C)\nShort.\n"
        f"CSC 301: Data Structures (3 Units C: LH 45)\n{CONTENT}"
    ]

    assert [c.code for c in extract_courses(pages, page_numbers=False)] == ["CSC 301"]
    assert extract_courses(pages, page_numbers=False)[0].page_number is None


def test_a_repeated_code_keeps_its_longest_description_and_text_is_capped() -> None:
    long_content = "word " * (MAX_COURSE_WORDS + 100)
    pages = [
        f"CSC 301: Data Structures (3 Units C)\n{CONTENT}\n"
        f"CSC 301: Data Structures (3 Units C)\n{long_content}"
    ]

    (course,) = extract_courses(pages)

    assert len(course.text.split()) == MAX_COURSE_WORDS


def test_exclusions_match_code_prefixes_and_title_keywords_case_insensitively() -> None:
    rules = CourseExclusions.from_setting(
        {"code_prefixes": ["gst"], "title_keywords": ["SIWES", "Final Year Project"]}
    )

    assert rules.excludes("GST 111", "Communication in English")
    assert rules.excludes("CSC 299", "Students Industrial Work Experience Scheme (siwes)")
    assert rules.excludes("SEN 498", "Final year project II")
    assert not rules.excludes("INS 401", "Project Management")
    assert not rules.excludes("ENT 312", "Venture Creation")
    assert not CourseExclusions.from_setting(None).excludes("GST 111", "Anything")


def test_course_embedding_is_the_normalised_mean_of_its_chunks() -> None:
    class CountingEncoder:
        model_name = "counting"

        def encode(self, texts: list[str]) -> np.ndarray:
            # First dimension: chunk length; second: constant.
            return np.asarray([[len(t.split()), 100.0] for t in texts], dtype=np.float32)

    text = "w " * 250  # two chunks: 200 and 50 words
    course = CourseData(code="CSC 301", title="T", units=3, page_number=1, text=text)

    assert [len(chunk.split()) for chunk in course_chunks(text)] == [200, 50]
    (vector,) = embed_courses([course], CountingEncoder())
    expected = np.array([125.0, 100.0]) / np.linalg.norm([125.0, 100.0])
    assert np.allclose(vector, expected)
    assert embed_courses([], CountingEncoder()).shape[0] == 0
