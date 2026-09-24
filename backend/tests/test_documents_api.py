"""Document library API and the ingestion job it triggers (run eagerly in tests)."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from flask import Flask
from sqlalchemy import select

from app.extensions import db
from app.models import (
    AnalysisSession,
    AuditLog,
    Document,
    DocumentSession,
    Passage,
)
from app.tasks import ingestion
from tests.conftest import ApiClient
from tests.documents import (
    FINTECH_TEXT,
    JOB_AD_TEXT,
    SECURITY_TEXT,
    make_blank_pdf,
    make_docx,
    make_pdf,
)


def upload(client: ApiClient, *files: tuple[str, bytes, str]):
    """POST files as (filename, content, category) triples."""
    return client.post(
        "/api/documents",
        data={
            "files": [(io.BytesIO(content), name) for name, content, _ in files],
            "categories": [category for _, _, category in files],
        },
        content_type="multipart/form-data",
    )


@pytest.fixture
def planner(login_as) -> ApiClient:
    return login_as("planner")


def stored_files(app: Flask) -> list[Path]:
    folder = Path(app.config["STORAGE_DIR"]) / "documents"
    return sorted(folder.glob("*")) if folder.exists() else []


# ------------------------------------------------------------------------- upload


def test_upload_parses_the_document_and_stores_passages(app: Flask, planner: ApiClient) -> None:
    response = upload(
        planner, ("Backend_Engineer-Ad.pdf", make_pdf([JOB_AD_TEXT, SECURITY_TEXT]), "job_market")
    )

    assert response.status_code == 201
    (accepted,) = response.get_json()["data"]["accepted"]
    assert accepted["title"] == "Backend Engineer Ad"
    assert accepted["file_type"] == "pdf"

    document = db.session.get(Document, accepted["id"])
    assert document.processing_status == "ready"
    assert document.page_count == 2
    assert document.word_count > 40
    assert document.parsed_at is not None
    passages = db.session.scalars(select(Passage).where(Passage.document_id == document.id)).all()
    assert passages
    assert all(p.embedding is not None and len(p.embedding) == 32 for p in passages)
    assert passages[0].embedding_model == "test-fake-encoder"
    # Stored under a UUID name, not the uploaded name.
    (stored,) = stored_files(app)
    assert stored.name == document.stored_filename != "Backend_Engineer-Ad.pdf"


def test_upload_accepts_some_files_and_rejects_others(planner: ApiClient) -> None:
    response = upload(
        planner,
        ("good.docx", make_docx([FINTECH_TEXT]), "institutional"),
        ("image.png", b"\x89PNG\r\n", "policy"),
        ("renamed.pdf", b"not a pdf at all", "academic"),
        ("bad-category.txt", b"Python role.", "nuc_core"),
    )

    assert response.status_code == 201
    data = response.get_json()["data"]
    assert [d["original_filename"] for d in data["accepted"]] == ["good.docx"]
    reasons = {r["filename"]: r["reason"] for r in data["rejected"]}
    assert "Unsupported file type" in reasons["image.png"]
    assert "does not match" in reasons["renamed.pdf"]
    assert reasons["bad-category.txt"] == "Choose a valid category."


def test_upload_with_every_file_rejected_is_422_and_stores_nothing(
    app: Flask, planner: ApiClient
) -> None:
    response = upload(planner, ("empty.txt", b"", "job_market"))

    assert response.status_code == 422
    assert response.get_json()["error"]["details"]["rejected"][0]["reason"] == "The file is empty."
    assert db.session.query(Document).count() == 0
    assert stored_files(app) == []


def test_duplicate_content_is_rejected(planner: ApiClient) -> None:
    content = make_pdf([JOB_AD_TEXT])
    upload(planner, ("first.pdf", content, "job_market"))

    response = upload(planner, ("copy.pdf", content, "policy"))

    assert response.status_code == 422
    assert (
        "already been uploaded as “first”"
        in response.get_json()["error"]["details"]["rejected"][0]["reason"]
    )


def test_upload_requires_one_category_per_file(planner: ApiClient) -> None:
    response = planner.post(
        "/api/documents",
        data={"files": [(io.BytesIO(b"Python role."), "a.txt")], "categories": []},
        content_type="multipart/form-data",
    )

    assert response.status_code == 422


def test_upload_with_no_files_is_422(planner: ApiClient) -> None:
    response = planner.post("/api/documents", data={}, content_type="multipart/form-data")

    assert response.status_code == 422


def test_upload_is_audited(planner: ApiClient) -> None:
    upload(planner, ("ad.txt", JOB_AD_TEXT.encode(), "job_market"))

    entry = db.session.scalars(
        select(AuditLog).where(AuditLog.action_type == "document.uploaded")
    ).one()
    assert entry.detail["filename"] == "ad.txt"
    assert entry.detail["category"] == "job_market"


def test_viewer_cannot_upload(login_as) -> None:
    viewer = login_as("viewer")

    assert upload(viewer, ("ad.txt", JOB_AD_TEXT.encode(), "job_market")).status_code == 403


# ----------------------------------------------------------------------- ingestion


def test_scanned_pdf_fails_with_a_clear_message(planner: ApiClient) -> None:
    response = upload(planner, ("scan.pdf", make_blank_pdf(), "policy"))

    document = db.session.get(Document, response.get_json()["data"]["accepted"][0]["id"])
    assert document.processing_status == "failed"
    assert document.error_message == "No extractable text (scanned PDF). OCR is not supported."


def test_unexpected_errors_fail_with_a_generic_message(planner: ApiClient, monkeypatch) -> None:
    def explode(*_args, **_kwargs):
        raise RuntimeError("internal detail that must not reach users")

    monkeypatch.setattr(ingestion, "process_document", explode)

    response = upload(planner, ("ad.txt", JOB_AD_TEXT.encode(), "job_market"))

    document = db.session.get(Document, response.get_json()["data"]["accepted"][0]["id"])
    assert document.processing_status == "failed"
    assert document.error_message == ingestion.UNEXPECTED_FAILURE


def test_custom_stop_words_are_applied_to_normalised_text(planner: ApiClient) -> None:
    from app.models import StopWord

    db.session.add(StopWord(word="django"))
    db.session.commit()

    upload(planner, ("ad.txt", JOB_AD_TEXT.encode(), "job_market"))

    normalised = " ".join(db.session.scalars(select(Passage.normalised_text)))
    assert "django" not in normalised
    assert "python" in normalised


def test_ingestion_skips_missing_and_archived_documents(app: Flask, planner: ApiClient) -> None:
    ingestion.ingest_document(99999)  # no error for a missing document

    response = upload(planner, ("ad.txt", JOB_AD_TEXT.encode(), "job_market"))
    document_id = response.get_json()["data"]["accepted"][0]["id"]
    planner.post(f"/api/documents/{document_id}/archive")
    with app.app_context():
        ingestion.ingest_document(document_id)
    db.session.expire_all()
    assert db.session.get(Document, document_id).processing_status == "archived"


# --------------------------------------------------------------------- list/detail


def test_list_filters_search_and_category_counts(login_as, planner: ApiClient) -> None:
    upload(planner, ("fintech ad.txt", FINTECH_TEXT.encode(), "job_market"))
    upload(planner, ("security ad.txt", SECURITY_TEXT.encode(), "job_market"))
    upload(planner, ("ict policy.docx", make_docx([JOB_AD_TEXT]), "policy"))
    viewer = login_as("viewer")

    def titles(query: str = "") -> set[str]:
        items = viewer.get(f"/api/documents{query}").get_json()["data"]["items"]
        return {item["title"] for item in items}

    assert titles() == {"fintech ad", "security ad", "ict policy"}
    assert titles("?category=policy") == {"ict policy"}
    assert titles("?search=SECURITY") == {"security ad"}
    assert titles("?status=failed") == set()
    counts = viewer.get("/api/documents").get_json()["data"]["category_counts"]
    assert counts == {"job_market": 2, "institutional": 0, "policy": 1, "academic": 0}


def test_detail_includes_preview_and_sessions(planner: ApiClient) -> None:
    response = upload(planner, ("ad.pdf", make_pdf([JOB_AD_TEXT, SECURITY_TEXT]), "job_market"))
    document_id = response.get_json()["data"]["accepted"][0]["id"]
    session = AnalysisSession(created_by_id=planner.user.id, session_name="Test session")
    session.document_links.append(DocumentSession(document_id=document_id, processing_order=1))
    db.session.add(session)
    db.session.commit()

    detail = planner.get(f"/api/documents/{document_id}").get_json()["data"]

    assert detail["passage_count"] >= 1
    assert detail["preview"][0]["page_number"] == 1
    assert detail["sessions"] == [
        {
            "id": session.id,
            "session_name": "Test session",
            "status": "pending",
            "created_at": detail["sessions"][0]["created_at"],
        }
    ]
    assert detail["is_nuc_core"] is False


def test_passages_are_paginated(planner: ApiClient) -> None:
    long_text = " ".join([JOB_AD_TEXT, SECURITY_TEXT, FINTECH_TEXT] * 6)
    response = upload(planner, ("long.txt", long_text.encode(), "academic"))
    document_id = response.get_json()["data"]["accepted"][0]["id"]

    page = planner.get(f"/api/documents/{document_id}/passages?per_page=2").get_json()["data"]

    assert len(page["items"]) == 2
    assert page["pagination"]["total"] > 2
    assert [item["position"] for item in page["items"]] == [0, 1]


def test_unknown_document_is_404(planner: ApiClient) -> None:
    assert planner.get("/api/documents/424242").status_code == 404


def test_download_returns_the_original_file(planner: ApiClient) -> None:
    content = make_docx([FINTECH_TEXT])
    response = upload(planner, ("Fintech Brief.docx", content, "institutional"))
    document_id = response.get_json()["data"]["accepted"][0]["id"]

    download = planner.get(f"/api/documents/{document_id}/file")

    assert download.status_code == 200
    assert download.data == content
    assert "Fintech Brief.docx" in download.headers["Content-Disposition"]


def test_download_requires_login(api: ApiClient) -> None:
    assert api.get("/api/documents/1/file").status_code == 401


# ------------------------------------------------------------------ archive/delete


def test_archive_hides_the_document_from_the_default_list(planner: ApiClient) -> None:
    response = upload(planner, ("ad.txt", JOB_AD_TEXT.encode(), "job_market"))
    document_id = response.get_json()["data"]["accepted"][0]["id"]

    archived = planner.post(f"/api/documents/{document_id}/archive")

    assert archived.get_json()["data"]["processing_status"] == "archived"
    assert planner.get("/api/documents").get_json()["data"]["items"] == []
    assert len(planner.get("/api/documents?status=archived").get_json()["data"]["items"]) == 1
    # An archived document no longer blocks re-uploading the same file.
    assert upload(planner, ("again.txt", JOB_AD_TEXT.encode(), "job_market")).status_code == 201


def test_delete_removes_row_passages_and_file(app: Flask, planner: ApiClient) -> None:
    response = upload(planner, ("ad.txt", JOB_AD_TEXT.encode(), "job_market"))
    document_id = response.get_json()["data"]["accepted"][0]["id"]

    deleted = planner.delete(f"/api/documents/{document_id}")

    assert deleted.status_code == 200
    assert db.session.get(Document, document_id) is None
    assert db.session.query(Passage).count() == 0
    assert stored_files(app) == []
    assert db.session.scalars(select(AuditLog.action_type)).all()[-1] == "document.deleted"


def test_document_used_by_a_session_cannot_be_deleted(planner: ApiClient) -> None:
    response = upload(planner, ("ad.txt", JOB_AD_TEXT.encode(), "job_market"))
    document_id = response.get_json()["data"]["accepted"][0]["id"]
    session = AnalysisSession(created_by_id=planner.user.id, session_name="Uses the doc")
    session.document_links.append(DocumentSession(document_id=document_id, processing_order=1))
    db.session.add(session)
    db.session.commit()

    response = planner.delete(f"/api/documents/{document_id}")

    assert response.status_code == 409
    error = response.get_json()["error"]
    assert "Archive it instead" in error["message"]
    assert error["details"]["sessions"] == [{"id": session.id, "session_name": "Uses the doc"}]


def test_viewer_cannot_archive_or_delete(login_as, planner: ApiClient) -> None:
    response = upload(planner, ("ad.txt", JOB_AD_TEXT.encode(), "job_market"))
    document_id = response.get_json()["data"]["accepted"][0]["id"]
    viewer = login_as("viewer")

    assert viewer.post(f"/api/documents/{document_id}/archive").status_code == 403
    assert viewer.delete(f"/api/documents/{document_id}").status_code == 403
