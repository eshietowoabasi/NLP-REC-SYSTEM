"""Academic programme and curriculum benchmark management."""

from __future__ import annotations

from flask import Blueprint, Response, request
from flask_login import current_user
from pydantic import ValidationError
from sqlalchemy import func, select

from app.access import programme_condition, require_programme
from app.audit import AuditAction, record_audit
from app.auth.decorators import login_required, role_required
from app.extensions import db
from app.models import (
    NUC_DISCIPLINE_NAMES,
    NucCoreVersion,
    NucDiscipline,
    Programme,
    SkillPattern,
    SourceCategory,
    UserRole,
)
from app.schemas.documents import NucCoreUploadForm, NucCoreVersionOut
from app.schemas.programmes import (
    DisciplineOut,
    ProgrammeCreate,
    ProgrammeListQuery,
    ProgrammeOut,
    ProgrammeUpdate,
)
from app.services.ingestion.validation import UploadRejectedError
from app.tasks.queue import enqueue
from app.uploads import discard, store_upload
from app.utils.errors import ApiError
from app.utils.responses import success
from app.utils.validation import parse_body, parse_query, validation_details

bp = Blueprint("programmes", __name__, url_prefix="/programmes")


def programme_json(programme: Programme) -> dict:
    return ProgrammeOut.model_validate(programme).model_dump(mode="json")


def version_json(version: NucCoreVersion | None) -> dict | None:
    if version is None:
        return None
    return NucCoreVersionOut.model_validate(version).model_dump(mode="json")


def get_programme_or_404(programme_id: int) -> Programme:
    """The programme, or 404 if it does not exist or is not one of the user's."""
    programme = db.session.get(Programme, programme_id)
    if programme is None:
        raise ApiError("NOT_FOUND", "Programme not found.", 404)
    require_programme(programme.id)
    return programme


def _check_unique(name: str | None, code: str | None, exclude_id: int | None = None) -> None:
    """409 if another programme already has this name or discipline code (any letter case)."""
    others = select(Programme)
    if exclude_id is not None:
        others = others.where(Programme.id != exclude_id)
    if name and db.session.scalar(
        others.where(func.lower(Programme.name) == name.lower()).limit(1)
    ):
        raise ApiError(
            "CONFLICT",
            "A programme with that name already exists.",
            409,
            {"fields": {"name": ["A programme with that name already exists."]}},
        )
    if code and db.session.scalar(
        others.where(func.lower(Programme.discipline_code) == code.lower()).limit(1)
    ):
        raise ApiError(
            "CONFLICT",
            "That discipline code is already in use.",
            409,
            {"fields": {"discipline_code": ["That discipline code is already in use."]}},
        )


@bp.get("/disciplines")
@login_required
def list_disciplines() -> tuple[Response, int]:
    """The 17 NUC CCMAS disciplines with how many distinct skills each list has; ``general``
    counts the skills every programme uses."""
    counts = dict(
        db.session.execute(
            select(SkillPattern.discipline, func.count(func.distinct(SkillPattern.canonical_name)))
            .where(SkillPattern.is_active.is_(True))
            .group_by(SkillPattern.discipline)
        ).all()
    )
    return success(
        {
            "general_skills": counts.get(None, 0),
            "disciplines": [
                DisciplineOut(
                    value=d, name=NUC_DISCIPLINE_NAMES[d], skills=counts.get(d, 0)
                ).model_dump(mode="json")
                for d in NucDiscipline
            ],
        }
    )


@bp.get("")
@login_required
def list_programmes() -> tuple[Response, int]:
    """The user's active programmes by name (admins: all; ``include_inactive=true`` adds
    retired ones)."""
    params = parse_query(ProgrammeListQuery)
    query = select(Programme).where(programme_condition()).order_by(Programme.name)
    if not (params.include_inactive and current_user.role == UserRole.ADMIN):
        query = query.where(Programme.is_active.is_(True))
    return success([programme_json(programme) for programme in db.session.scalars(query)])


@bp.post("")
@role_required(UserRole.ADMIN)
def create_programme() -> tuple[Response, int]:
    """Add a programme (it starts without a benchmark or a job-collection profile)."""
    data = parse_body(ProgrammeCreate)
    _check_unique(data.name, data.discipline_code)

    programme = Programme(**data.model_dump())
    db.session.add(programme)
    db.session.flush()
    record_audit(
        AuditAction.PROGRAMME_CREATED,
        "programme",
        programme.id,
        {"name": programme.name, "discipline_code": programme.discipline_code},
    )
    db.session.commit()
    db.session.refresh(programme)

    return success(programme_json(programme), 201)


@bp.patch("/<int:programme_id>")
@role_required(UserRole.ADMIN)
def update_programme(programme_id: int) -> tuple[Response, int]:
    """Change a programme's details, or retire/restore it with ``is_active``.

    Programmes are never deleted: sessions, benchmarks and documents keep referring to them.
    A retired programme cannot be chosen for new sessions, uploads or collections. The last
    active programme cannot be retired.
    """
    programme = get_programme_or_404(programme_id)
    data = parse_body(ProgrammeUpdate)
    fields = data.model_fields_set
    if "name" in fields and data.name is None:
        raise ApiError(
            "VALIDATION_ERROR",
            "Some fields are invalid.",
            422,
            {"fields": {"name": ["Enter a name."]}},
        )
    _check_unique(
        data.name if "name" in fields else None,
        data.discipline_code if "discipline_code" in fields else None,
        exclude_id=programme.id,
    )
    if "is_active" in fields and data.is_active is False and programme.is_active:
        active_count = db.session.scalar(
            select(func.count()).select_from(Programme).where(Programme.is_active.is_(True))
        )
        if active_count <= 1:
            raise ApiError(
                "CONFLICT",
                "At least one programme must stay active.",
                409,
                {"fields": {"is_active": ["At least one programme must stay active."]}},
            )

    changes = {}
    for field in sorted(fields):
        value = getattr(data, field)
        if field == "is_active" and value is None:
            continue
        if getattr(programme, field) != value:
            changes[field] = {"from": getattr(programme, field), "to": value}
            setattr(programme, field, value)
    if changes:
        record_audit(AuditAction.PROGRAMME_UPDATED, "programme", programme.id, changes)
    db.session.commit()
    return success(programme_json(programme))


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
            "versions": [version_json(version) for version in versions],
        }
    )


@bp.post("/<int:programme_id>/benchmarks")
@role_required(UserRole.ADMIN)
def upload_benchmark(programme_id: int) -> tuple[Response, int]:
    programme = get_programme_or_404(programme_id)
    if not programme.is_active:
        raise ApiError("CONFLICT", "This programme has been retired.", 409)

    try:
        form = NucCoreUploadForm.model_validate(
            {"version_label": request.form.get("version_label", "")}
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
            {"fields": {"file": ["Choose a curriculum benchmark document to upload."]}},
        )

    try:
        document = store_upload(
            upload,
            SourceCategory.NUC_CORE,
            current_user,
            programme.id,
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
