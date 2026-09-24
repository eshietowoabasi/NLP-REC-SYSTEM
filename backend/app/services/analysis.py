"""Analysis pipeline orchestration (spec §6 steps 7–15, §15, Appendix C).

parse -> preprocess -> TF-IDF -> NER -> SBERT -> BERTopic -> overlap -> scoring -> persist.

NUC Core Reference documents in a session are processed but treated as the
comparison baseline: they are excluded from corpus keywords, skill demand and
topic modelling so the prescribed core does not count as "demand".
"""
import time
from collections import Counter
from datetime import datetime, timedelta, timezone

import numpy as np
from flask import current_app
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload, undefer

from ..extensions import db
from ..models import (
    AnalysisSession,
    Document,
    DocumentSession,
    DocumentStatus,
    NLPResult,
    Recommendation,
    SessionStatus,
    SourceCategory,
)
from ..utils.audit import record_audit
from .embeddings import get_embedder, mean_embedding
from .ingestion import parse_document
from .ner import aggregate_skill_demand, extract_entities
from .preprocessing import preprocess
from .preprocessing.normalize import split_blocks
from .recommendations import Candidate, rank_candidates, score_candidates
from .similarity import build_core_index, detect_overlap
from .tfidf import extract_keywords
from .topics import model_topics, select_passages


class _StageTimer:
    def __init__(self, session):
        self.session = session
        self.timings = {}
        self._stage = None
        self._start = None

    def start(self, stage):
        self._finish()
        self._stage, self._start = stage, time.perf_counter()
        self.session.progress_stage = stage
        self.session.heartbeat_at = datetime.now(timezone.utc)
        db.session.commit()  # make progress visible to pollers

    def _finish(self):
        if self._stage:
            self.timings[self._stage] = round(time.perf_counter() - self._start, 3)

    def done(self):
        self._finish()
        self._stage = None
        return self.timings


def _document_text(document: Document) -> str:
    if document.extracted_text:
        return document.extracted_text
    with open(document.file_path, "rb") as fh:  # parsed text missing: re-parse the stored file
        return parse_document(fh.read(), document.file_type).text


NO_CORE_MESSAGE = (
    "No parsed NUC Core Reference document is available for overlap detection. "
    "An Admin must upload the CCMAS core curriculum first."
)


class NoCoreReferenceError(RuntimeError):
    pass


def core_reference_available() -> bool:
    return db.session.execute(
        select(Document.document_id).where(
            Document.source_category == SourceCategory.NUC_CORE,
            Document.processing_status == DocumentStatus.PARSED,
        ).limit(1)
    ).first() is not None


def _core_reference_documents():
    """All parsed NUC Core Reference documents in the library (a session's own core
    references are part of the library too)."""
    return db.session.execute(
        select(Document)
        .where(Document.source_category == SourceCategory.NUC_CORE,
               Document.processing_status == DocumentStatus.PARSED)
        .order_by(Document.document_id)
        .options(undefer(Document.extracted_text))
    ).scalars().all()


def _build_candidates(topic_result, passages, sentence_entities) -> list[Candidate]:
    """One candidate per BERTopic topic (Appendix C: build_topic_candidates)."""
    members = {}
    for passage, topic_id in zip(passages, topic_result.assignments):
        if topic_id != -1:
            members.setdefault(topic_id, []).append(passage)
    candidates = []
    for topic in topic_result.topics:
        topic_members = members.get(topic["topic_id"], [])
        mentions, in_passages, seen = Counter(), Counter(), set()
        for passage in topic_members:
            found = sentence_entities.get((passage.document_id, passage.text), [])
            mentions.update(found)
            key = " ".join(passage.text.lower().split())
            if key not in seen:  # distinct passages, matching distinct_passages
                seen.add(key)
                in_passages.update(set(found))
        candidates.append(Candidate(
            topic_id=topic["topic_id"],
            topic_label=topic["label"],
            embedding=np.asarray(topic["embedding"], dtype=np.float32),
            passage_count=topic["size"],
            distinct_passages=topic.get("distinct_passages", topic["size"]),
            document_ids=[c["document_id"] for c in topic["document_counts"]],
            source_category_counts=topic["source_category_counts"],
            keywords=[k["term"] for k in topic["keywords"]],
            representative_passages=topic["representative_passages"],
            entity_mentions=mentions,
            entity_passages=in_passages,
        ))
    return candidates


