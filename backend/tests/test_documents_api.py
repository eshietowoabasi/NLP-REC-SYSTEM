import io
import os

import pytest

from app.models import AnalysisSession, AuditLog, Document, DocumentSession, Role, SessionStatus

from .fixtures import JOB_AD, make_docx, make_pdf


@pytest.fixture()
def planner(make_user, login):
    user = make_user("planner", role=Role.PLANNER)
    login("planner")
    return user


def upload(client, data, filename, category="Job Market Data", title=None):
    form = {"file": (io.BytesIO(data), filename), "source_category": category}
    if title is not None:
        form["title"] = title
    return client.post("/api/documents", data=form, content_type="multipart/form-data")


class TestUpload:
    @pytest.mark.parametrize(
        "filename, data",
        [("ad.pdf", make_pdf([JOB_AD])), ("ad.docx", make_docx([JOB_AD])), ("ad.txt", JOB_AD.encode())],
        ids=["pdf", "docx", "txt"],
    )
    def test_upload_parses_each_format(self, client, planner, app, db, filename, data):
        resp = upload(client, data, filename)
        assert resp.status_code == 201, resp.json
        doc = resp.json["document"]
        assert doc["processing_status"] == "Parsed"
        assert doc["title"] == "ad" and doc["original_filename"] == filename
        assert doc["file_type"] == filename.rsplit(".", 1)[1]
        assert doc["word_count"] == 32  # same count whatever the format
        assert "file_path" not in doc

        stored = db.session.get(Document, doc["document_id"])
        assert os.path.exists(stored.file_path)
        assert os.path.basename(stored.file_path) != filename  # stored under a UUID name
        assert stored.file_path.startswith(app.config["UPLOAD_FOLDER"])
        assert db.session.query(AuditLog).filter_by(action_type="DOCUMENT_UPLOAD").count() == 1

    def test_title_and_filename_sanitised(self, client, planner):
        resp = upload(client, JOB_AD.encode(), "../../etc/ad.txt", title="  Lagos tech ads 2025  ")
        assert resp.json["document"]["title"] == "Lagos tech ads 2025"
        assert resp.json["document"]["original_filename"] == "ad.txt"

    def test_unsupported_type_rejected_before_saving(self, client, planner, app, db):
        resp = upload(client, b"binary", "slides.pptx")
        assert resp.status_code == 415 and resp.json["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
        assert db.session.query(Document).count() == 0
        assert not os.path.exists(app.config["UPLOAD_FOLDER"]) or not os.listdir(app.config["UPLOAD_FOLDER"])

    def test_oversized_file_rejected(self, client, planner, app):
        app.config["MAX_DOCUMENT_BYTES"] = 100
        resp = upload(client, b"a" * 101, "big.txt")
        assert resp.status_code == 413 and resp.json["error"]["code"] == "PAYLOAD_TOO_LARGE"

    def test_corrupt_file_is_stored_as_failed_with_reason(self, client, planner):
        resp = upload(client, b"%PDF-1.7\n garbage", "broken.pdf")
        assert resp.status_code == 201
        assert resp.json["document"]["processing_status"] == "Failed"
        assert "Could not open PDF" in resp.json["document"]["error_message"]

    def test_duplicate_content_rejected(self, client, planner):
        first = upload(client, JOB_AD.encode(), "a.txt")
        resp = upload(client, JOB_AD.encode(), "copy.txt")
        assert resp.status_code == 409 and resp.json["error"]["code"] == "DUPLICATE_DOCUMENT"
        assert resp.json["error"]["details"]["document_id"] == first.json["document"]["document_id"]

    @pytest.mark.parametrize(
        "form, field",
        [({"source_category": "Job Market Data"}, "file"), ({"file": (io.BytesIO(b"x"), "a.txt")}, "source_category")],
    )
    def test_required_fields(self, client, planner, form, field):
        resp = client.post("/api/documents", data=form, content_type="multipart/form-data")
        assert resp.status_code == 422 and field in resp.json["error"]["details"]

    def test_invalid_category(self, client, planner):
        resp = upload(client, JOB_AD.encode(), "a.txt", category="Social Media")
        assert resp.status_code == 422 and "source_category" in resp.json["error"]["details"]

    def test_viewer_cannot_upload(self, client, make_user, login):
        make_user("viewer", role=Role.VIEWER)
        login("viewer")
        assert upload(client, JOB_AD.encode(), "a.txt").status_code == 403

    def test_only_admin_uploads_nuc_core(self, client, planner, make_user, login):
        assert upload(client, JOB_AD.encode(), "core.txt", category="NUC Core Reference").status_code == 403
        client.post("/api/auth/logout")
        make_user("admin", role=Role.ADMIN)
        login("admin")
        assert upload(client, JOB_AD.encode(), "core.txt", category="NUC Core Reference").status_code == 201


class TestReadAndDelete:
    def test_list_filters_and_pagination(self, client, planner):
        upload(client, b"Job ad about Python.", "a.txt")
        upload(client, b"Policy on digital economy.", "b.txt", category="Policy Document")
        upload(client, b"%PDF-1.7 broken", "c.pdf")

        resp = client.get("/api/documents?per_page=2")
        assert resp.json["pagination"] == {"page": 1, "per_page": 2, "total": 3, "pages": 2}
        assert len(resp.json["items"]) == 2

        def titles(query):
            return {d["title"] for d in client.get(f"/api/documents?{query}").json["items"]}

        assert titles("source_category=Policy Document") == {"b"}
        assert titles("status=Failed") == {"c"}
        assert titles("q=A") == {"a"}
        assert client.get("/api/documents?status=Bogus").status_code == 422
        assert client.get("/api/documents?per_page=1000").status_code == 422

    def test_get_and_text_views(self, client, planner):
        data = make_docx(["Real content about cloud security."], toc_entries=[("Intro", 1)])
        doc_id = upload(client, data, "a.docx").json["document"]["document_id"]
        assert client.get(f"/api/documents/{doc_id}").json["document"]["document_id"] == doc_id

        raw = client.get(f"/api/documents/{doc_id}/text").json["text"]
        clean = client.get(f"/api/documents/{doc_id}/text?view=clean").json["text"]
        assert "Intro\t1" in raw
        assert clean == "Real content about cloud security."
        assert client.get(f"/api/documents/{doc_id}/text?view=x").status_code == 422

    def test_text_unavailable_for_failed_document(self, client, planner):
        doc_id = upload(client, b"%PDF-1.7 broken", "c.pdf").json["document"]["document_id"]
        resp = client.get(f"/api/documents/{doc_id}/text")
        assert resp.status_code == 409 and resp.json["error"]["code"] == "NOT_PARSED"

    def test_missing_document_404(self, client, planner):
        assert client.get("/api/documents/999").status_code == 404

    def test_viewer_can_read(self, client, planner, make_user, login):
        upload(client, JOB_AD.encode(), "a.txt")
        client.post("/api/auth/logout")
        make_user("viewer", role=Role.VIEWER)
        login("viewer")
        assert client.get("/api/documents").json["pagination"]["total"] == 1

    def test_delete_removes_row_and_file(self, client, planner, db):
        doc_id = upload(client, JOB_AD.encode(), "a.txt").json["document"]["document_id"]
        path = db.session.get(Document, doc_id).file_path
        assert client.delete(f"/api/documents/{doc_id}").status_code == 200
        assert db.session.get(Document, doc_id) is None and not os.path.exists(path)
        assert db.session.query(AuditLog).filter_by(action_type="DOCUMENT_DELETE").count() == 1

    def test_planner_cannot_delete_others_documents_but_admin_can(self, client, planner, make_user, login):
        doc_id = upload(client, JOB_AD.encode(), "a.txt").json["document"]["document_id"]
        client.post("/api/auth/logout")
        make_user("other", role=Role.PLANNER)
        login("other")
        assert client.delete(f"/api/documents/{doc_id}").status_code == 403
        client.post("/api/auth/logout")
        make_user("admin", role=Role.ADMIN)
        login("admin")
        assert client.delete(f"/api/documents/{doc_id}").status_code == 200

    def test_cannot_delete_document_in_processing_session(self, client, planner, db):
        doc_id = upload(client, JOB_AD.encode(), "a.txt").json["document"]["document_id"]
        session = AnalysisSession(user_id=planner.user_id, session_name="s", status=SessionStatus.PROCESSING)
        session.document_links = [DocumentSession(document_id=doc_id)]
        db.session.add(session)
        db.session.commit()
        resp = client.delete(f"/api/documents/{doc_id}")
        assert resp.status_code == 409 and resp.json["error"]["code"] == "DOCUMENT_IN_USE"
