"""Analysis sessions: create, run, retry, inspect and delete."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response
from flask_login import current_user
from sqlalchemy import func, select

from app.audit import AuditAction, record_audit
from app.auth.decorators import EDITOR_ROLES, login_required, role_required
from app.extensions import db
from app.models import (
    AnalysisSession,
    DocumentSession,
    NLPResult,
    NLPResultType,
    Recommendation,
    SessionStatus,
)
from app.schemas.documents import UserRef
from app.schemas.sessions import (
    NucCoreRef,
    SessionCreate,
    SessionDetailOut,
    SessionDocumentOut,
    SessionListQuery,
    SessionSummaryOut,
)
from app.sessions import (
    active_nuc_core,
    build_parameters,
    check_documents,
    clear_results,
    default_parameters,
    link_documents,
)
from app.settings import get_setting
from app.tasks.queue import enqueue
from app.utils.errors import ApiError
from app.utils.responses import success
from app.utils.validation import paginate, parse_body, parse_query

bp = Blueprint("sessions", __name__, url_prefix="/sessions")

ANALYSIS_JOB = "app.tasks.analysis.run_session"


def _counts(session_ids: list[int]) -> tuple[dict[int, int], dict[int, int]]:
    """Document and recommendation counts per session, in two queries."""
    if not session_ids:
        return {}, {}
    documents = dict(
        db.session.execute(
            select(DocumentSession.session_id, func.count())
            .where(DocumentSession.session_id.in_(session_ids))
            .group_by(DocumentSession.session_id)
        ).all()
    )
    recommendations = dict(
        db.session.execute(
            select(Recommendation.session_id, func.count())
            .where(Recommendation.session_id.in_(session_ids))
            .group_by(Recommendation.session_id)
        ).all()
    )
    return documents, recommendations


def summary_json(session: AnalysisSession, documents: int, recommendations: int) -> dict[str, Any]:
    return SessionSummaryOut(
        id=session.id,
        session_name=session.session_name,
        status=session.status,
        current_stage=session.current_stage,
        progress_percent=session.progress_percent,
        created_by=UserRef.model_validate(session.created_by),
        document_count=documents,
        recommendation_count=recommendations,
        created_at=session.created_at,
        started_at=session.started_at,
        completed_at=session.completed_at,
    ).model_dump(mode="json")


def detail_json(session: AnalysisSession) -> dict[str, Any]:
    documents, recommendations = _counts([session.id])
    topics = db.session.scalar(
        select(NLPResult.payload).where(
            NLPResult.session_id == session.id, NLPResult.result_type == NLPResultType.TOPICS
        )
    )
    version = session.nuc_core_version
    data = SessionDetailOut(
        **SessionSummaryOut.model_validate(
            summary_json(session, documents.get(session.id, 0), recommendations.get(session.id, 0))
        ).model_dump(),
        parameter_config=session.parameter_config or {},
        stage_timings=session.stage_timings or {},
        error_message=session.error_message,
        nuc_core_version=NucCoreRef.model_validate(version) if version else None,
        documents=[
            SessionDocumentOut.model_validate(link.document) for link in session.document_links
        ],
        topic_count=topics.get("topic_count") if topics else None,
    )
    return data.model_dump(mode="json")


def get_session_or_404(session_id: int) -> AnalysisSession:
    session = db.session.get(AnalysisSession, session_id)
    if session is None:
        raise ApiError("NOT_FOUND", "Analysis session not found.", 404)
    return session


def require_nuc_core() -> None:
    if active_nuc_core() is None:
        raise ApiError(
            "NO_NUC_CORE",
            "There is no active NUC core reference. An administrator must upload one before "
            "sessions can run.",
            409,
        )


def queue_run(session: AnalysisSession) -> None:
    """Mark the session as processing and queue the analysis job (the caller commits first)."""
    session.status = SessionStatus.PROCESSING
    session.current_stage = "queued"
    session.progress_percent = 0
    session.error_message = None
    session.stage_timings = {}
    session.started_at = None
    session.completed_at = None


@bp.get("")
@login_required
def list_sessions() -> tuple[Response, int]:
    """Sessions, newest first. Filters: ``status``, ``search`` (name)."""
    params = parse_query(SessionListQuery)
    query = select(AnalysisSession).order_by(
        AnalysisSession.created_at.desc(), AnalysisSession.id.desc()
    )
    if params.status is not None:
        query = query.where(AnalysisSession.status == params.status)
    if params.search:
        query = query.where(AnalysisSession.session_name.ilike(f"%{params.search}%"))
    sessions, meta = paginate(query, params.page, params.per_page)
    documents, recommendations = _counts([s.id for s in sessions])
    return success(
        {
            "items": [
                summary_json(s, documents.get(s.id, 0), recommendations.get(s.id, 0))
                for s in sessions
            ],
            "pagination": meta,
        }
    )


@bp.get("/defaults")
@login_required
def session_defaults() -> tuple[Response, int]:
    """Default parameters for a new session, the document limit and the NUC core status."""
    version = active_nuc_core()
    return success(
        {
            "parameters": default_parameters(),
            "max_documents": int(get_setting("max_documents_per_session")),
            "nuc_core_version": (
                NucCoreRef.model_validate(version).model_dump() if version else None
            ),
        }
    )


@bp.post("")
@role_required(*EDITOR_ROLES)
def create_session() -> tuple[Response, int]:
    """Create a session; with ``"run": true`` it is queued for analysis straight away."""
    data = parse_body(SessionCreate)
    documents = check_documents(data.document_ids)
    if data.run:
        require_nuc_core()
    session = AnalysisSession(
        created_by_id=current_user.id,
        session_name=data.session_name,
        parameter_config=build_parameters(data.parameters),
    )
    link_documents(session, documents)
    db.session.add(session)
    db.session.flush()
    record_audit(
        AuditAction.SESSION_CREATED,
        "analysis_session",
        session.id,
        {"session_name": session.session_name, "documents": data.document_ids},
    )
    if data.run:
        queue_run(session)
        record_audit(AuditAction.SESSION_RUN, "analysis_session", session.id)
    db.session.commit()
    if data.run:
        enqueue(ANALYSIS_JOB, session.id)
    db.session.refresh(session)
    return success(detail_json(session), 201)


@bp.get("/<int:session_id>")
@login_required
def get_session(session_id: int) -> tuple[Response, int]:
    """Status, stage, progress, documents, parameters and NUC core version of a session."""
    return success(detail_json(get_session_or_404(session_id)))


@bp.post("/<int:session_id>/run")
@role_required(*EDITOR_ROLES)
def run_session(session_id: int) -> tuple[Response, int]:
    """Queue a pending session for analysis (202 Accepted; poll the session for progress)."""
    session = get_session_or_404(session_id)
    if session.status != SessionStatus.PENDING:
        hint = " Use retry for a failed session." if session.status == SessionStatus.FAILED else ""
        raise ApiError("CONFLICT", f"This session is already {session.status}.{hint}", 409)
    require_nuc_core()
    queue_run(session)
    record_audit(AuditAction.SESSION_RUN, "analysis_session", session.id)
    db.session.commit()
    enqueue(ANALYSIS_JOB, session.id)
    db.session.refresh(session)
    return success(detail_json(session), 202)


@bp.post("/<int:session_id>/retry")
@role_required(*EDITOR_ROLES)
def retry_session(session_id: int) -> tuple[Response, int]:
    """Run a failed session again from the start (202 Accepted)."""
    session = get_session_or_404(session_id)
    if session.status != SessionStatus.FAILED:
        raise ApiError("CONFLICT", "Only failed sessions can be retried.", 409)
    require_nuc_core()
    clear_results(session)
    queue_run(session)
    record_audit(AuditAction.SESSION_RUN, "analysis_session", session.id, {"retry": True})
    db.session.commit()
    enqueue(ANALYSIS_JOB, session.id)
    db.session.refresh(session)
    return success(detail_json(session), 202)


@bp.delete("/<int:session_id>")
@role_required(*EDITOR_ROLES)
def delete_session(session_id: int) -> tuple[Response, int]:
    """Delete a session and its results (documents are kept)."""
    session = get_session_or_404(session_id)
    if session.status == SessionStatus.PROCESSING:
        raise ApiError("CONFLICT", "The session is running; wait until it finishes.", 409)
    record_audit(
        AuditAction.SESSION_DELETED,
        "analysis_session",
        session.id,
        {"session_name": session.session_name},
    )
    db.session.delete(session)
    db.session.commit()
    return success({"deleted": True})
