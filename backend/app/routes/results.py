"""NLP results for a completed session (spec §12: results, keywords, entities, topics)."""
from flask import Blueprint, jsonify, request
from sqlalchemy import select
from sqlalchemy.orm import selectinload, undefer

from ..extensions import db
from ..models import AnalysisSession, DocumentSession, NLPResult, SessionStatus
from ..utils.errors import ConflictError, NotFoundError, ValidationError
from ..utils.rbac import login_required

bp = Blueprint("results", __name__)

ENTITY_LABELS = {"SKILL", "TOOL", "CERT", "ORG", "PRODUCT", "GPE"}


def _completed_session(session_id):
    session = db.session.get(AnalysisSession, session_id, options=[undefer(AnalysisSession.corpus_results)])
    if session is None:
        raise NotFoundError("Analysis session not found")
    if session.status is not SessionStatus.COMPLETED:
        raise ConflictError(
            "Results are available once the analysis has completed",
            code="RESULTS_NOT_READY",
            details={"status": session.status.value, "progress": session.progress()},
        )
    return session


def _document_results(session_id):
    links = db.session.execute(
        select(DocumentSession)
        .where(DocumentSession.session_id == session_id)
        .order_by(DocumentSession.processing_order)
        .options(selectinload(DocumentSession.document), selectinload(DocumentSession.nlp_results))
    ).scalars().all()
    for link in links:
        result = link.nlp_results[0] if link.nlp_results else None
        yield link.document, result


def _doc_header(document):
    return {
        "document_id": document.document_id,
        "title": document.title,
        "source_category": document.source_category.value,
    }


def _public_topics(topics):
    return [{k: v for k, v in t.items() if k != "embedding"} for t in topics]


@bp.get("/<int:session_id>/results")
@login_required
def all_results(session_id):
    session = _completed_session(session_id)
    corpus = session.corpus_results or {}
    documents = []
    for document, result in _document_results(session_id):
        entry = _doc_header(document)
        if result:
            entry.update({k: v for k, v in result.to_dict().items() if k not in ("doc_session_id", "document_id")})
        documents.append(entry)
    return jsonify({
        "success": True,
        "session_id": session_id,
        "pipeline_info": session.pipeline_info,
        "corpus": {**corpus, "topics": _public_topics(corpus.get("topics", []))},
        "documents": documents,
    })


@bp.get("/<int:session_id>/keywords")
@login_required
def keywords(session_id):
    session = _completed_session(session_id)
    return jsonify({
        "success": True,
        "session_id": session_id,
        "corpus_keywords": (session.corpus_results or {}).get("corpus_keywords", []),
        "documents": [
            {**_doc_header(d), "keywords": r.tfidf_keywords if r else []} for d, r in _document_results(session_id)
        ],
    })


@bp.get("/<int:session_id>/entities")
@login_required
def entities(session_id):
    session = _completed_session(session_id)
    label = request.args.get("label")
    if label and label not in ENTITY_LABELS:
        raise ValidationError("Invalid label", details={"label": f"Must be one of: {', '.join(sorted(ENTITY_LABELS))}"})

    def keep(rows):
        return [r for r in rows if not label or r["label"] == label]

    return jsonify({
        "success": True,
        "session_id": session_id,
        "skill_demand": keep((session.corpus_results or {}).get("skill_demand", [])),
        "documents": [
            {**_doc_header(d), "entities": keep(r.ner_entities or []) if r else []}
            for d, r in _document_results(session_id)
        ],
    })


@bp.get("/<int:session_id>/topics")
@login_required
def topics(session_id):
    session = _completed_session(session_id)
    corpus = session.corpus_results or {}
    info = session.pipeline_info or {}
    return jsonify({
        "success": True,
        "session_id": session_id,
        "method": corpus.get("topic_method"),
        "passage_count": info.get("passage_count"),
        "outlier_passages": info.get("outlier_passages"),
        "topics": _public_topics(corpus.get("topics", [])),
        "documents": [
            {**_doc_header(d), "topics": r.topics if r else []} for d, r in _document_results(session_id)
        ],
    })
