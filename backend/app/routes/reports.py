"""Report generation and history (spec §12 reports, §16; docs/DECISIONS.md, D8)."""
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_login import current_user
from sqlalchemy import select

from ..extensions import db
from ..models import Report, ReportFormat
from ..services.ingestion import delete_file, save_bytes
from ..services.reports import RENDERERS, build_report
from ..utils.audit import record_audit
from ..utils.errors import NotFoundError
from ..utils.pagination import paginate
from ..utils.params import parse_enum
from ..utils.rbac import WRITE_ROLES, login_required, roles_required
from .results import _completed_session

sessions_bp = Blueprint("session_reports", __name__)
bp = Blueprint("reports", __name__)

MIME_TYPES = {
    ReportFormat.PDF: "application/pdf",
    ReportFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def get_report_or_404(report_id):
    report = db.session.get(Report, report_id)
    if report is None:
        raise NotFoundError("Report not found")
    return report


@sessions_bp.post("/<int:session_id>/reports")
@roles_required(*WRITE_ROLES)
def generate_report(session_id):
    session = _completed_session(session_id)
    payload = request.get_json(silent=True) or {}
    report_format = parse_enum(ReportFormat, payload.get("format", "pdf"), "format")

    content = build_report(session.session_id, current_user, current_app.config["INSTITUTION_NAME"])
    data = RENDERERS[report_format.value](content)
    path = save_bytes(data, current_app.config["REPORT_FOLDER"], report_format.value)
    report = Report(session_id=session.session_id, user_id=current_user.user_id,
                    report_format=report_format, file_path=path, file_size=len(data))
    db.session.add(report)
    try:
        db.session.flush()
        record_audit("REPORT_GENERATE", "Report", report.report_id,
                     {"session_id": session.session_id, "format": report_format.value}, commit=False)
        db.session.commit()
    except Exception:
        db.session.rollback()
        delete_file(path)
        raise
    return jsonify({"success": True, "report": report.to_dict()}), 201


@bp.get("")
@login_required
def list_reports():
    query = select(Report).order_by(Report.created_at.desc(), Report.report_id.desc())
    if session_id := request.args.get("session_id", type=int):
        query = query.where(Report.session_id == session_id)
    return jsonify(paginate(query, Report.to_dict))


@bp.get("/<int:report_id>")
@login_required
def get_report(report_id):
    return jsonify({"success": True, "report": get_report_or_404(report_id).to_dict()})


@bp.get("/<int:report_id>/download")
@login_required
def download_report(report_id):
    report = get_report_or_404(report_id)
    try:
        handle = open(report.file_path, "rb")
    except FileNotFoundError:
        raise NotFoundError("The report file is no longer available; generate a new report")
    stamp = (report.created_at or datetime.now(timezone.utc)).strftime("%Y%m%d-%H%M")
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in report.session.session_name)[:60]
    return send_file(
        handle,
        mimetype=MIME_TYPES[report.report_format],
        as_attachment=True,
        download_name=f"NLP-RS_{safe_name}_{stamp}.{report.report_format.value}",
    )
