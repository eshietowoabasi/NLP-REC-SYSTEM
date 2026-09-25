"""Reports: queue generation for a session, list, inspect, download and delete.

Report files live in the storage volume under UUID names and are only served through the
authorised download endpoint.
"""

from __future__ import annotations

import re
from typing import Any

from flask import Blueprint, Response, send_file
from flask_login import current_user
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.audit import AuditAction, record_audit
from app.auth.decorators import EDITOR_ROLES, login_required, role_required
from app.extensions import db
from app.models import AnalysisSession, Report, ReportFormat, ReportStatus, SessionStatus
from app.schemas.documents import UserRef
from app.schemas.reports import ReportCreate, ReportListQuery, ReportOut, ReportSessionRef
from app.services.storage import get_storage
from app.tasks.queue import enqueue
from app.utils.errors import ApiError
from app.utils.responses import success
from app.utils.validation import paginate, parse_body, parse_query

bp = Blueprint("reports", __name__)

REPORT_JOB = "app.tasks.reports.generate_report"
MIME_TYPES = {
    ReportFormat.PDF: "application/pdf",
    ReportFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def report_json(report: Report) -> dict[str, Any]:
    size = None
    if report.status == ReportStatus.COMPLETED and report.file_path:
        path = get_storage().path(report.file_path, area="reports")
        size = path.stat().st_size if path.exists() else None
    return ReportOut(
        id=report.id,
        session=ReportSessionRef.model_validate(report.session),
        format=report.format,
        sections=list(report.sections or []),
        status=report.status,
        error_message=report.error_message,
        file_size=size,
        created_by=UserRef.model_validate(report.created_by),
        created_at=report.created_at,
        completed_at=report.completed_at,
    ).model_dump(mode="json")


def get_report_or_404(report_id: int) -> Report:
    report = db.session.get(Report, report_id)
    if report is None:
        raise ApiError("NOT_FOUND", "Report not found.", 404)
    return report


def download_name(report: Report) -> str:
    """A readable, filesystem-safe file name.

    For example ``NLP-RS report - 2026 review - 25 Sep 2026.pdf``.
    """
    name = re.sub(r"[^\w\- ]+", "", report.session.session_name).strip()[:80] or "session"
    date = report.created_at.strftime("%d %b %Y")
    return f"NLP-RS report - {name} - {date}.{report.format}"


@bp.post("/sessions/<int:session_id>/reports")
@role_required(*EDITOR_ROLES)
def create_report(session_id: int) -> tuple[Response, int]:
    """Queue a report of a completed session (202 Accepted; poll the report for its status)."""
    session = db.session.get(AnalysisSession, session_id)
    if session is None:
        raise ApiError("NOT_FOUND", "Analysis session not found.", 404)
    if session.status != SessionStatus.COMPLETED:
        raise ApiError(
            "RESULTS_NOT_READY", "Reports can only be generated for completed sessions.", 409
        )
    data = parse_body(ReportCreate)
    report = Report(
        session_id=session.id,
        format=data.format,
        sections=list(data.sections),
        created_by_id=current_user.id,
    )
    db.session.add(report)
    db.session.flush()
    record_audit(
        AuditAction.REPORT_GENERATED,
        "report",
        report.id,
        {"session_id": session.id, "format": str(data.format), "sections": list(data.sections)},
    )
    db.session.commit()
    enqueue(REPORT_JOB, report.id)
    db.session.refresh(report)
    return success(report_json(report), 202)


@bp.get("/reports")
@login_required
def list_reports() -> tuple[Response, int]:
    """Reports, newest first. Filters: ``session_id``, ``status``, ``format``."""
    params = parse_query(ReportListQuery)
    query = (
        select(Report)
        .options(selectinload(Report.session), selectinload(Report.created_by))
        .order_by(Report.created_at.desc(), Report.id.desc())
    )
    if params.session_id is not None:
        query = query.where(Report.session_id == params.session_id)
    if params.status is not None:
        query = query.where(Report.status == params.status)
    if params.format is not None:
        query = query.where(Report.format == params.format)
    reports, meta = paginate(query, params.page, params.per_page)
    return success({"items": [report_json(r) for r in reports], "pagination": meta})


@bp.get("/reports/<int:report_id>")
@login_required
def get_report(report_id: int) -> tuple[Response, int]:
    return success(report_json(get_report_or_404(report_id)))


@bp.get("/reports/<int:report_id>/download")
@login_required
def download_report(report_id: int) -> Response:
    """Download a generated report file."""
    report = get_report_or_404(report_id)
    if report.status != ReportStatus.COMPLETED or not report.file_path:
        raise ApiError("REPORT_NOT_READY", "This report has not been generated yet.", 409)
    path = get_storage().path(report.file_path, area="reports")
    if not path.exists():
        raise ApiError("NOT_FOUND", "The report file is missing; generate it again.", 404)
    return send_file(
        path,
        mimetype=MIME_TYPES[ReportFormat(report.format)],
        as_attachment=True,
        download_name=download_name(report),
    )


@bp.delete("/reports/<int:report_id>")
@role_required(*EDITOR_ROLES)
def delete_report(report_id: int) -> tuple[Response, int]:
    """Delete a report and its file (not while it is being generated)."""
    report = get_report_or_404(report_id)
    if report.status in (ReportStatus.QUEUED, ReportStatus.PROCESSING):
        raise ApiError("CONFLICT", "The report is being generated; wait until it finishes.", 409)
    file_path = report.file_path
    record_audit(
        AuditAction.REPORT_DELETED,
        "report",
        report.id,
        {"session_id": report.session_id, "format": str(report.format)},
    )
    db.session.delete(report)
    db.session.commit()
    if file_path:
        get_storage().delete(file_path, area="reports")
    return success({"deleted": True})
