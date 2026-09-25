"""Dashboard: headline counts and recent sessions for the landing page."""

from __future__ import annotations

from flask import Blueprint, Response
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.auth.decorators import login_required
from app.extensions import db
from app.models import (
    AnalysisSession,
    CurriculumMap,
    Document,
    DocumentStatus,
    Recommendation,
    Report,
    SessionStatus,
    SourceCategory,
)
from app.routes.sessions import session_counts, summary_json
from app.sessions import active_nuc_core
from app.utils.responses import success

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

RECENT_SESSIONS = 5


def _grouped(column, *where) -> dict[str, int]:  # type: ignore[no-untyped-def]
    """``{value: count}`` of ``column`` over rows matching ``where``."""
    query = select(column, func.count()).group_by(column)
    for condition in where:
        query = query.where(condition)
    return {str(value): count for value, count in db.session.execute(query).all()}


@bp.get("/summary")
@login_required
def summary() -> tuple[Response, int]:
    """Counts of documents, sessions, recommendations awaiting review and mapped courses.

    Library documents exclude archived ones and the NUC core; recommendation counts cover
    completed sessions.
    """
    library = (
        Document.processing_status != DocumentStatus.ARCHIVED,
        Document.source_category != SourceCategory.NUC_CORE,
    )
    document_status = _grouped(Document.processing_status, *library)
    session_status = _grouped(AnalysisSession.status)
    completed = select(AnalysisSession.id).where(AnalysisSession.status == SessionStatus.COMPLETED)
    in_completed = Recommendation.session_id.in_(completed)
    decisions = {
        ("undecided" if value == "None" else value): count
        for value, count in _grouped(Recommendation.planner_decision, in_completed).items()
    }
    recent = list(
        db.session.scalars(
            select(AnalysisSession)
            .options(selectinload(AnalysisSession.created_by))
            .order_by(AnalysisSession.created_at.desc(), AnalysisSession.id.desc())
            .limit(RECENT_SESSIONS)
        )
    )
    documents, recommendations = session_counts([s.id for s in recent])
    version = active_nuc_core()
    return success(
        {
            "documents": {
                "total": sum(document_status.values()),
                "ready": document_status.get(DocumentStatus.READY, 0),
                "processing": document_status.get(DocumentStatus.UPLOADED, 0)
                + document_status.get(DocumentStatus.PARSING, 0),
                "failed": document_status.get(DocumentStatus.FAILED, 0),
                "by_category": _grouped(Document.source_category, *library),
            },
            "sessions": {
                "total": sum(session_status.values()),
                "by_status": {
                    status.value: session_status.get(status, 0) for status in SessionStatus
                },
            },
            "recommendations": {
                "total": sum(decisions.values()),
                "pending_review": decisions.get("undecided", 0),
                "accepted": decisions.get("accepted", 0),
                "rejected": decisions.get("rejected", 0),
                "flagged": decisions.get("flagged", 0),
            },
            "courses_mapped": db.session.scalar(select(func.count(CurriculumMap.id))) or 0,
            "reports": db.session.scalar(select(func.count(Report.id))) or 0,
            "nuc_core_version": (
                {"id": version.id, "version_label": version.version_label} if version else None
            ),
            "recent_sessions": [
                summary_json(s, documents.get(s.id, 0), recommendations.get(s.id, 0))
                for s in recent
            ],
        }
    )
