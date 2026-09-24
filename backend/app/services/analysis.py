"""Analysis pipeline orchestration (spec §6 steps 7–12, §15, Appendix C).

parse -> preprocess -> TF-IDF -> NER -> SBERT -> BERTopic -> persist.
Semantic overlap and recommendation scoring (steps 13–15) plug in after "topics".

NUC Core Reference documents in a session are processed but treated as the
comparison baseline: they are excluded from corpus keywords, skill demand and
topic modelling so the prescribed core does not count as "demand".
"""
import time
from datetime import datetime, timezone

import numpy as np
from flask import current_app
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload, undefer

from ..extensions import db
from ..models import AnalysisSession, Document, DocumentSession, NLPResult, SessionStatus, SourceCategory
from ..utils.audit import record_audit
from .embeddings import get_embedder, mean_embedding
from .ingestion import parse_document
from .ner import aggregate_skill_demand, extract_entities
from .preprocessing import preprocess
from .preprocessing.normalize import split_blocks
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
    if len(analysis_links) == len(links):
        warnings.append("No NUC Core Reference documents in this session; overlap detection will use the library's core references.")

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

    # --- persist
    timer.start("saving")
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
        "warnings": warnings,
    }
    session.status = SessionStatus.COMPLETED
    session.progress_stage = None
    session.error_message = None
    session.completed_at = datetime.now(timezone.utc)
    record_audit("SESSION_RUN_COMPLETED", "AnalysisSession", session.session_id,
                 {"total_seconds": session.pipeline_info["total_seconds"], "topics": len(topic_result.topics)},
                 user_id=session.user_id, commit=False)
    db.session.commit()
