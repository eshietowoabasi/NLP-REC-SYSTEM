"""NUC CCMAS core reference: the baseline every candidate topic is compared against.

Exactly one version is active at a time. A new version becomes active automatically once its
document has been parsed successfully; until then the previous version stays active.
Everyone can see which version is active (planners need to know before running a session);
only admins can upload.
"""

from __future__ import annotations

from flask import Blueprint, Response, request
from flask_login import current_user
from pydantic import ValidationError
from sqlalchemy import select

from app.audit import AuditAction, record_audit
from app.auth.decorators import login_required, role_required
from app.extensions import db
from app.models import NucCoreVersion, SourceCategory, UserRole
from app.schemas.documents import NucCoreUploadForm, NucCoreVersionOut
from app.services.ingestion.validation import UploadRejectedError
from app.tasks.queue import enqueue
from app.uploads import discard, store_upload
from app.utils.errors import ApiError
from app.utils.responses import success
from app.utils.validation import validation_details

bp = Blueprint("nuc_core", __name__, url_prefix="/nuc-core")


def version_json(version: NucCoreVersion | None) -> dict | None:
    if version is None:
        return None
    return NucCoreVersionOut.model_validate(version).model_dump(mode="json")


@bp.get("")
@login_required
def current_nuc_core() -> tuple[Response, int]:
    """The active version (null if none) and the most recent upload (may still be processing)."""
    active = db.session.scalar(select(NucCoreVersion).where(NucCoreVersion.is_active.is_(True)))
    latest = db.session.scalar(select(NucCoreVersion).order_by(NucCoreVersion.id.desc()).limit(1))
    return success({"active": version_json(active), "latest": version_json(latest)})


@bp.get("/versions")
@login_required
def list_versions() -> tuple[Response, int]:
    """Every uploaded version, newest first."""
    versions = db.session.scalars(select(NucCoreVersion).order_by(NucCoreVersion.id.desc()))
    return success([version_json(version) for version in versions])


@bp.post("")
@role_required(UserRole.ADMIN)
def upload_version() -> tuple[Response, int]:
    """Upload a new version (multipart: ``file`` and ``version_label``)."""
    try:
        form = NucCoreUploadForm.model_validate(
            {"version_label": request.form.get("version_label", "")}
        )
    except ValidationError as exc:
        raise ApiError(
            "VALIDATION_ERROR", "Some fields are invalid.", 422, validation_details(exc)
        ) from exc
    upload = request.files.get("file")
    if upload is None:
        raise ApiError(
            "VALIDATION_ERROR",
            "Some fields are invalid.",
            422,
            {"fields": {"file": ["Choose the NUC core document to upload."]}},
        )
    try:
        document = store_upload(upload, SourceCategory.NUC_CORE, current_user)
    except UploadRejectedError as exc:
        raise ApiError("VALIDATION_ERROR", str(exc), 422, {"fields": {"file": [str(exc)]}}) from exc
    try:
        version = NucCoreVersion(
            document_id=document.id,
            version_label=form.version_label,
            is_active=False,
            uploaded_by_id=current_user.id,
        )
        db.session.add(version)
        db.session.flush()
        record_audit(
            AuditAction.NUC_CORE_UPLOADED,
            "nuc_core_version",
            version.id,
            {"version_label": version.version_label, "filename": document.original_filename},
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        discard([document])
        raise
    enqueue("app.tasks.ingestion.ingest_document", document.id)
    db.session.refresh(version)
    return success(version_json(version), 201)
