"""Labour-market collection API and job (synthetic adverts; the job site is never contacted)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.extensions import db
from app.harvesting import STOPPED_AFTER, STOPPED_MESSAGE, expire_stopped_runs
from app.models import AuditLog, Document, DocumentStatus, JobHarvestRun, UserRole
from app.services.harvesting.myjobmag import Collection, JobAdvert
from app.sessions import default_programme
from app.utils.time import utcnow

SENTENCES = [
    "The nurse assesses patients on admission and records vital signs accurately.",
    "Medication is administered safely and documented in the electronic health record.",
    "The role involves wound care, infection prevention and patient education.",
    "Candidates must hold a current licence from the Nursing and Midwifery Council of Nigeria.",
    "The nurse works with doctors, pharmacists and laboratory scientists in a ward team.",
    "Emergency triage, basic life support and safe handover are daily responsibilities.",
]


def synthetic_advert(number: int) -> JobAdvert:
    """A synthetic nursing advert with enough text for several passages."""
    body = " ".join(f"{s} Ward {number}, item {i}." for i in range(4) for s in SENTENCES)
    return JobAdvert(
        title=f"Registered Nurse {number}",
        company="Synthetic Hospital",
        url=f"https://www.myjobmag.com/job/synthetic-registered-nurse-{number}",
        location="Uyo, Akwa Ibom",
        date_posted="2026-11-01",
        text=f"Job title: Registered Nurse {number}\nEmployer: Synthetic Hospital\n\n{body}",
    )


@pytest.fixture
def programme_id(app) -> int:
    programme = default_programme()
    programme.job_search_terms = ["nurse", "nursing"]
    programme.job_field_slugs = ["medical"]
    db.session.commit()
    return programme.id


@pytest.fixture
def fake_collector(monkeypatch):
    def collect(search_terms, field_slugs, target_count, pages_per_field):
        adverts = [synthetic_advert(n) for n in range(1, target_count + 1)]
        return Collection(adverts=adverts, examined=target_count + 2, skipped=2)

    monkeypatch.setattr("app.tasks.harvest.collect_jobs", collect)


def add_run(programme_id: int, user_id: int, **fields) -> JobHarvestRun:
    run = JobHarvestRun(programme_id=programme_id, requested_by_id=user_id, **fields)
    db.session.add(run)
    db.session.commit()
    return run


def test_a_collection_imports_adverts_and_reports_them_ready(
    login_as, programme_id, fake_collector
):
    admin = login_as(UserRole.ADMIN)

    response = admin.post(f"/api/harvest/programmes/{programme_id}/runs", json={"target_count": 3})

    assert response.status_code == 202
    state = admin.get(f"/api/harvest/programmes/{programme_id}").get_json()["data"]
    run = state["latest_run"]
    assert run["status"] == "completed"
    assert run["imported_count"] == 3
    assert run["phase"] == "ready"
    assert run["documents_ready"] == 3
    assert run["documents_processing"] == 0
    documents = db.session.scalars(select(Document).where(Document.harvest_run_id == run["id"]))
    assert {d.programme_id for d in documents} == {programme_id}
    assert db.session.scalar(
        select(AuditLog).where(
            AuditLog.action_type == "harvest.started", AuditLog.entity_id == str(run["id"])
        )
    )


def test_adverts_still_being_processed_are_reported_as_preparing(login_as, programme_id):
    admin = login_as(UserRole.ADMIN)
    run = add_run(programme_id, admin.user.id, status="completed", imported_count=2)
    for number, status in ((1, DocumentStatus.READY), (2, DocumentStatus.PARSING)):
        db.session.add(
            Document(
                uploaded_by_id=admin.user.id,
                programme_id=programme_id,
                harvest_run_id=run.id,
                title=f"Synthetic advert {number}",
                original_filename=f"advert-{number}.txt",
                stored_filename=f"synthetic-{number}.txt",
                file_type="txt",
                file_size=10,
                content_hash=str(number) * 64,
                source_category="job_market",
                processing_status=status,
            )
        )
    db.session.commit()

    latest = admin.get(f"/api/harvest/programmes/{programme_id}").get_json()["data"]["latest_run"]

    assert latest["phase"] == "preparing"
    assert (latest["documents_ready"], latest["documents_processing"]) == (1, 1)


def test_a_collection_that_stopped_no_longer_blocks_new_ones(
    login_as, programme_id, fake_collector
):
    admin = login_as(UserRole.ADMIN)
    long_ago = utcnow() - STOPPED_AFTER - timedelta(minutes=1)
    stuck = add_run(programme_id, admin.user.id, status="running", started_at=long_ago)

    response = admin.post(f"/api/harvest/programmes/{programme_id}/runs", json={"target_count": 1})

    assert response.status_code == 202
    db.session.refresh(stuck)
    assert stuck.status == "failed"
    assert stuck.error_message == STOPPED_MESSAGE


def test_a_recent_collection_still_blocks_a_second_one(login_as, programme_id):
    admin = login_as(UserRole.ADMIN)
    add_run(programme_id, admin.user.id, status="running", started_at=utcnow())

    response = admin.post(f"/api/harvest/programmes/{programme_id}/runs", json={})

    assert response.status_code == 409


@pytest.mark.parametrize(("job_ended", "expected"), [(True, "failed"), (None, "running")])
def test_a_collection_whose_background_job_ended_is_marked_failed(
    app, make_user, programme_id, monkeypatch, job_ended, expected
):
    # Outside eager mode the RQ job is checked; None means Redis could not be asked.
    app.config["TASKS_EAGER"] = False
    monkeypatch.setattr("app.harvesting._job_has_ended", lambda job_id: job_ended)
    user = make_user(UserRole.ADMIN)
    run = add_run(programme_id, user.id, status="running", started_at=utcnow(), rq_job_id="job-1")

    expire_stopped_runs(programme_id)

    db.session.refresh(run)
    assert run.status == expected


def test_a_run_marked_stopped_is_not_started_later(app, make_user, programme_id, fake_collector):
    from app.tasks.harvest import harvest_programme_jobs

    user = make_user(UserRole.ADMIN)
    run = add_run(programme_id, user.id, status="failed", error_message=STOPPED_MESSAGE)

    harvest_programme_jobs(run.id)

    db.session.refresh(run)
    assert run.status == "failed"
    assert db.session.scalar(select(Document.id).where(Document.harvest_run_id == run.id)) is None


def test_profile_changes_are_audited_and_only_admins_collect(login_as, programme_id):
    admin = login_as(UserRole.ADMIN)
    response = admin.patch(
        f"/api/harvest/programmes/{programme_id}",
        json={"search_terms": ["nurse", "midwife"], "field_slugs": ["medical"]},
    )
    assert response.status_code == 200
    assert db.session.scalar(
        select(AuditLog).where(AuditLog.action_type == "harvest.profile_updated")
    )

    planner = login_as(UserRole.PLANNER)
    assert planner.post(f"/api/harvest/programmes/{programme_id}/runs", json={}).status_code == 403