def _recommendation(session_id, rank, candidate, core_titles) -> Recommendation:
    return Recommendation(
        session_id=session_id,
        rank=rank,
        topic_title=candidate.title,
        topic_description=candidate.description,
        ner_score=candidate.ner_score,
        topic_score=candidate.topic_score,
        novelty_score=candidate.novelty_score,
        composite_score=candidate.composite_score,
        max_similarity=candidate.max_similarity,
        overlap_status=candidate.overlap_status,
        evidence={
            "topic_id": candidate.topic_id,
            "topic_label": candidate.topic_label,
            "keywords": candidate.keywords[:10],
            "passage_count": candidate.passage_count,
            "document_ids": candidate.document_ids,
            "source_category_counts": candidate.source_category_counts,
            "passages": candidate.representative_passages,
            "skills": [
                {"text": name, "label": label, "mentions": n}
                for (name, label), n in candidate.entity_mentions.most_common(10)
            ],
            "core_matches": [
                {**match, "document_title": core_titles.get(match["document_id"])}
                for match in candidate.core_matches
            ],
        },
    )


def run_analysis(session_id: int) -> None:
    """Execute the pipeline for a session already marked Processing. Never raises."""
    session = db.session.get(AnalysisSession, session_id)
    if session is None or session.status is not SessionStatus.PROCESSING:
        current_app.logger.warning("Session %s is not processing; skipping run", session_id)
        return
    try:
        _run(session)
    except Exception as exc:
        current_app.logger.exception("Analysis session %s failed", session_id)
        db.session.rollback()
        session = db.session.get(AnalysisSession, session_id)
        session.status = SessionStatus.FAILED
        session.error_message = f"{type(exc).__name__}: {exc}"[:2000]
        record_audit("SESSION_RUN_FAILED", "AnalysisSession", session_id,
                     {"stage": session.progress_stage, "error": session.error_message[:500]},
                     user_id=session.user_id, commit=False)
        db.session.commit()


