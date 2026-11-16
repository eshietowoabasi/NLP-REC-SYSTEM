"""Programme-specific labour-market harvesting API."""

from __future__ import annotations

from flask import Blueprint, Response
from flask_login import current_user
from sqlalchemy import select

from app.audit import AuditAction, record_audit
from app.auth.decorators import (
    EDITOR_ROLES,
    login_required,
    role_required,
)
from app.extensions import db
from app.harvesting import HARVEST_JOB_TIMEOUT, expire_stopped_runs, run_progress
from app.models import (
    JobHarvestRun,
    Programme,
    UserRole,
)
from app.schemas.harvest import (
    HarvestProfileUpdate,
    HarvestRunRequest,
)
from app.tasks.queue import enqueue
from app.utils.errors import ApiError
from app.utils.responses import success
from app.utils.validation import parse_body

bp = Blueprint(
    "harvest",
    __name__,
    url_prefix="/harvest",
)


def get_programme(
    programme_id: int,
) -> Programme:
    programme = db.session.get(
        Programme,
        programme_id,
    )

    if programme is None:
        raise ApiError(
            "NOT_FOUND",
            "Programme not found.",
            404,
        )

    return programme


def run_json(
    run: JobHarvestRun | None,
):
    if run is None:
        return None

    progress = run_progress(run)

    return {
        "id": run.id,
        "programme_id": run.programme_id,
        "status": run.status,
        "phase": progress.phase,
        "target_count": run.target_count,
        "pages_per_field": run.pages_per_field,
        "examined_count": run.examined_count,
        "found_count": run.found_count,
        "imported_count": run.imported_count,
        "skipped_count": run.skipped_count,
        "documents_ready": progress.documents_ready,
        "documents_processing": progress.documents_processing,
        "documents_failed": progress.documents_failed,
        "ready_document_ids": progress.ready_document_ids,
        "error_message": run.error_message,
        "created_at": run.created_at.isoformat(),
        "started_at": (run.started_at.isoformat() if run.started_at else None),
        "completed_at": (run.completed_at.isoformat() if run.completed_at else None),
    }


@bp.get("/programmes/<int:programme_id>")
@login_required
def harvest_state(
    programme_id: int,
) -> tuple[Response, int]:
    programme = get_programme(programme_id)
    expire_stopped_runs(programme.id)

    latest = db.session.scalar(
        select(JobHarvestRun)
        .where(JobHarvestRun.programme_id == programme.id)
        .order_by(JobHarvestRun.id.desc())
        .limit(1)
    )

    return success(
        {
            "programme": {
                "id": programme.id,
                "name": programme.name,
                "discipline_code": programme.discipline_code,
            },
            "profile": {
                "search_terms": programme.job_search_terms or [],
                "field_slugs": programme.job_field_slugs or [],
            },
            "latest_run": run_json(latest),
        }
    )


@bp.patch("/programmes/<int:programme_id>")
@role_required(UserRole.ADMIN)
def update_harvest_profile(
    programme_id: int,
) -> tuple[Response, int]:
    programme = get_programme(programme_id)

    data = parse_body(HarvestProfileUpdate)

    programme.job_search_terms = data.search_terms

    programme.job_field_slugs = data.field_slugs

    record_audit(
        AuditAction.HARVEST_PROFILE_UPDATED,
        "programme",
        programme.id,
        {"search_terms": data.search_terms, "field_slugs": data.field_slugs},
    )
    db.session.commit()

    return success(
        {
            "search_terms": programme.job_search_terms,
            "field_slugs": programme.job_field_slugs,
        }
    )


@bp.post("/programmes/<int:programme_id>/runs")
@role_required(*EDITOR_ROLES)
def start_harvest(
    programme_id: int,
) -> tuple[Response, int]:
    """Start collecting job adverts for the programme with its saved search profile.

    Admins and planners may start a collection (planners from New analysis); only admins change
    the profile. Collected adverts become the programme's job-advert documents.
    """
    programme = get_programme(programme_id)

    if not programme.is_active:
        raise ApiError("CONFLICT", "This programme has been retired.", 409)

    if not programme.job_search_terms:
        raise ApiError(
            "VALIDATION_ERROR",
            "Job collection is not set up for this programme yet. Ask an admin to add job"
            " titles on the Labour Market page.",
            422,
        )

    if not programme.job_field_slugs:
        raise ApiError(
            "VALIDATION_ERROR",
            "Job collection is not set up for this programme yet. Ask an admin to choose job"
            " fields on the Labour Market page.",
            422,
        )

    expire_stopped_runs(programme.id)

    latest_running = db.session.scalar(
        select(JobHarvestRun.id)
        .where(
            JobHarvestRun.programme_id == programme.id,
            JobHarvestRun.status.in_(["queued", "running"]),
        )
        .limit(1)
    )

    if latest_running is not None:
        raise ApiError(
            "CONFLICT",
            "A labour-market collection is already running for this programme.",
            409,
        )

    data = parse_body(HarvestRunRequest)

    run = JobHarvestRun(
        programme_id=programme.id,
        requested_by_id=current_user.id,
        target_count=data.target_count,
        pages_per_field=data.pages_per_field,
        status="queued",
    )

    db.session.add(run)
    db.session.flush()
    record_audit(
        AuditAction.HARVEST_STARTED,
        "job_harvest_run",
        run.id,
        {
            "programme_id": programme.id,
            "target_count": run.target_count,
            "pages_per_field": run.pages_per_field,
        },
    )
    db.session.commit()

    job_id = enqueue(
        "app.tasks.harvest.harvest_programme_jobs",
        run.id,
        timeout=HARVEST_JOB_TIMEOUT,
    )
    run = db.session.get(JobHarvestRun, run.id)
    if job_id is not None:
        run.rq_job_id = job_id
        db.session.commit()
    db.session.refresh(run)

    return success(
        run_json(run),
        202,
    )
