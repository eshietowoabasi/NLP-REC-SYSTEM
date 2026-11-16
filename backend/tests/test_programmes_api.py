"""Programmes, and how they separate documents and sessions (synthetic data)."""

from __future__ import annotations

import io

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import AuditLog, Document, Programme
from app.sessions import default_programme
from tests.conftest import ApiClient
from tests.documents import JOB_AD_TEXT, SECURITY_TEXT


@pytest.fixture
def admin(login_as) -> ApiClient:
    return login_as("admin")


@pytest.fixture
def planner(login_as) -> ApiClient:
    return login_as("planner")


@pytest.fixture
def nursing(app) -> Programme:
    default_programme()  # Computer Science stays the default (lowest id)
    programme = Programme(name="Synthetic Nursing Science", discipline_code="NSC")
    db.session.add(programme)
    db.session.commit()
    return programme


def upload(client: ApiClient, name: str, text: str, programme_id: int | None = None):
    data = {"files": [(io.BytesIO(text.encode()), name)], "categories": ["job_market"]}
    if programme_id is not None:
        data["programme_id"] = str(programme_id)
    return client.post("/api/documents", data=data, content_type="multipart/form-data")


def audited(action: str) -> bool:
    return db.session.scalar(select(AuditLog).where(AuditLog.action_type == action)) is not None


# ------------------------------------------------------------------------ programmes


def test_admins_create_programmes_with_unique_names_and_codes(admin: ApiClient) -> None:
    response = admin.post(
        "/api/programmes", json={"name": "Synthetic Nursing Science", "discipline_code": "NSC"}
    )
    assert response.status_code == 201
    assert audited("programme.created")

    same_name = admin.post("/api/programmes", json={"name": "synthetic NURSING science"})
    same_code = admin.post("/api/programmes", json={"name": "Midwifery", "discipline_code": "nsc"})

    assert same_name.status_code == 409
    assert same_name.get_json()["error"]["details"]["fields"]["name"]
    assert same_code.status_code == 409


def test_admins_edit_and_retire_programmes(admin: ApiClient, nursing: Programme) -> None:
    response = admin.patch(
        f"/api/programmes/{nursing.id}", json={"faculty": "Synthetic Faculty of Nursing"}
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["faculty"] == "Synthetic Faculty of Nursing"
    assert audited("programme.updated")

    retired = admin.patch(f"/api/programmes/{nursing.id}", json={"is_active": False})
    assert retired.status_code == 200
    active_names = [p["name"] for p in admin.get("/api/programmes").get_json()["data"]]
    all_names = [
        p["name"] for p in admin.get("/api/programmes?include_inactive=true").get_json()["data"]
    ]
    assert nursing.name not in active_names
    assert nursing.name in all_names


def test_the_last_active_programme_cannot_be_retired(admin: ApiClient) -> None:
    only = default_programme()
    db.session.commit()

    response = admin.patch(f"/api/programmes/{only.id}", json={"is_active": False})

    assert response.status_code == 409


def test_a_programme_cannot_take_another_programmes_name(
    admin: ApiClient, nursing: Programme
) -> None:
    computing = default_programme().name

    response = admin.patch(f"/api/programmes/{nursing.id}", json={"name": computing})

    assert response.status_code == 409


def test_planners_cannot_change_programmes(planner: ApiClient, nursing: Programme) -> None:
    assert planner.post("/api/programmes", json={"name": "Pharmacy"}).status_code == 403
    assert planner.patch(f"/api/programmes/{nursing.id}", json={"name": "X Y"}).status_code == 403
    # include_inactive is an admin option: planners still see active programmes only.
    nursing.is_active = False
    db.session.commit()
    names = [
        p["name"] for p in planner.get("/api/programmes?include_inactive=true").get_json()["data"]
    ]
    assert nursing.name not in names


# ------------------------------------------------------------------------ documents


def test_uploads_belong_to_the_chosen_programme_or_none(
    planner: ApiClient, nursing: Programme
) -> None:
    tagged = upload(planner, "nursing-advert.txt", JOB_AD_TEXT, nursing.id)
    general = upload(planner, "general-policy.txt", SECURITY_TEXT)

    assert tagged.status_code == 201
    assert tagged.get_json()["data"]["accepted"][0]["programme"]["name"] == nursing.name
    assert general.get_json()["data"]["accepted"][0]["programme"] is None


def test_uploads_to_an_unknown_or_retired_programme_are_refused(
    planner: ApiClient, nursing: Programme
) -> None:
    nursing.is_active = False
    db.session.commit()

    for value in (nursing.id, 999, "abc"):
        response = planner.post(
            "/api/documents",
            data={
                "files": [(io.BytesIO(JOB_AD_TEXT.encode()), "advert.txt")],
                "categories": ["job_market"],
                "programme_id": str(value),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 422
        assert "programme_id" in response.get_json()["error"]["details"]["fields"]


def test_the_library_filters_by_programme(planner: ApiClient, nursing: Programme) -> None:
    computing = default_programme()
    db.session.commit()
    upload(planner, "nursing.txt", JOB_AD_TEXT, nursing.id)
    upload(planner, "computing.txt", SECURITY_TEXT, computing.id)
    upload(planner, "general.txt", JOB_AD_TEXT + " General policy edition.")

    def titles(query: str) -> set[str]:
        items = planner.get(f"/api/documents?{query}").get_json()["data"]["items"]
        return {item["original_filename"] for item in items}

    assert titles(f"programme_id={nursing.id}") == {"nursing.txt", "general.txt"}
    assert titles(f"programme_id={nursing.id}&include_general=false") == {"nursing.txt"}
    assert titles("") == {"nursing.txt", "computing.txt", "general.txt"}


def test_a_document_can_be_moved_or_made_general(planner: ApiClient, nursing: Programme) -> None:
    document_id = upload(planner, "advert.txt", JOB_AD_TEXT).get_json()["data"]["accepted"][0]["id"]

    moved = planner.patch(f"/api/documents/{document_id}", json={"programme_id": nursing.id})
    assert moved.get_json()["data"]["programme"]["id"] == nursing.id

    general = planner.patch(f"/api/documents/{document_id}", json={"programme_id": None})
    assert general.get_json()["data"]["programme"] is None
    assert db.session.get(Document, document_id).programme_id is None


# ------------------------------------------------------------------------ sessions


def test_sessions_refuse_another_programmes_documents(
    planner: ApiClient, nursing: Programme
) -> None:
    computing = default_programme()
    db.session.commit()
    computing_doc = upload(planner, "computing.txt", JOB_AD_TEXT, computing.id)
    general_doc = upload(planner, "general.txt", SECURITY_TEXT)
    computing_id = computing_doc.get_json()["data"]["accepted"][0]["id"]
    general_id = general_doc.get_json()["data"]["accepted"][0]["id"]

    mixed = planner.post(
        "/api/sessions",
        json={
            "session_name": "Synthetic nursing analysis",
            "programme_id": nursing.id,
            "document_ids": [computing_id, general_id],
        },
    )
    allowed = planner.post(
        "/api/sessions",
        json={
            "session_name": "Synthetic nursing analysis",
            "programme_id": nursing.id,
            "document_ids": [general_id],
        },
    )

    assert mixed.status_code == 422
    problems = mixed.get_json()["error"]["details"]["fields"]["document_ids"]
    assert problems == [f"“computing” belongs to {computing.name}, not {nursing.name}."]
    assert allowed.status_code == 201
