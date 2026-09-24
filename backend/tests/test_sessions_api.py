import pytest

from app.models import AnalysisSession, Document, DocumentStatus, FileType, Role, SessionStatus, SourceCategory


@pytest.fixture()
def planner(make_user, login):
    user = make_user("planner", role=Role.PLANNER)
    login("planner")
    return user


@pytest.fixture()
def make_docs(db, planner):
    def _make(n, status=DocumentStatus.PARSED):
        docs = [
            Document(
                user_id=planner.user_id, title=f"doc{i}", file_path=f"/x/{i}", file_type=FileType.TXT,
                source_category=SourceCategory.JOB_MARKET, processing_status=status,
            )
            for i in range(n)
        ]
        db.session.add_all(docs)
        db.session.commit()
        return [d.document_id for d in docs]

    return _make


def create(client, document_ids, **extra):
    return client.post("/api/sessions", json={"session_name": "2026 Review", "document_ids": document_ids, **extra})


def test_create_session_with_defaults(client, make_docs):
    ids = make_docs(3)
    resp = create(client, [ids[2], ids[0], ids[2], ids[1]])
    assert resp.status_code == 201, resp.json
    session = resp.json["session"]
    assert session["status"] == "Pending"
    assert session["document_ids"] == [ids[2], ids[0], ids[1]]  # de-duplicated, order kept
    assert session["parameter_config"]["similarity_threshold"] == 0.80
    assert session["parameter_config"]["max_recommendations"] == 20


def test_custom_config_validated(client, make_docs):
    ids = make_docs(1)
    ok = create(client, ids, parameter_config={"ner_weight": 0.5, "topic_weight": 0.25, "novelty_weight": 0.25})
    assert ok.status_code == 201
    bad = create(client, ids, parameter_config={"ner_weight": 0.9})
    assert bad.status_code == 422 and "weights" in bad.json["error"]["details"]


def test_document_limit(client, app, make_docs):
    app.config["MAX_DOCUMENTS_PER_SESSION"] = 3
    ids = make_docs(4)
    assert create(client, ids[:3]).status_code == 201
    resp = create(client, ids)
    assert resp.status_code == 422 and "maximum is 3" in resp.json["error"]["details"]["document_ids"]


def test_rejects_missing_and_unparsed_documents(client, make_docs):
    parsed = make_docs(1)
    failed = make_docs(1, status=DocumentStatus.FAILED)
    resp = create(client, parsed + failed + [9999])
    assert resp.status_code == 422
    assert resp.json["error"]["details"] == {"missing": [9999], "not_parsed": failed}


@pytest.mark.parametrize("body", [{}, {"session_name": "x"}, {"session_name": "x", "document_ids": []},
                                  {"session_name": "x", "document_ids": ["1"]}, {"session_name": "  ", "document_ids": [1]}])
def test_invalid_bodies(client, planner, body):
    assert client.post("/api/sessions", json=body).status_code == 422


def test_viewer_cannot_create(client, make_docs, make_user, login):
    ids = make_docs(1)
    client.post("/api/auth/logout")
    make_user("viewer", role=Role.VIEWER)
    login("viewer")
    assert create(client, ids).status_code == 403


def test_list_get_delete(client, make_docs, db):
    ids = make_docs(2)
    sid = create(client, ids).json["session"]["session_id"]
    assert client.get("/api/sessions").json["pagination"]["total"] == 1
    assert client.get("/api/sessions?status=Pending").json["items"][0]["session_id"] == sid
    assert client.get(f"/api/sessions/{sid}").json["session"]["document_ids"] == ids
    assert client.get("/api/sessions/999").status_code == 404

    assert client.delete(f"/api/sessions/{sid}").status_code == 200
    assert db.session.get(AnalysisSession, sid) is None
    assert all(db.session.get(Document, i) for i in ids)  # documents survive


def test_cannot_delete_processing_or_others_session(client, make_docs, db, make_user, login):
    ids = make_docs(1)
    sid = create(client, ids).json["session"]["session_id"]
    session = db.session.get(AnalysisSession, sid)
    session.status = SessionStatus.PROCESSING
    db.session.commit()
    assert client.delete(f"/api/sessions/{sid}").status_code == 409

    session.status = SessionStatus.COMPLETED
    db.session.commit()
    client.post("/api/auth/logout")
    make_user("other", role=Role.PLANNER)
    login("other")
    assert client.delete(f"/api/sessions/{sid}").status_code == 403
