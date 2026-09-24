import io

import pytest

from app.models import AnalysisSession, AuditLog, NLPResult, Role, SessionStatus

from .corpus import theme_text


@pytest.fixture()
def planner(make_user, login):
    user = make_user("planner", role=Role.PLANNER)
    login("planner")
    return user


def upload_text(client, text, name, category="Job Market Data"):
    resp = client.post(
        "/api/documents",
        data={"file": (io.BytesIO(text.encode()), name), "source_category": category},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201, resp.json
    return resp.json["document"]["document_id"]


@pytest.fixture()
def job_session(client, planner, core_document):
    ids = [upload_text(client, theme_text(theme), f"{theme}.txt") for theme in ("cloud", "security", "data")]
    resp = client.post("/api/sessions", json={"session_name": "Jobs 2026", "document_ids": ids})
    return resp.json["session"]["session_id"], ids


def test_run_pipeline_end_to_end(client, db, job_session):
    session_id, doc_ids = job_session
    resp = client.post(f"/api/sessions/{session_id}/run")
    assert resp.status_code == 202
    assert resp.json["success"] and resp.json["message"] == "Analysis started"
    # Jobs run inline in tests, so the session is already finished.
    session = client.get(f"/api/sessions/{session_id}").json["session"]
    assert session["status"] == "Completed", session["error_message"]
    assert session["completed_at"] and session["progress"]["stage"] is None

    info = session["pipeline_info"]
    assert info["embedding_backend"] == "hashing" and info["document_count"] == 3
    assert set(info["stage_seconds"]) == {
        "parsing", "preprocessing", "keywords", "entities", "embeddings", "topics", "overlap", "scoring", "saving"
    }
    assert any("Hashing embeddings" in w for w in info["warnings"])
    assert db.session.query(NLPResult).count() == 3

    keywords = client.get(f"/api/sessions/{session_id}/keywords").json
    assert keywords["corpus_keywords"] and len(keywords["documents"]) == 3
    assert keywords["documents"][0]["document_id"] == doc_ids[0]

    entities = client.get(f"/api/sessions/{session_id}/entities").json
    demand = {e["text"]: e for e in entities["skill_demand"]}
    assert {"Kubernetes", "Penetration Testing", "CISSP", "Machine Learning"} <= set(demand)
    assert demand["Kubernetes"]["document_ids"] == [doc_ids[0]]
    certs = client.get(f"/api/sessions/{session_id}/entities?label=CERT").json["skill_demand"]
    assert certs and all(e["label"] == "CERT" for e in certs)
    assert client.get(f"/api/sessions/{session_id}/entities?label=FOO").status_code == 422

    topics = client.get(f"/api/sessions/{session_id}/topics").json
    assert topics["method"] == "bertopic" and topics["topics"]
    assert all("embedding" not in t for t in topics["topics"])
    assert {"label", "keywords", "size", "relevance", "representative_passages", "document_counts"} <= set(topics["topics"][0])

    everything = client.get(f"/api/sessions/{session_id}/results").json
    assert everything["pipeline_info"]["topic_count"] == len(topics["topics"])
    assert all("embedding" not in d for d in everything["documents"])
    assert all("embedding" not in t for t in everything["corpus"]["topics"])

    actions = [a.action_type for a in db.session.query(AuditLog).order_by(AuditLog.log_id)]
    assert "SESSION_RUN" in actions and "SESSION_RUN_COMPLETED" in actions


def test_completed_session_cannot_be_rerun(client, job_session):
    session_id, _ = job_session
    client.post(f"/api/sessions/{session_id}/run")
    resp = client.post(f"/api/sessions/{session_id}/run")
    assert resp.status_code == 409 and resp.json["error"]["code"] == "SESSION_NOT_RUNNABLE"


def test_processing_session_cannot_be_started_twice(client, db, job_session):
    session_id, _ = job_session
    session = db.session.get(AnalysisSession, session_id)
    session.status = SessionStatus.PROCESSING
    db.session.commit()
    assert client.post(f"/api/sessions/{session_id}/run").status_code == 409


def test_results_not_ready_before_completion(client, job_session):
    session_id, _ = job_session
    for endpoint in ("results", "keywords", "entities", "topics"):
        resp = client.get(f"/api/sessions/{session_id}/{endpoint}")
        assert resp.status_code == 409 and resp.json["error"]["code"] == "RESULTS_NOT_READY"
    assert client.get("/api/sessions/999/topics").status_code == 404


def test_pipeline_failure_marks_session_failed_and_allows_retry(client, db, job_session, monkeypatch):
    session_id, _ = job_session
    import app.services.analysis as analysis

    def boom(*args, **kwargs):
        raise RuntimeError("model exploded")

    monkeypatch.setattr(analysis, "extract_entities", boom)
    assert client.post(f"/api/sessions/{session_id}/run").status_code == 202
    session = client.get(f"/api/sessions/{session_id}").json["session"]
    assert session["status"] == "Failed"
    assert "model exploded" in session["error_message"]
    assert db.session.query(AuditLog).filter_by(action_type="SESSION_RUN_FAILED").one().detail["stage"] == "entities"

    monkeypatch.undo()
    assert client.post(f"/api/sessions/{session_id}/run").status_code == 202
    assert client.get(f"/api/sessions/{session_id}").json["session"]["status"] == "Completed"


def test_queue_unavailable_restores_status(client, job_session, monkeypatch):
    session_id, _ = job_session
    from app.tasks import run_analysis_task

    def fail(*args, **kwargs):
        raise ConnectionError("redis down")

    monkeypatch.setattr(run_analysis_task, "delay", fail)
    resp = client.post(f"/api/sessions/{session_id}/run")
    assert resp.status_code == 503 and resp.json["error"]["code"] == "QUEUE_UNAVAILABLE"
    assert client.get(f"/api/sessions/{session_id}").json["session"]["status"] == "Pending"


def test_reference_documents_excluded_from_demand(client, make_user, login, db, core_document):
    make_user("admin", role=Role.ADMIN)
    login("admin")
    job = upload_text(client, theme_text("cloud"), "cloud.txt")
    core = upload_text(client, theme_text("security", seed=1), "core.txt", category="NUC Core Reference")
    session_id = client.post("/api/sessions", json={"session_name": "s", "document_ids": [job, core]}).json["session"]["session_id"]
    client.post(f"/api/sessions/{session_id}/run")

    info = client.get(f"/api/sessions/{session_id}").json["session"]["pipeline_info"]
    assert info["reference_document_count"] == 1 and info["analysis_document_count"] == 1
    demand = {e["text"] for e in client.get(f"/api/sessions/{session_id}/entities").json["skill_demand"]}
    assert "Kubernetes" in demand and "Penetration Testing" not in demand
    docs = client.get(f"/api/sessions/{session_id}/entities").json["documents"]
    assert any(e["text"] == "Penetration Testing" for e in docs[1]["entities"])  # still processed per document
    topics = client.get(f"/api/sessions/{session_id}/topics").json["topics"]
    assert topics and all([c["document_id"] for c in t["document_counts"]] == [job] for t in topics)


def test_reference_only_session_fails_with_reason(client, make_user, login, core_document):
    make_user("admin", role=Role.ADMIN)
    login("admin")
    core = upload_text(client, theme_text("security"), "core.txt", category="NUC Core Reference")
    session_id = client.post("/api/sessions", json={"session_name": "s", "document_ids": [core]}).json["session"]["session_id"]
    client.post(f"/api/sessions/{session_id}/run")
    session = client.get(f"/api/sessions/{session_id}").json["session"]
    assert session["status"] == "Failed" and "only NUC Core Reference" in session["error_message"]


def test_permissions(client, job_session, make_user, login):
    session_id, _ = job_session
    client.post("/api/auth/logout")
    make_user("viewer", role=Role.VIEWER)
    login("viewer")
    assert client.post(f"/api/sessions/{session_id}/run").status_code == 403
    client.post("/api/auth/logout")
    make_user("other", role=Role.PLANNER)
    login("other")
    assert client.post(f"/api/sessions/{session_id}/run").status_code == 403


def test_run_requires_a_core_reference(client, planner):
    doc = upload_text(client, theme_text("cloud"), "cloud.txt")
    session_id = client.post("/api/sessions", json={"session_name": "s", "document_ids": [doc]}).json["session"]["session_id"]
    resp = client.post(f"/api/sessions/{session_id}/run")
    assert resp.status_code == 409 and resp.json["error"]["code"] == "NO_CORE_REFERENCE"
    assert client.get(f"/api/sessions/{session_id}").json["session"]["status"] == "Pending"


def test_stale_runs_are_failed_and_retryable(app, client, db, job_session):
    from datetime import datetime, timedelta, timezone

    from app.services.analysis import fail_stale_runs

    session_id, _ = job_session
    session = db.session.get(AnalysisSession, session_id)
    session.status = SessionStatus.PROCESSING
    session.progress_stage = "topics"
    session.heartbeat_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db.session.commit()
    assert fail_stale_runs(30) == []  # recent heartbeat: still running

    session.heartbeat_at = datetime.now(timezone.utc) - timedelta(minutes=45)
    db.session.commit()
    assert fail_stale_runs(30) == [session_id]
    data = client.get(f"/api/sessions/{session_id}").json["session"]
    assert data["status"] == "Failed" and "stopped responding (stage: topics)" in data["error_message"]
    assert db.session.query(AuditLog).filter_by(action_type="SESSION_RUN_STALE").count() == 1
    assert client.post(f"/api/sessions/{session_id}/run").status_code == 202  # retry works

    result = app.test_cli_runner().invoke(args=["fail-stale-runs", "--minutes", "30"])
    assert result.exit_code == 0 and "Marked 0 stale" in result.output


def test_run_records_heartbeat(client, db, job_session, monkeypatch):
    from app.tasks import run_analysis_task

    session_id, _ = job_session
    monkeypatch.setattr(run_analysis_task, "delay", lambda *_: None)  # leave it queued
    client.post(f"/api/sessions/{session_id}/run")
    db.session.expire_all()
    session = db.session.get(AnalysisSession, session_id)
    assert session.status is SessionStatus.PROCESSING and session.heartbeat_at is not None
