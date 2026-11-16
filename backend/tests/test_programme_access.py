"""Planners and viewers only reach their own programmes; admins reach all (synthetic data)."""

from __future__ import annotations

import io

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import AuditLog, Document, Programme, User
from app.sessions import default_programme
from tests.conftest import ApiClient
from tests.documents import JOB_AD_TEXT
from tests.review_data import ReviewSession, build_review_session


@pytest.fixture
def nursing(app) -> Programme:
    default_programme()
    programme = Programme(name="Synthetic Nursing Science", discipline_code="NSC")
    db.session.add(programme)
    db.session.commit()
    return programme


@pytest.fixture
def computing_review(make_user) -> ReviewSession:
    """A completed Computer Science review (its documents are general: no programme)."""
    review = build_review_session(make_user("planner", username="cs-owner"))
    db.session.commit()
    return review


@pytest.fixture
def computing_advert(make_user) -> Document:
    owner: User = make_user("planner", username="cs-uploader")
    document = Document(
        uploaded_by_id=owner.id,
        programme_id=default_programme().id,
        title="Synthetic computing advert",
        original_filename="computing.txt",
        stored_filename="synthetic-computing.txt",
        file_type="txt",
        file_size=10,
        content_hash="c" * 64,
        source_category="job_market",
        processing_status="ready",
    )
    db.session.add(document)
    db.session.commit()
    return document


@pytest.fixture
def nurse_planner(login_as, nursing: Programme) -> ApiClient:
    return login_as("planner", username="nurse-planner", programmes=[nursing])


def test_planners_only_see_their_programmes_reviews(
    nurse_planner: ApiClient, computing_review: ReviewSession, login_as
) -> None:
    session_id = computing_review.session.id
    recommendation_id = computing_review.recommendations[0].id

    assert nurse_planner.get("/api/sessions").get_json()["data"]["items"] == []
    for url in (
        f"/api/sessions/{session_id}",
        f"/api/sessions/{session_id}/recommendations",
        f"/api/sessions/{session_id}/recommendations/export",
        f"/api/sessions/{session_id}/curriculum",
        f"/api/sessions/{session_id}/keywords",
        f"/api/recommendations/{recommendation_id}",
    ):
        assert nurse_planner.get(url).status_code == 404, url
    decision = nurse_planner.patch(
        f"/api/recommendations/{recommendation_id}/decision", json={"decision": "accepted"}
    )
    assert decision.status_code == 404

    computing_planner = login_as("planner", username="cs-planner")
    assert computing_planner.get(f"/api/sessions/{session_id}").status_code == 200
    assert computing_planner.get(f"/api/sessions/{session_id}/keywords").status_code == 200
    admin = login_as("admin")
    assert admin.get(f"/api/sessions/{session_id}").status_code == 200


def test_the_library_shows_own_and_general_documents_only(
    nurse_planner: ApiClient, computing_advert: Document, computing_review: ReviewSession
) -> None:
    titles = {
        item["title"] for item in nurse_planner.get("/api/documents").get_json()["data"]["items"]
    }

    assert computing_advert.title not in titles
    assert "Synthetic policy" in titles  # general documents are shared
    assert nurse_planner.get(f"/api/documents/{computing_advert.id}").status_code == 404


def test_a_general_document_does_not_name_other_programmes_reviews(
    nurse_planner: ApiClient, computing_review: ReviewSession
) -> None:
    general = computing_review.documents[0]

    detail = nurse_planner.get(f"/api/documents/{general.id}").get_json()["data"]

    assert detail["sessions"] == []


