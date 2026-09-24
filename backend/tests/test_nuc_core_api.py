"""NUC core reference versioning (admin upload; activation once parsed)."""

from __future__ import annotations

import io

from sqlalchemy import select

from app.extensions import db
from app.models import AuditLog, Document, NucCoreVersion
from app.tasks import ingestion
from tests.conftest import ApiClient
from tests.documents import JOB_AD_TEXT, SECURITY_TEXT, make_blank_pdf, make_pdf

NUC_TEXT_V1 = (
    "Synthetic core course: Introduction to Computer Science covers algorithms, data "
    "structures and programming in Python. Students learn operating systems and databases."
)
NUC_TEXT_V2 = NUC_TEXT_V1 + " The revised core adds computer networks and software engineering."


def upload_version(client: ApiClient, label: str, content: bytes, name: str = "core.pdf"):
    return client.post(
        "/api/nuc-core",
        data={"version_label": label, "file": (io.BytesIO(content), name)},
        content_type="multipart/form-data",
    )


def test_no_active_version_initially(login_as) -> None:
    data = login_as("planner").get("/api/nuc-core").get_json()["data"]

    assert data == {"active": None, "latest": None}


def test_upload_parses_and_activates_the_version(login_as) -> None:
    admin = login_as("admin")

    response = upload_version(admin, "CCMAS 2023", make_pdf([NUC_TEXT_V1]))

    assert response.status_code == 201
    version = response.get_json()["data"]
    assert version["version_label"] == "CCMAS 2023"
    current = admin.get("/api/nuc-core").get_json()["data"]
    assert current["active"]["id"] == version["id"]
    assert current["active"]["document"]["processing_status"] == "ready"
    assert current["active"]["document"]["source_category"] == "nuc_core"
    entry = db.session.scalars(
        select(AuditLog).where(AuditLog.action_type == "nuc_core.uploaded")
    ).one()
    assert entry.detail["version_label"] == "CCMAS 2023"


def test_a_new_version_replaces_the_active_one(login_as) -> None:
    admin = login_as("admin")
    first = upload_version(admin, "v1", make_pdf([NUC_TEXT_V1])).get_json()["data"]
    second = upload_version(admin, "v2", make_pdf([NUC_TEXT_V2])).get_json()["data"]

    versions = admin.get("/api/nuc-core/versions").get_json()["data"]

    assert [(v["id"], v["is_active"]) for v in versions] == [
        (second["id"], True),
        (first["id"], False),
    ]


def test_a_failed_version_leaves_the_previous_one_active(login_as) -> None:
    admin = login_as("admin")
    good = upload_version(admin, "v1", make_pdf([NUC_TEXT_V1])).get_json()["data"]

    upload_version(admin, "scanned", make_blank_pdf())

    current = admin.get("/api/nuc-core").get_json()["data"]
    assert current["active"]["id"] == good["id"]
    assert current["latest"]["version_label"] == "scanned"
    assert current["latest"]["document"]["processing_status"] == "failed"


def test_an_older_version_finishing_late_does_not_replace_a_newer_active_one(login_as) -> None:
    admin = login_as("admin")
    newer = upload_version(admin, "v2", make_pdf([NUC_TEXT_V2])).get_json()["data"]
    older_document = Document(
        uploaded_by_id=admin.user.id,
        title="late",
        original_filename="late.pdf",
        stored_filename="0" * 32 + ".pdf",
        file_type="pdf",
        file_size=1,
        content_hash="x" * 64,
        source_category="nuc_core",
    )
    db.session.add(older_document)
    db.session.flush()
    older = NucCoreVersion(
        document_id=older_document.id, version_label="v1", uploaded_by_id=admin.user.id
    )
    db.session.add(older)
    db.session.commit()
    # Simulate "older" having a lower id than the active version.
    db.session.execute(
        NucCoreVersion.__table__.update().where(NucCoreVersion.id == older.id).values(id=0)
    )
    db.session.commit()

    ingestion.activate_nuc_core_version(older_document)
    db.session.commit()

    assert db.session.get(NucCoreVersion, newer["id"]).is_active is True


def test_nuc_core_documents_are_not_in_the_library(login_as) -> None:
    admin = login_as("admin")
    upload_version(admin, "v1", make_pdf([NUC_TEXT_V1]))

    library = admin.get("/api/documents").get_json()["data"]
    only_core = admin.get("/api/documents?category=nuc_core").get_json()["data"]

    assert library["items"] == []
    assert len(only_core["items"]) == 1


def test_nuc_core_documents_cannot_be_archived_or_deleted_from_the_library(login_as) -> None:
    admin = login_as("admin")
    version = upload_version(admin, "v1", make_pdf([NUC_TEXT_V1])).get_json()["data"]
    document_id = version["document"]["id"]

    assert admin.post(f"/api/documents/{document_id}/archive").status_code == 409
    assert admin.delete(f"/api/documents/{document_id}").status_code == 409


def test_upload_validation(login_as) -> None:
    admin = login_as("admin")

    no_label = upload_version(admin, "  ", make_pdf([NUC_TEXT_V1]))
    no_file = admin.post(
        "/api/nuc-core", data={"version_label": "v1"}, content_type="multipart/form-data"
    )
    bad_file = upload_version(admin, "v1", b"not a pdf", name="core.pdf")

    assert (
        no_label.status_code == 422
        and "version_label" in no_label.get_json()["error"]["details"]["fields"]
    )
    assert no_file.status_code == 422 and "file" in no_file.get_json()["error"]["details"]["fields"]
    assert (
        bad_file.status_code == 422 and "file" in bad_file.get_json()["error"]["details"]["fields"]
    )
    assert db.session.query(NucCoreVersion).count() == 0


def test_only_admins_can_upload(login_as) -> None:
    for role in ("planner", "viewer"):
        client = login_as(role)
        assert upload_version(client, "v1", make_pdf([JOB_AD_TEXT])).status_code == 403


def test_everyone_can_see_the_active_version(login_as) -> None:
    upload_version(login_as("admin"), "v1", make_pdf([SECURITY_TEXT]))

    for role in ("planner", "viewer"):
        assert login_as(role).get("/api/nuc-core").get_json()["data"]["active"] is not None
