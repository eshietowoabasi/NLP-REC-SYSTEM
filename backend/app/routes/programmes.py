"""Academic programme and curriculum benchmark management."""

from __future__ import annotations

from flask import Blueprint, Response, request
from flask_login import current_user
from pydantic import ValidationError
from sqlalchemy import select

from app.audit import AuditAction, record_audit
from app.auth.decorators import login_required, role_required
from app.extensions import db
from app.models import NucCoreVersion, Programme, SourceCategory, UserRole
from app.schemas.documents import NucCoreUploadForm, NucCoreVersionOut
from app.schemas.programmes import ProgrammeCreate, ProgrammeOut
from app.services.ingestion.validation import UploadRejectedError
from app.tasks.queue import enqueue
from app.uploads import discard, store_upload
from app.utils.errors import ApiError
from app.utils.responses import success
from app.utils.validation import parse_body, validation_details

bp = Blueprint("programmes", __name__, url_prefix="/programmes")


def programme_json(programme: Programme) -> dict:
    return ProgrammeOut.model_validate(programme).model_dump(mode="json")


def version_json(version: NucCoreVersion | None) -> dict | None:
    if version is None:
        return None
    return NucCoreVersionOut.model_validate(version).model_dump(mode="json")


def get_programme_or_404(programme_id: int) -> Programme:
    programme = db.session.get(Programme, programme_id)
    if programme is None:
        raise ApiError("NOT_FOUND", "Programme not found.", 404)
    return programme


@bp.get("")
@login_required
def list_programmes() -> tuple[Response, int]:
    programmes = db.session.scalars(
        select(Programme)
        .where(Programme.is_active.is_(True))
        .order_by(Programme.name)
    ).all()
    return success([programme_json(programme) for programme in programmes])


@bp.post("")
@role_required(UserRole.ADMIN)
def create_programme() -> tuple[Response, int]:
    data = parse_body(ProgrammeCreate)

    if db.session.scalar(
        select(Programme).where(Programme.name.ilike(data.name))
    ) is not None:
        raise ApiError(
            "CONFLICT",
            "A programme with that name already exists.",
            409,
        )

    if data.discipline_code and db.session.scalar(
        select(Programme).where(
            Programme.discipline_code == data.discipline_code
        )
    ) is not None:
        raise ApiError(
            "CONFLICT",
            "That discipline code is already in use.",
            409,
        )

    programme = Programme(**data.model_dump())
    db.session.add(programme)
    db.session.commit()
    db.session.refresh(programme)

    return success(programme_json(programme), 201)


@bp.get("/<int:programme_id>")
@login_required
def get_programme(programme_id: int) -> tuple[Response, int]:
    return success(programme_json(get_programme_or_404(programme_id)))


@bp.get("/<int:programme_id>/benchmarks")
@login_required
def list_benchmarks(programme_id: int) -> tuple[Response, int]:
    programme = get_programme_or_404(programme_id)

    versions = db.session.scalars(
        select(NucCoreVersion)
        .where(NucCoreVersion.programme_id == programme.id)
        .order_by(NucCoreVersion.id.desc())
    ).all()

    active = next(
        (version for version in versions if version.is_active),
        None,
    )

    latest = versions[0] if versions else None

    return success(
        {
            "programme": programme_json(programme),
            "active": version_json(active),
            "latest": version_json(latest),
            "versions": [
                version_json(version)
                for version in versions
            ],
        }
    )


@bp.post("/<int:programme_id>/benchmarks")
@role_required(UserRole.ADMIN)
def upload_benchmark(programme_id: int) -> tuple[Response, int]:
    programme = get_programme_or_404(programme_id)

    try:
        form = NucCoreUploadForm.model_validate(
            {
                "version_label":
                    request.form.get("version_label", "")
            }
        )
    except ValidationError as exc:
        raise ApiError(
            "VALIDATION_ERROR",
            "Some fields are invalid.",
            422,
            validation_details(exc),
        ) from exc

    upload = request.files.get("file")

    if upload is None:
        raise ApiError(
            "VALIDATION_ERROR",
            "Some fields are invalid.",
            422,
            {
                "fields": {
                    "file": [
                        "Choose a curriculum benchmark document to upload."
                    ]
                }
            },
        )

    try:
        document = store_upload(
            upload,
            SourceCategory.NUC_CORE,
            current_user,
        )
    except UploadRejectedError as exc:
        raise ApiError(
            "VALIDATION_ERROR",
            str(exc),
            422,
            {"fields": {"file": [str(exc)]}},
        ) from exc

    try:
        version = NucCoreVersion(
            programme_id=programme.id,
            document_id=document.id,
            version_label=form.version_label,
            is_active=False,
            uploaded_by_id=current_user.id,
        )

        db.session.add(version)
        db.session.flush()

        record_audit(
            AuditAction.NUC_CORE_UPLOADED,
            "curriculum_benchmark",
            version.id,
            {
                "programme_id": programme.id,
                "programme": programme.name,
                "version_label": version.version_label,
                "filename": document.original_filename,
            },
        )

        db.session.commit()

    except Exception:
        db.session.rollback()
        discard([document])
        raise

    enqueue(
        "app.tasks.ingestion.ingest_document",
        document.id,
    )

    db.session.refresh(version)

    return success(version_json(version), 201)
