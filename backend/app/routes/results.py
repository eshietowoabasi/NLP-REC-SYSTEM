"""Session-level analysis results for the Evidence Dashboard.

Each endpoint returns the stored NLPResult payload of a completed session, enriched at read
time with document titles and NUC passage details.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response, request
from sqlalchemy import select

from app.auth.decorators import login_required
from app.extensions import db
from app.models import (
    AnalysisSession,
    Document,
    NLPResult,
    NLPResultType,
    NucCoreVersion,
    Passage,
    SessionStatus,
    SourceCategory,
)
from app.utils.errors import ApiError
from app.utils.responses import success

bp = Blueprint("results", __name__, url_prefix="/sessions")


def completed_session(session_id: int) -> AnalysisSession:
    session = db.session.get(AnalysisSession, session_id)
    if session is None:
        raise ApiError("NOT_FOUND", "Analysis session not found.", 404)
    if session.status != SessionStatus.COMPLETED:
        raise ApiError(
            "RESULTS_NOT_READY",
            "This session has no results yet; they are available once the analysis completes.",
            409,
        )
    return session


def payload(session: AnalysisSession, result_type: NLPResultType) -> dict[str, Any]:
    data = db.session.scalar(
        select(NLPResult.payload).where(
            NLPResult.session_id == session.id, NLPResult.result_type == result_type
        )
    )
    if data is None:
        raise ApiError("NOT_FOUND", "No results of this type are stored for the session.", 404)
    return dict(data)


@bp.get("/<int:session_id>/keywords")
@login_required
def keywords(session_id: int) -> tuple[Response, int]:
    """Top TF-IDF terms overall and per category. ``?category=`` limits to one category."""
    data = payload(completed_session(session_id), NLPResultType.TFIDF)
    category = request.args.get("category")
    if category:
        valid = {c.value for c in SourceCategory}
        if category not in valid:
            raise ApiError("VALIDATION_ERROR", "Unknown category.", 422)
        data["by_category"] = {category: data.get("by_category", {}).get(category, [])}
    return success(data)


@bp.get("/<int:session_id>/entities")
@login_required
def entities(session_id: int) -> tuple[Response, int]:
    """Skills, tools, languages and certifications: mentions and document frequency."""
    return success(payload(completed_session(session_id), NLPResultType.ENTITIES))


@bp.get("/<int:session_id>/topics")
@login_required
def topics(session_id: int) -> tuple[Response, int]:
    """Every discovered theme with keywords, size, strength and sample passages."""
    data = payload(completed_session(session_id), NLPResultType.TOPICS)
    document_ids = {
        sample["document_id"]
        for topic in data.get("topics", [])
        for sample in topic.get("samples", [])
    }
    titles = dict(
        db.session.execute(
            select(Document.id, Document.title).where(Document.id.in_(document_ids))
        ).all()
    )
    for topic in data.get("topics", []):
        for sample in topic.get("samples", []):
            sample["document_title"] = titles.get(sample["document_id"], "(deleted document)")
    return success(data)


@bp.get("/<int:session_id>/similarity")
@login_required
def similarity(session_id: int) -> tuple[Response, int]:
    """Overlap of every theme with the NUC core, with the closest NUC passage."""
    session = completed_session(session_id)
    data = payload(session, NLPResultType.SIMILARITY)
    passage_ids = {
        c["closest_nuc_passage"]["id"]
        for c in data.get("candidates", [])
        if c.get("closest_nuc_passage", {}).get("id")
    }
    pages = dict(
        db.session.execute(
            select(Passage.id, Passage.page_number).where(Passage.id.in_(passage_ids))
        ).all()
    )
    version = (
        db.session.get(NucCoreVersion, session.nuc_core_version_id)
        if session.nuc_core_version_id
        else None
    )
    for candidate in data.get("candidates", []):
        closest = candidate.get("closest_nuc_passage") or {}
        closest["page_number"] = pages.get(closest.get("id"))
    data["nuc_core_version"] = (
        {"id": version.id, "version_label": version.version_label} if version else None
    )
    return success(data)