def test_planners_cannot_upload_to_or_collect_for_other_programmes(
    nurse_planner: ApiClient, nursing: Programme
) -> None:
    computing = default_programme()
    db.session.commit()
    upload = nurse_planner.post(
        "/api/documents",
        data={
            "files": [(io.BytesIO(JOB_AD_TEXT.encode()), "advert.txt")],
            "categories": ["job_market"],
            "programme_id": str(computing.id),
        },
        content_type="multipart/form-data",
    )
    assert upload.status_code == 422
    assert nurse_planner.get(f"/api/harvest/programmes/{computing.id}").status_code == 404
    assert nurse_planner.post(f"/api/harvest/programmes/{computing.id}/runs").status_code == 404
    assert nurse_planner.get(f"/api/programmes/{computing.id}/benchmarks").status_code == 404

    names = [p["name"] for p in nurse_planner.get("/api/programmes").get_json()["data"]]
    assert names == [nursing.name]


def test_new_sessions_default_to_the_users_own_programme(
    nurse_planner: ApiClient, nursing: Programme
) -> None:
    defaults = nurse_planner.get("/api/sessions/defaults").get_json()["data"]

    assert defaults["default_programme_id"] == nursing.id
    assert [p["id"] for p in defaults["programmes"]] == [nursing.id]


def test_the_dashboard_counts_only_the_users_programmes(
    nurse_planner: ApiClient, computing_review: ReviewSession, login_as
) -> None:
    mine = nurse_planner.get("/api/dashboard/summary").get_json()["data"]
    everything = login_as("admin").get("/api/dashboard/summary").get_json()["data"]

    assert mine["sessions"]["total"] == 0
    assert mine["recent_sessions"] == []
    assert everything["sessions"]["total"] == 1


def test_a_user_without_programmes_sees_nothing_and_cannot_start_a_review(
    login_as, computing_review: ReviewSession
) -> None:
    newcomer = login_as("planner", username="newcomer", programmes=[])

    assert newcomer.get("/api/sessions").get_json()["data"]["items"] == []
    assert newcomer.get("/api/programmes").get_json()["data"] == []
    response = newcomer.post(
        "/api/sessions",
        json={
            "session_name": "Synthetic review",
            "document_ids": [computing_review.documents[0].id],
        },
    )
    assert response.status_code == 422
    assert "Ask an admin" in response.get_json()["error"]["message"]


def test_admins_assign_programmes_to_users(login_as, make_user, nursing: Programme) -> None:
    admin = login_as("admin")
    viewer = make_user("viewer", username="dean")

    response = admin.patch(
        f"/api/admin/users/{viewer.id}",
        json={"programme_ids": [nursing.id, default_programme().id]},
    )

    assert response.status_code == 200
    names = sorted(p["name"] for p in response.get_json()["data"]["programmes"])
    assert names == sorted([nursing.name, default_programme().name])
    assert db.session.scalar(
        select(AuditLog).where(AuditLog.action_type == "user.programmes_changed")
    )
    bad = admin.patch(f"/api/admin/users/{viewer.id}", json={"programme_ids": [999]})
    assert bad.status_code == 422
    assert "programme_ids" in bad.get_json()["error"]["details"]["fields"]


def test_new_users_get_their_programmes_and_admins_need_none(login_as, nursing: Programme) -> None:
    admin = login_as("admin")
    base = {"full_name": "Synthetic Person", "password": "Synthetic-pass-2026"}

    planner = admin.post(
        "/api/admin/users",
        json={
            **base,
            "username": "new-planner",
            "email": "new-planner@example.com",
            "role": "planner",
            "programme_ids": [nursing.id],
        },
    ).get_json()["data"]
    other_admin = admin.post(
        "/api/admin/users",
        json={
            **base,
            "username": "new-admin",
            "email": "new-admin@example.com",
            "role": "admin",
            "programme_ids": [nursing.id],
        },
    ).get_json()["data"]

    assert [p["id"] for p in planner["programmes"]] == [nursing.id]
    assert other_admin["programmes"] == []


def test_the_signed_in_user_sees_their_programmes(nurse_planner: ApiClient) -> None:
    me = nurse_planner.get("/api/auth/me").get_json()["data"]

    assert [p["name"] for p in me["programmes"]] == ["Synthetic Nursing Science"]
