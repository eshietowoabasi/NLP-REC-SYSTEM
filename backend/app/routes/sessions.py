"""Analysis sessions (spec §6 steps 5–6). Running the pipeline arrives with the NLP stages."""
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user
from sqlalchemy import select, update

from ..extensions import db
from ..models import AnalysisSession, Document, DocumentSession, DocumentStatus, Role, SessionStatus
from ..schemas.session_config import build_session_config
from ..utils.audit import record_audit
from ..utils.errors import ApiError, ConflictError, NotFoundError, ValidationError
from ..utils.pagination import paginate
from ..utils.params import parse_enum
from ..utils.rbac import WRITE_ROLES, login_required, roles_required

# A Completed session keeps its results (and, later, planner decisions); re-analysing
# means creating a new session.
RUNNABLE_STATUSES = (SessionStatus.PENDING, SessionStatus.FAILED)

bp = Blueprint("sessions", __name__)


def get_session_or_404(session_id):
    session = db.session.get(AnalysisSession, session_id)
    if session is None:
        raise NotFoundError("Analysis session not found")
    return session


def _validate_document_ids(raw_ids):
    limit = current_app.config["MAX_DOCUMENTS_PER_SESSION"]
    if not isinstance(raw_ids, list) or not raw_ids:
        raise ValidationError("document_ids must be a non-empty list", details={"document_ids": "Required"})
    if any(isinstance(i, bool) or not isinstance(i, int) for i in raw_ids):
        raise ValidationError("document_ids must be integers", details={"document_ids": "Must be integers"})
    ids = list(dict.fromkeys(raw_ids))  # de-duplicate, keep order
    if len(ids) > limit:
        raise ValidationError(
            f"A session can include at most {limit} documents",
            details={"document_ids": f"{len(ids)} provided, maximum is {limit}"},
        )

    documents = {
        d.document_id: d
        for d in db.session.execute(select(Document).where(Document.document_id.in_(ids))).scalars()
    }
    missing = [i for i in ids if i not in documents]
    unparsed = [i for i in ids if i in documents and documents[i].processing_status is not DocumentStatus.PARSED]
    if missing or unparsed:
        details = {}
        if missing:
            details["missing"] = missing
        if unparsed:
            details["not_parsed"] = unparsed
        raise ValidationError("Some documents cannot be analysed", details=details)
    return ids


@bp.get("")
@login_required
def list_sessions():
    query = select(AnalysisSession).order_by(AnalysisSession.created_at.desc(), AnalysisSession.session_id.desc())
    if status := request.args.get("status"):
        query = query.where(AnalysisSession.status == parse_enum(SessionStatus, status, "status"))
    if request.args.get("mine") in ("1", "true"):
        query = query.where(AnalysisSession.user_id == current_user.user_id)
    return jsonify(paginate(query, AnalysisSession.to_dict))


@bp.post("")
@roles_required(*WRITE_ROLES)
def create_session():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object")

    name = (payload.get("session_name") or "").strip() if isinstance(payload.get("session_name"), str) else ""
    if not name:
        raise ValidationError("session_name is required", details={"session_name": "Required"})
    config = build_session_config(payload.get("parameter_config"))
    document_ids = _validate_document_ids(payload.get("document_ids"))

    session = AnalysisSession(
        user_id=current_user.user_id, session_name=name[:255], parameter_config=config
    )
    session.document_links = [
        DocumentSession(document_id=doc_id, processing_order=order)
        for order, doc_id in enumerate(document_ids, start=1)
    ]
    db.session.add(session)
    db.session.flush()
    record_audit("SESSION_CREATE", "AnalysisSession", session.session_id,
                 {"session_name": session.session_name, "document_count": len(document_ids)}, commit=False)
    db.session.commit()
    return jsonify({"success": True, "session": session.to_dict(include_documents=True)}), 201


@bp.get("/<int:session_id>")
@login_required
def get_session(session_id):
    return jsonify({"success": True, "session": get_session_or_404(session_id).to_dict(include_documents=True)})


@bp.delete("/<int:session_id>")
@roles_required(*WRITE_ROLES)
def delete_session(session_id):
    session = get_session_or_404(session_id)
    if current_user.role is not Role.ADMIN and session.user_id != current_user.user_id:
        raise ApiError("You can only delete your own sessions", code="FORBIDDEN", status_code=403)
    if session.status is SessionStatus.PROCESSING:
        raise ConflictError("Cannot delete a session while it is processing", code="SESSION_PROCESSING")
    record_audit("SESSION_DELETE", "AnalysisSession", session.session_id,
                 {"session_name": session.session_name}, commit=False)
    db.session.delete(session)
    db.session.commit()
    return jsonify({"success": True})


@bp.post("/<int:session_id>/run")
@roles_required(*WRITE_ROLES)
def run_session(session_id):
    """Start the NLP pipeline in the background; returns 202 immediately (spec §12.2, §15)."""
    session = get_session_or_404(session_id)
    if current_user.role is not Role.ADMIN and session.user_id != current_user.user_id:
        raise ApiError("You can only run your own sessions", code="FORBIDDEN", status_code=403)
    previous_status = session.status

    from ..services.analysis import NO_CORE_MESSAGE, core_reference_available

    # Overlap detection (spec §9) needs the NUC core; fail fast instead of mid-run.
    if session.status in RUNNABLE_STATUSES and not core_reference_available():
        raise ConflictError(NO_CORE_MESSAGE, code="NO_CORE_REFERENCE")

    # Conditional update so two concurrent requests cannot both start the same session.
    claimed = db.session.execute(
        update(AnalysisSession)
        .where(AnalysisSession.session_id == session_id, AnalysisSession.status.in_(RUNNABLE_STATUSES))
        .values(status=SessionStatus.PROCESSING, progress_stage="queued", error_message=None, completed_at=None,
                heartbeat_at=datetime.now(timezone.utc))
    ).rowcount
    if not claimed:
        db.session.rollback()
        raise ConflictError(
            f"Session cannot be run while {previous_status.value}",
            code="SESSION_NOT_RUNNABLE",
            details={"status": previous_status.value, "runnable_statuses": [s.value for s in RUNNABLE_STATUSES]},
        )
    record_audit("SESSION_RUN", "AnalysisSession", session_id, commit=False)
    db.session.commit()

    from ..tasks import run_analysis_task

    try:
        run_analysis_task.delay(session_id)
    except Exception:
        current_app.logger.exception("Could not queue analysis for session %s", session_id)
        db.session.execute(
            update(AnalysisSession)
            .where(AnalysisSession.session_id == session_id)
            .values(status=previous_status, progress_stage=None)
        )
        db.session.commit()
        raise ApiError("The analysis queue is unavailable; try again shortly",
                       code="QUEUE_UNAVAILABLE", status_code=503)

    db.session.expire_all()
    session = get_session_or_404(session_id)
    return jsonify({
        "success": True,
        "session_id": session_id,
        "status": session.status.value,
        "message": "Analysis started",
        "progress": session.progress(),
    }), 202
