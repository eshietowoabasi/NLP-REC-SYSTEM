"""Report content: turns a session's stored results into a format-neutral document.

``build_report`` is pure (no database, no rendering). It returns a :class:`ReportDocument`
made of sections, each a list of simple blocks (paragraphs, key/value lists, bullet lists and
tables). The PDF renderer (HTML + WeasyPrint) and the DOCX renderer (python-docx) both draw
this same structure, so the two formats always contain the same information.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from app.utils.labels import document_label, document_type

# Section keys in report order, with their headings. Planners choose any non-empty subset.
REPORT_SECTIONS: dict[str, str] = {
    "corpus_summary": "Documents analysed",
    "nlp_findings": "What the documents talk about",
    "overlap": "Comparison with the NUC core",
    "recommendations": "Recommended topics",
    "decisions": "Decisions",
    "proposed_courses": "Proposed courses",
}

STATUS_LABELS = {
    "Potential Duplicate": "May already be in NUC core",
    "No Significant Overlap": "Not in NUC core",
}
DECISION_LABELS = {"accepted": "Accepted", "rejected": "Rejected", "flagged": "Discuss later"}

TOP_TERMS = 20
TOP_SKILLS = 20
EXCERPT_CHARS = 300

DISCLAIMER = (
    "NLP-RS suggests topics to help the department decide. The suggestions and scores are "
    "worked out automatically from the documents; the decisions are made by the department's "
    "planners and the relevant university bodies."
)


# ---------------------------------------------------------------------------- blocks


@dataclass(frozen=True)
class Paragraph:
    text: str
    muted: bool = False


@dataclass(frozen=True)
class KeyValues:
    items: list[tuple[str, str]]


@dataclass(frozen=True)
class BulletList:
    items: list[str]


@dataclass(frozen=True)
class Table:
    columns: list[str]
    rows: list[list[str]]
    # Indexes of right-aligned (numeric) columns.
    numeric: tuple[int, ...] = ()
    caption: str | None = None
    # Relative column widths (renderers may ignore them).
    widths: tuple[int, ...] | None = None


@dataclass(frozen=True)
class Subheading:
    text: str


Block = Paragraph | KeyValues | BulletList | Table | Subheading


@dataclass
class Section:
    key: str
    title: str
    blocks: list[Block] = field(default_factory=list)


@dataclass
class ReportDocument:
    title: str
    subtitle: str
    meta: list[tuple[str, str]]
    sections: list[Section]
    disclaimer: str = DISCLAIMER


# ------------------------------------------------------------------------ input data


@dataclass(frozen=True)
class DocumentRow:
    title: str
    category: str
    file_type: str
    page_count: int | None
    word_count: int | None
    passage_count: int
    source: str | None = None
    published_on: date | None = None

    @property
    def label(self) -> str:
        return document_label(self.title, self.category, self.source, self.published_on)


@dataclass(frozen=True)
class RecommendationRow:
    rank: int
    title: str
    description: str
    composite: float
    ner: float
    topic: float
    novelty: float
    max_similarity: float
    overlap_status: str
    skills: list[str]
    decision: str | None
    notes: str | None
    decided_by: str | None
    decided_at: datetime | None


@dataclass(frozen=True)
class MappingRow:
    course_code: str
    course_title: str
    credit_units: int
    prerequisites: list[str]
    learning_outcomes: list[str]
    recommendation_rank: int
    recommendation_title: str


@dataclass(frozen=True)
class ReportData:
    """Everything a report can show, loaded from the database by the report job."""

    session_name: str
    completed_at: datetime | None
    generated_at: datetime
    generated_by: str
    nuc_core_version: str | None
    parameters: dict[str, Any]
    documents: list[DocumentRow]
    keywords: dict[str, Any]
    entities: dict[str, Any]
    topics: dict[str, Any]
    similarity: dict[str, Any]
    recommendations: list[RecommendationRow]
    mappings: list[MappingRow]
    credit_unit_allowance: int | None


# --------------------------------------------------------------------------- helpers


def points(value: float) -> int:
    """A 0-1 score as whole points out of 100."""
    return round(min(max(value, 0.0), 1.0) * 100)


def score_level(value: float) -> str:
    """High (70+), Medium (40-69) or Low (below 40), as on screen."""
    score = points(value)
    return "High" if score >= 70 else "Medium" if score >= 40 else "Low"


def fmt_points(value: float) -> str:
    """0.8492 -> "85/100"."""
    return f"{points(value)}/100"


def fmt_level(value: float) -> str:
    """0.9 -> "90 High"."""
    return f"{points(value)} {score_level(value)}"


def fmt_percent(value: float) -> str:
    """A similarity or threshold: 0.576 -> "58%"."""
    return f"{points(value)}%"


def fmt_weight(value: float) -> str:
    return f"counts for {round(value * 100)}%"


def fmt_number(value: int | None) -> str:
    return "—" if value is None else f"{value:,}"


def fmt_datetime(value: datetime | None) -> str:
    return "—" if value is None else value.strftime("%d %b %Y, %H:%M UTC")


def excerpt(text: str, limit: int = EXCERPT_CHARS) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def plural(count: int, word: str, plural_form: str | None = None) -> str:
    return f"{count:,} {word if count == 1 else (plural_form or word + 's')}"


# -------------------------------------------------------------------------- sections


def corpus_summary(data: ReportData) -> list[Block]:
    per_category = Counter(d.category for d in data.documents)
    passages = sum(d.passage_count for d in data.documents)
    words = sum(d.word_count or 0 for d in data.documents)
    blocks: list[Block] = [
        Paragraph(
            f"The analysis used {plural(len(data.documents), 'document')} "
            f"({fmt_number(words)} words). Each document was split into short extracts of 3 to "
            f"5 sentences ({plural(passages, 'extract')} in all), which are what the system "
            "compares."
        ),
        KeyValues(
            [
                (document_type(category, plural=True).capitalize(), str(count))
                for category, count in sorted(per_category.items())
            ]
        ),
        Table(
            columns=["Document", "File", "Pages", "Words", "Extracts"],
            rows=[
                [
                    d.label,
                    d.file_type.upper(),
                    fmt_number(d.page_count),
                    fmt_number(d.word_count),
                    fmt_number(d.passage_count),
                ]
                for d in data.documents
            ],
            numeric=(2, 3, 4),
            widths=(52, 8, 10, 15, 15),
        ),
    ]
    return blocks


def nlp_findings(data: ReportData) -> list[Block]:
    blocks: list[Block] = [Subheading("Words that stand out")]
    terms = data.keywords.get("overall", [])[:TOP_TERMS]
    if terms:
        blocks.append(
            Table(
                columns=["Word", "Weight", "Extracts"],
                rows=[
                    [t["term"], f"{t['score']:.3f}", fmt_number(t.get("passage_count"))]
                    for t in terms
                ],
                numeric=(1, 2),
                widths=(60, 20, 20),
            )
        )
    else:
        blocks.append(Paragraph("No words stood out.", muted=True))

    blocks.append(Subheading("Skills employers ask for"))
    skills = data.entities.get("skills", [])[:TOP_SKILLS]
    if skills:
        blocks.append(
            Paragraph(
                f"{fmt_number(data.entities.get('passages_with_skills'))} of "
                f"{fmt_number(data.entities.get('passage_count'))} extracts mention at least one "
                "known skill, tool, programming language or certification."
            )
        )
        blocks.append(
            Table(
                columns=["Skill", "Type", "Documents", "Mentions"],
                rows=[
                    [
                        s["name"],
                        s["label"].title() if s["label"] != "CERT" else "Certification",
                        fmt_number(s["document_frequency"]),
                        fmt_number(s["mentions"]),
                    ]
                    for s in skills
                ],
                numeric=(2, 3),
                widths=(45, 20, 17, 18),
            )
        )
    else:
        blocks.append(Paragraph("No known skills were found in the documents.", muted=True))

    blocks.append(Subheading("Topics found"))
    topics = data.topics.get("topics", [])
    blocks.append(
        Paragraph(
            f"{plural(len(topics), 'topic')} found in "
            f"{fmt_number(data.topics.get('modelled_passages'))} extracts; "
            f"{fmt_number(data.topics.get('outlier_passages'))} extracts did not fit any topic."
        )
    )
    if topics:
        blocks.append(
            Table(
                columns=["Topic", "Extracts", "Documents", "How often it comes up", "Keywords"],
                rows=[
                    [
                        t["title"],
                        fmt_number(t["size"]),
                        fmt_number(t["document_count"]),
                        fmt_level(t["strength"]),
                        ", ".join(k.get("label") or k["term"] for k in t.get("keywords", [])[:8]),
                    ]
                    for t in topics
                ],
                numeric=(1, 2, 3),
                widths=(28, 11, 11, 11, 39),
            )
        )
    return blocks


def overlap(data: ReportData) -> list[Block]:
    threshold = float(
        data.similarity.get("threshold", data.parameters.get("similarity_threshold", 0.8))
    )
    candidates = data.similarity.get("candidates", [])
    duplicates = sum(c["overlap_status"] == "Potential Duplicate" for c in candidates)
    by_course = data.similarity.get("basis") == "course"
    compared_with = "every course" if by_course else "every extract"
    return [
        Paragraph(
            f"Each topic was compared, by meaning, with {compared_with} of the NUC core "
            f"({data.nuc_core_version or 'unknown version'}). Topics more than "
            f"{fmt_percent(threshold)} similar to it are marked “May already be in NUC core”: "
            f"{duplicates} of "
            f"{len(candidates)}."
        ),
        Table(
            columns=[
                "Topic",
                "Similarity",
                "How new it is (/100)",
                "NUC core",
                "Closest NUC course" if by_course else "Closest NUC core extract",
            ],
            rows=[
                [
                    c["title"],
                    fmt_percent(c["max_similarity"]),
                    fmt_level(c["novelty"]),
                    STATUS_LABELS.get(c["overlap_status"], c["overlap_status"]),
                    (
                        f"{course['code']} – {course['title']}"
                        if by_course and (course := c.get("closest_nuc_course"))
                        else excerpt(c.get("closest_nuc_passage", {}).get("text", ""), 220)
                    ),
                ]
                for c in candidates
            ],
            numeric=(1, 2),
            widths=(22, 11, 9, 16, 42),
        ),
    ]


def recommendations(data: ReportData) -> list[Block]:
    weights = data.parameters.get("weights", {})
    blocks: list[Block] = [
        Paragraph(
            "Each topic has a score out of 100 made of three parts, each out of 100 and compared "
            "with the session's other topics: employer demand "
            f"{fmt_weight(weights.get('ner', 0))}, how often it comes up "
            f"{fmt_weight(weights.get('topic', 0))} and how new it is compared with the NUC core "
            f"{fmt_weight(weights.get('novelty', 0))}. High = 70 or more, Medium = 40–69, "
            "Low = below 40."
        ),
        Table(
            columns=[
                "#",
                "Recommended topic",
                "Score (/100)",
                "Employer demand",
                "How often it comes up",
                "How new it is",
                "NUC core",
            ],
            rows=[
                [
                    str(r.rank),
                    r.title,
                    str(points(r.composite)),
                    fmt_level(r.ner),
                    fmt_level(r.topic),
                    fmt_level(r.novelty),
                    STATUS_LABELS.get(r.overlap_status, r.overlap_status),
                ]
                for r in data.recommendations
            ],
            numeric=(0, 2, 3, 4, 5),
            widths=(5, 35, 11, 11, 12, 10, 16),
        ),
    ]
    for r in data.recommendations:
        blocks.append(Subheading(f"{r.rank}. {r.title}"))
        blocks.append(
            Paragraph(
                f"Score {fmt_points(r.composite)}: employer demand {fmt_level(r.ner)}, how often "
                f"it comes up {fmt_level(r.topic)}, how new it is {fmt_level(r.novelty)}.",
                muted=True,
            )
        )
        blocks.append(Paragraph(r.description))
        if r.skills:
            blocks.append(Paragraph("Skills: " + ", ".join(r.skills), muted=True))
    return blocks


def decisions(data: ReportData) -> list[Block]:
    counts = Counter(r.decision or "undecided" for r in data.recommendations)
    decided = [r for r in data.recommendations if r.decision]
    blocks: list[Block] = [
        KeyValues(
            [
                ("Accepted", str(counts["accepted"])),
                ("Rejected", str(counts["rejected"])),
                ("Discuss later", str(counts["flagged"])),
                ("Not yet reviewed", str(counts["undecided"])),
            ]
        )
    ]
    if decided:
        blocks.append(
            Table(
                columns=["#", "Recommended topic", "Decision", "By", "Date", "Notes"],
                rows=[
                    [
                        str(r.rank),
                        r.title,
                        DECISION_LABELS.get(r.decision or "", r.decision or ""),
                        r.decided_by or "—",
                        r.decided_at.strftime("%d %b %Y") if r.decided_at else "—",
                        r.notes or "",
                    ]
                    for r in decided
                ],
                numeric=(0,),
                widths=(5, 30, 11, 16, 12, 26),
            )
        )
    else:
        blocks.append(Paragraph("No recommendation has been reviewed yet.", muted=True))
    return blocks


def proposed_courses(data: ReportData) -> list[Block]:
    if not data.mappings:
        return [
            Paragraph("No course has been designed for an accepted recommendation yet.", muted=True)
        ]
    total = sum(m.credit_units for m in data.mappings)
    if data.credit_unit_allowance is None:
        allowance = (
            f"{plural(total, 'credit unit')} proposed. No 30% credit-unit allowance has been "
            "configured."
        )
    elif total > data.credit_unit_allowance:
        allowance = (
            f"{total} of {data.credit_unit_allowance} credit units: over the allowance by "
            f"{total - data.credit_unit_allowance}."
        )
    else:
        allowance = (
            f"{total} of {data.credit_unit_allowance} credit units "
            f"({data.credit_unit_allowance - total} remaining)."
        )
    blocks: list[Block] = [
        Paragraph(allowance),
        Table(
            columns=["Code", "Course title", "Units", "Prerequisites", "From recommendation"],
            rows=[
                [
                    m.course_code,
                    m.course_title,
                    str(m.credit_units),
                    ", ".join(m.prerequisites) or "—",
                    f"#{m.recommendation_rank} {m.recommendation_title}",
                ]
                for m in data.mappings
            ],
            numeric=(2,),
            widths=(11, 30, 8, 20, 31),
        ),
    ]
    for m in data.mappings:
        blocks.append(Subheading(f"{m.course_code}: {m.course_title}"))
        blocks.append(Paragraph("Learning outcomes — on completion, students should be able to:"))
        blocks.append(BulletList(m.learning_outcomes))
    return blocks


BUILDERS = {
    "corpus_summary": corpus_summary,
    "nlp_findings": nlp_findings,
    "overlap": overlap,
    "recommendations": recommendations,
    "decisions": decisions,
    "proposed_courses": proposed_courses,
}


def build_report(data: ReportData, sections: list[str]) -> ReportDocument:
    """Assemble the chosen sections (always in the standard order) into a report document."""
    unknown = set(sections) - set(REPORT_SECTIONS)
    if unknown:
        raise ValueError(f"Unknown report sections: {', '.join(sorted(unknown))}")
    weights = data.parameters.get("weights", {})
    meta = [
        ("Analysis session", data.session_name),
        ("Analysis completed", fmt_datetime(data.completed_at)),
        ("NUC core reference", data.nuc_core_version or "—"),
        (
            "Score weights",
            f"employer demand {fmt_weight(weights.get('ner', 0))} · how often it comes up "
            f"{fmt_weight(weights.get('topic', 0))} · how new it is "
            f"{fmt_weight(weights.get('novelty', 0))}",
        ),
        (
            "“May already be in NUC core” when",
            f"more than {fmt_percent(float(data.parameters.get('similarity_threshold', 0.8)))}"
            " similar",
        ),
        ("Generated", f"{fmt_datetime(data.generated_at)} by {data.generated_by}"),
    ]
    chosen = [key for key in REPORT_SECTIONS if key in sections]
    return ReportDocument(
        title="Curriculum Recommendation Report",
        subtitle=data.session_name,
        meta=meta,
        sections=[Section(key, REPORT_SECTIONS[key], BUILDERS[key](data)) for key in chosen],
    )