def _run(session: AnalysisSession) -> None:
    config = current_app.config
    started = datetime.now(timezone.utc)
    timer = _StageTimer(session)
    warnings = []

    # --- parsing
    timer.start("parsing")
    links = db.session.execute(
        select(DocumentSession)
        .where(DocumentSession.session_id == session.session_id)
        .order_by(DocumentSession.processing_order)
        .options(selectinload(DocumentSession.document).options(undefer(Document.extracted_text)))
    ).scalars().all()
    if not links:
        raise ValueError("Session has no documents")
    texts = {link.doc_session_id: _document_text(link.document) for link in links}
    is_reference = {link.doc_session_id: link.document.source_category is SourceCategory.NUC_CORE for link in links}
    analysis_links = [link for link in links if not is_reference[link.doc_session_id]]
    if not analysis_links:
        raise ValueError("Session contains only NUC Core Reference documents; add documents to analyse")

    # --- preprocessing
    timer.start("preprocessing")
    pre = {ds_id: preprocess(split_blocks(text), config["SPACY_MODEL"]) for ds_id, text in texts.items()}

    # --- TF-IDF
    timer.start("keywords")
    order = [link.doc_session_id for link in links]
    per_doc_keywords = extract_keywords([pre[i].tokens for i in order], top_n=config["TFIDF_TOP_N"]).per_document
    keywords = dict(zip(order, per_doc_keywords))
    corpus_keywords = extract_keywords(
        [pre[link.doc_session_id].tokens for link in analysis_links],
        top_n=config["TFIDF_TOP_N"], corpus_top_n=config["TFIDF_CORPUS_TOP_N"],
    ).corpus

    # --- NER
    timer.start("entities")
    entities = {ds_id: extract_entities(pre[ds_id].sentences, config["SPACY_MODEL"]) for ds_id in order}
    skill_demand = aggregate_skill_demand(
        {link.document_id: entities[link.doc_session_id] for link in analysis_links}
    )

    # --- SBERT embeddings
    timer.start("embeddings")
    embedder = get_embedder(config["EMBEDDING_BACKEND"], config["SBERT_MODEL"])
    if embedder.backend == "hashing":
        warnings.append("Hashing embeddings in use (offline mode): similarity is lexical, not semantic. Do not use these results for decisions.")
    passages, doc_vectors, passage_vectors = {}, {}, {}
    for link in links:
        ds_id = link.doc_session_id
        passages[ds_id] = select_passages(pre[ds_id].sentences, link.document_id, link.document.source_category.value)
        texts_to_embed = [p.text for p in passages[ds_id]] or pre[ds_id].sentences
        vectors = embedder.encode(texts_to_embed)
        passage_vectors[ds_id] = vectors if passages[ds_id] else vectors[:0]
        doc_vectors[ds_id] = mean_embedding(vectors)

    # --- BERTopic
    timer.start("topics")
    topic_passages = [p for link in analysis_links for p in passages[link.doc_session_id]]
    topic_vectors = [passage_vectors[link.doc_session_id] for link in analysis_links]
    topic_vectors = np.vstack(topic_vectors) if topic_vectors else np.zeros((0, 1))
    topic_result = model_topics(topic_passages, topic_vectors)
    warnings.extend(topic_result.warnings)

    # --- semantic overlap with the NUC core (spec §9)
    timer.start("overlap")
    params = session.parameter_config
    core_documents = _core_reference_documents()
    if not core_documents:
        raise NoCoreReferenceError(NO_CORE_MESSAGE)
    core_index = build_core_index(
        ((d.document_id, d.content_hash or str(d.document_id), _document_text(d)) for d in core_documents), embedder
    )
    if len(core_index) == 0:
        raise NoCoreReferenceError("The NUC Core Reference documents contain no usable text segments")
    sentence_entities = {
        (link.document_id, sentence): found
        for link in analysis_links
        for sentence, found in zip(pre[link.doc_session_id].sentences, entities[link.doc_session_id].sentence_entities)
    }
    candidates = _build_candidates(topic_result, topic_passages, sentence_entities)
    overlaps = detect_overlap(np.array([c.embedding for c in candidates]), core_index,
                              params["similarity_threshold"]) if candidates else []
    if not candidates:
        warnings.append("No candidate topics were found, so no recommendations were generated.")

    # --- recommendation scoring and ranking (spec §10)
    timer.start("scoring")
    score_candidates(candidates, overlaps, params)
    ranked = rank_candidates(candidates, params["max_recommendations"])
    core_titles = {d.document_id: d.title for d in core_documents}

    # --- persist
    timer.start("saving")
    db.session.execute(delete(Recommendation).where(Recommendation.session_id == session.session_id))
    for position, candidate in enumerate(ranked, start=1):
        db.session.add(_recommendation(session.session_id, position, candidate, core_titles))
    db.session.execute(delete(NLPResult).where(NLPResult.doc_session_id.in_(order)))
    for link in links:
        ds_id = link.doc_session_id
        vector = doc_vectors[ds_id]
        db.session.add(NLPResult(
            doc_session_id=ds_id,
            tfidf_keywords=keywords[ds_id],
            ner_entities=entities[ds_id].entities,
            topics=topic_result.document_topics.get(link.document_id, []),
            embedding=[round(float(x), 6) for x in vector] if vector is not None else None,
        ))
    session.corpus_results = {
        "corpus_keywords": corpus_keywords,
        "skill_demand": skill_demand,
        "topics": topic_result.topics,
        "topic_method": topic_result.method,
    }
    timings = timer.done()
    session.pipeline_info = {
        "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "stage_seconds": timings,
        "total_seconds": round(sum(timings.values()), 3),
        "spacy_model": config["SPACY_MODEL"],
        "embedding_backend": embedder.backend,
        "embedding_model": embedder.model_name,
        "document_count": len(links),
        "analysis_document_count": len(analysis_links),
        "reference_document_count": len(links) - len(analysis_links),
        "word_count": sum(len(t.split()) for t in texts.values()),
        "passage_count": topic_result.passage_count,
        "topic_count": len(topic_result.topics),
        "outlier_passages": topic_result.outlier_count,
        "core_document_ids": core_index.document_ids,
        "core_segment_count": len(core_index),
        "candidate_count": len(candidates),
        "recommendation_count": len(ranked),
        "potential_duplicates": sum(c.overlap_status.value == "Potential Duplicate" for c in ranked),
        "warnings": warnings,
    }
    session.status = SessionStatus.COMPLETED
    session.progress_stage = None
    session.error_message = None
    session.completed_at = datetime.now(timezone.utc)
    record_audit("SESSION_RUN_COMPLETED", "AnalysisSession", session.session_id,
                 {"total_seconds": session.pipeline_info["total_seconds"], "topics": len(topic_result.topics),
                  "recommendations": len(ranked)},
                 user_id=session.user_id, commit=False)
    db.session.commit()


STALE_RUN_MESSAGE = (
    "The analysis worker stopped responding (stage: {stage}). The run was marked as failed "
    "so it can be retried."
)


def fail_stale_runs(max_minutes: int) -> list[int]:
    """Mark sessions stuck in Processing (no heartbeat for ``max_minutes``) as Failed."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_minutes)
    stale = db.session.execute(
        select(AnalysisSession).where(
            AnalysisSession.status == SessionStatus.PROCESSING,
            (AnalysisSession.heartbeat_at < cutoff) | AnalysisSession.heartbeat_at.is_(None),
        )
    ).scalars().all()
    for session in stale:
        session.status = SessionStatus.FAILED
        session.error_message = STALE_RUN_MESSAGE.format(stage=session.progress_stage or "unknown")
        record_audit("SESSION_RUN_STALE", "AnalysisSession", session.session_id,
                     {"stage": session.progress_stage, "max_minutes": max_minutes},
                     user_id=session.user_id, commit=False)
        session.progress_stage = None
    db.session.commit()
    return [s.session_id for s in stale]
