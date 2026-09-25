"""Report content: turns a session's stored results into a format-neutral document.

``build_report`` is pure (no database, no rendering). It returns a :class:`ReportDocument`
made of sections, each a list of simple blocks (paragraphs, key/value lists, bullet lists and
tables). The PDF renderer (HTML + WeasyPrint) and the DOCX renderer (python-docx) both draw
this same structure, so the two formats always contain the same information.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# Section keys in report order, with their headings. Planners choose any non-empty subset.
REPORT_SECTIONS: dict[str, str] = {
    "corpus_summary": "Corpus summary",
    "nlp_findings": "NLP findings",
    "overlap": "Overlap with the NUC core",
    "recommendations": "Recommendations",
    "decisions": "Planner decisions",
    "proposed_courses": "Proposed courses",
}

CATEGORY_LABELS = {
    "job_market": "Job market",
    "institutional": "Institutional",
    "policy": "Policy",
    "academic": "Academic",
}
DECISION_LABELS = {"accepted": "Accepted", "rejected": "Rejected", "flagged": "Flagged"}

TOP_TERMS = 20
TOP_SKILLS = 20
EXCERPT_CHARS = 300

DISCLAIMER = (
    "NLP-RS proposes candidate topics as decision support. The recommendations, scores and "
    "overlap flags are produced automatically from the uploaded documents; curriculum decisions "
    "rest with the department's planners and the relevant university bodies."
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


def fmt_score(value: float) -> str:
    return f"{value:.2f}"


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
            f"({fmt_number(words)} words, {plural(passages, 'passage')}). "
            "Each document was split into passages of 3–5 sentences, which are the unit of "
            "analysis."
        ),
        KeyValues(
            [
                (CATEGORY_LABELS.get(category, category), plural(count, "document"))
                for category, count in sorted(per_category.items())
            ]
        ),
        Table(
            columns=["Document", "Category", "Type", "Pages", "Words", "Passages"],
            rows=[
                [
                    d.title,
                    CATEGORY_LABELS.get(d.category, d.category),
                    d.file_type.upper(),
                    fmt_number(d.page_count),
                    fmt_number(d.word_count),
                    fmt_number(d.passage_count),
                ]
                for d in data.documents
            ],
            numeric=(3, 4, 5),
            widths=(40, 14, 8, 10, 14, 14),
        ),
    ]
    return blocks


def nlp_findings(data: ReportData) -> list[Block]:
    blocks: list[Block] = [Subheading("Most characteristic terms (TF-IDF)")]
    terms = data.keywords.get("overall", [])[:TOP_TERMS]
    if terms:
        blocks.append(
            Table(
                columns=["Term", "Mean TF-IDF", "Passages"],
                rows=[
                    [t["term"], f"{t['score']:.3f}", fmt_number(t.get("passage_count"))]
                    for t in terms
                ],
                numeric=(1, 2),
                widths=(60, 20, 20),
            )
        )
    else:
        blocks.append(Paragraph("No terms were extracted.", muted=True))

    blocks.append(Subheading("Skills in demand"))
    skills = data.entities.get("skills", [])[:TOP_SKILLS]
    if skills:
        blocks.append(
            Paragraph(
                f"{fmt_number(data.entities.get('passages_with_skills'))} of "
                f"{fmt_number(data.entities.get('passage_count'))} passages mention at least one "
                "recognised skill, tool, language or certification."
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
        blocks.append(Paragraph("No skill patterns matched the documents.", muted=True))

    blocks.append(Subheading("Themes discovered (BERTopic)"))
    topics = data.topics.get("topics", [])
    blocks.append(
        Paragraph(
            f"{plural(len(topics), 'theme')} found in "
            f"{fmt_number(data.topics.get('modelled_passages'))} passages; "
            f"{fmt_number(data.topics.get('outlier_passages'))} passages fitted no theme."
        )
    )
    if topics:
        blocks.append(
            Table(
                columns=["Theme", "Passages", "Documents", "Strength", "Keywords"],
                rows=[
                    [
                        t["title"],
                        fmt_number(t["size"]),
                        fmt_number(t["document_count"]),
                        fmt_score(t["strength"]),
                        ", ".join(k["term"] for k in t.get("keywords", [])[:8]),
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
    return [
        Paragraph(
            "Each theme was compared with every passage of the NUC core reference "
            f"({data.nuc_core_version or 'unknown version'}) by cosine similarity of sentence "
            f"embeddings. Themes with a highest similarity above {fmt_score(threshold)} are "
            f"flagged as potential duplicates of existing core content: {duplicates} of "
            f"{len(candidates)}."
        ),
        Table(
            columns=["Theme", "Max similarity", "Novelty", "Status", "Closest NUC core passage"],
            rows=[
                [
                    c["title"],
                    fmt_score(c["max_similarity"]),
                    fmt_score(c["novelty"]),
                    c["overlap_status"],
                    excerpt(c.get("closest_nuc_passage", {}).get("text", ""), 220),
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
            "Composite score = "
            f"{weights.get('ner', 0):.2f} × skill demand + "
            f"{weights.get('topic', 0):.2f} × theme strength + "
            f"{weights.get('novelty', 0):.2f} × novelty; each score is scaled to 0–1 across "
            "the session's themes."
        ),
        Table(
            columns=[
                "#",
                "Recommended topic",
                "Composite",
                "Skill demand",
                "Theme strength",
                "Novelty",
                "Overlap",
            ],
            rows=[
                [
                    str(r.rank),
                    r.title,
                    fmt_score(r.composite),
                    fmt_score(r.ner),
                    fmt_score(r.topic),
                    fmt_score(r.novelty),
                    "Potential duplicate" if r.overlap_status == "Potential Duplicate" else "New",
                ]
                for r in data.recommendations
            ],
            numeric=(0, 2, 3, 4, 5),
            widths=(5, 35, 11, 11, 12, 10, 16),
        ),
    ]
    for r in data.recommendations:
        blocks.append(Subheading(f"{r.rank}. {r.title}"))
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
                ("Flagged", str(counts["flagged"])),
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
            Paragraph("No accepted recommendation has been mapped to a course yet.", muted=True)
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
            f"skill demand {weights.get('ner', 0):.2f} · theme strength "
            f"{weights.get('topic', 0):.2f} · novelty {weights.get('novelty', 0):.2f}",
        ),
        (
            "Duplicate threshold",
            fmt_score(float(data.parameters.get("similarity_threshold", 0.8))),
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
