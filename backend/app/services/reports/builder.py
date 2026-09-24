"""Report content (spec §16), independent of output format.

The builder produces a list of simple blocks; the PDF and DOCX renderers only lay
them out, so both formats always contain the same information.
"""
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload, undefer

from ...extensions import db
from ...models import AnalysisSession, Document, DocumentSession, Recommendation

TOP_KEYWORDS = 15
TOP_SKILLS = 15


@dataclass
class Block:
    kind: str                      # heading | subheading | paragraph | table | bullets
    text: str = ""
    headers: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    items: list = field(default_factory=list)
    widths: list = field(default_factory=list)  # relative column widths for tables


@dataclass
class ReportContent:
    title: str
    subtitle: str
    meta: list                     # [(label, value)]
    blocks: list


def _pct(value):
    return f"{value:.2f}" if isinstance(value, (int, float)) else "-"


def build_report(session_id: int, author, institution: str) -> ReportContent:
    session = db.session.get(AnalysisSession, session_id, options=[undefer(AnalysisSession.corpus_results)])
    params = session.parameter_config
    info = session.pipeline_info or {}
    corpus = session.corpus_results or {}
    links = db.session.execute(
        select(DocumentSession).where(DocumentSession.session_id == session_id)
        .order_by(DocumentSession.processing_order).options(selectinload(DocumentSession.document))
    ).scalars().all()
    recs = db.session.execute(
        select(Recommendation).where(Recommendation.session_id == session_id)
        .order_by(Recommendation.rank).options(undefer(Recommendation.evidence), selectinload(Recommendation.curriculum_maps))
    ).scalars().all()
    core_docs = {
        d.document_id: d.title
        for d in db.session.execute(
            select(Document).where(Document.document_id.in_(info.get("core_document_ids", [])))
        ).scalars()
    }

    blocks = []
    add = blocks.append

    # 1. Summary
    decisions = Counter(r.planner_decision.value if r.planner_decision else "Pending review" for r in recs)
    mappings = [m for r in recs for m in r.curriculum_maps]
    add(Block("heading", "1. Summary"))
    add(Block("paragraph",
              f"This report presents {len(recs)} ranked recommendations for the NUC CCMAS 30% localised "
              f"curriculum, derived from {info.get('analysis_document_count', len(links))} source document(s) "
              f"and checked for semantic overlap against the NUC 70% core "
              f"({len(core_docs)} core reference document(s)). "
              f"{info.get('potential_duplicates', 0)} recommendation(s) were flagged as potential duplicates of the core."))
    add(Block("table", widths=[3, 1], headers=["Planner decision", "Count"],
              rows=[[k, str(v)] for k, v in sorted(decisions.items())] + [["Mapped to courses", str(len(mappings))]]))
    for warning in info.get("warnings", []):
        add(Block("paragraph", f"Note: {warning}"))

    # 2. Session configuration
    add(Block("heading", "2. Session configuration"))
    add(Block("table", widths=[1, 1], headers=["Parameter", "Value"], rows=[
        ["Semantic overlap threshold", _pct(params["similarity_threshold"])],
        ["NER skill-demand weight", _pct(params["ner_weight"])],
        ["BERTopic relevance weight", _pct(params["topic_weight"])],
        ["Semantic novelty weight", _pct(params["novelty_weight"])],
        ["Maximum recommendations", str(params["max_recommendations"])],
        ["Embedding model", f"{info.get('embedding_model', '-')} ({info.get('embedding_backend', '-')})"],
        ["spaCy model", info.get("spacy_model", "-")],
        ["Analysis completed", session.completed_at.strftime("%d %b %Y %H:%M UTC") if session.completed_at else "-"],
        ["Processing time", f"{info.get('total_seconds', '-')} s"],
    ]))
    add(Block("paragraph", "Composite score = (NER weight x NER score) + (topic weight x topic score) + "
                           "(novelty weight x novelty score); novelty = 1 - maximum cosine similarity to the NUC core."))

    # 3. Corpus
    add(Block("heading", "3. Corpus summary"))
    add(Block("table", widths=[0.5, 5, 2.5, 1], headers=["#", "Document", "Source category", "Words"], rows=[
        [str(i), link.document.title, link.document.source_category.value, str(link.document.word_count or "-")]
        for i, link in enumerate(links, start=1)
    ]))
    if core_docs:
        add(Block("paragraph", "NUC core reference used for overlap detection: " + "; ".join(core_docs.values()) + "."))

    # 4. NLP findings
    add(Block("heading", "4. NLP findings"))
    add(Block("subheading", "4.1 Most distinctive terms (TF-IDF)"))
    add(Block("paragraph", ", ".join(k["term"] for k in corpus.get("corpus_keywords", [])[:TOP_KEYWORDS]) or "None."))
    add(Block("subheading", "4.2 Skill demand (NER)"))
    add(Block("table", widths=[3, 1, 1, 1], headers=["Skill / tool / certification", "Type", "Documents", "Mentions"], rows=[
        [e["text"], e["label"], str(e["document_frequency"]), str(e["mentions"])]
        for e in corpus.get("skill_demand", [])[:TOP_SKILLS]
    ] or [["None found", "", "", ""]]))
    add(Block("subheading", "4.3 Themes (BERTopic)"))
    add(Block("table", widths=[3, 1, 1, 4], headers=["Topic", "Passages", "Relevance", "Top keywords"], rows=[
        [t["label"], str(t["size"]), _pct(t["relevance"]), ", ".join(k["term"] for k in t["keywords"][:5])]
        for t in corpus.get("topics", [])
    ] or [["No topics found", "", "", ""]]))

    # 5. Recommendations
    add(Block("heading", "5. Ranked recommendations"))
    add(Block("table", widths=[0.5, 3.5, 0.9, 0.8, 0.9, 0.9, 1.6, 1.1], headers=["#", "Recommendation", "Score", "NER", "Theme", "Novelty", "Overlap", "Decision"], rows=[
        [str(r.rank), r.topic_title, _pct(r.composite_score), _pct(r.ner_score), _pct(r.topic_score),
         _pct(r.novelty_score), r.overlap_status.value, r.planner_decision.value if r.planner_decision else "Pending"]
        for r in recs
    ] or [["-", "No recommendations", "", "", "", "", "", ""]]))
    for r in recs:
        evidence = r.evidence or {}
        add(Block("subheading", f"{r.rank}. {r.topic_title}"))
        if r.topic_description:
            add(Block("paragraph", r.topic_description))
        items = [f"Scores: composite {_pct(r.composite_score)}, NER {_pct(r.ner_score)}, "
                 f"topic {_pct(r.topic_score)}, novelty {_pct(r.novelty_score)}"]
        match = (evidence.get("core_matches") or [None])[0]
        if match:
            items.append(f"Closest NUC core content (similarity {_pct(match['similarity'])}): \"{match['text']}\"")
        for passage in evidence.get("passages", [])[:2]:
            items.append(f"Evidence: \"{passage['text']}\"")
        if r.planner_notes:
            items.append(f"Planner notes: {r.planner_notes}")
        add(Block("bullets", items=items))

    # 6. Overlap
    add(Block("heading", "6. Semantic overlap with the NUC core"))
    add(Block("paragraph", f"Candidates with maximum similarity above {_pct(params['similarity_threshold'])} "
                           "are flagged as Potential Duplicate and require planner review before acceptance."))
    add(Block("table", widths=[2.5, 1.1, 1.4, 4], headers=["Topic", "Max similarity", "Status", "Closest core segment"], rows=[
        [r.topic_title, _pct(r.max_similarity), r.overlap_status.value,
         ((r.evidence or {}).get("core_matches") or [{"text": "-"}])[0]["text"]]
        for r in recs
    ] or [["-", "", "", ""]]))

    # 7. Curriculum mapping
    add(Block("heading", "7. Proposed curriculum mapping"))
    if not mappings:
        add(Block("paragraph", "No accepted recommendation has been mapped to a course yet."))
    for r in recs:
        for m in r.curriculum_maps:
            add(Block("subheading", f"{m.course_code}: {m.course_title} ({m.credit_units} unit{'s' if m.credit_units > 1 else ''})"))
            add(Block("paragraph", f"Derived from recommendation #{r.rank}: {r.topic_title}. "
                                   f"Prerequisites: {', '.join(m.prerequisites or []) or 'none'}."))
            add(Block("bullets", items=m.learning_outcomes or []))

    now = datetime.now(timezone.utc)
    return ReportContent(
        title="Curriculum Recommendation Report",
        subtitle=session.session_name,
        meta=[("Institution", institution), ("Generated", now.strftime("%d %b %Y %H:%M UTC")),
              ("Prepared by", author.username), ("Session ID", str(session.session_id))],
        blocks=blocks,
    )
