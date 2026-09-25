"""Analysis sessions: API rules and full pipeline runs on a SYNTHETIC corpus.

Documents are uploaded and ingested for real (with the fake encoder instead of SBERT), and the
analysis job runs eagerly, so these tests exercise every pipeline stage end to end.
"""

from __future__ import annotations

import io

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import (
    AnalysisSession,
    AuditLog,
    Document,
    NLPResult,
    Recommendation,
    RecommendationEvidence,
    Setting,
)
from app.services import analysis as analysis_service
from app.services.exceptions import AnalysisError
from tests.conftest import ApiClient
from tests.corpus import NUC_CORE_TEXT, THEMES, corpus, document_text


def upload_text(client: ApiClient, name: str, text: str, category: str = "job_market") -> int:
    response = client.post(
        "/api/documents",
        data={"files": [(io.BytesIO(text.encode()), name)], "categories": [category]},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["data"]["accepted"][0]["id"]


def upload_core(client: ApiClient, text: str = NUC_CORE_TEXT * 3) -> int:
    response = client.post(
        "/api/nuc-core",
        data={
            "version_label": "Synthetic core v1",
            "file": (io.BytesIO(text.encode()), "core.txt"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["data"]["id"]


@pytest.fixture
def admin(login_as) -> ApiClient:
    return login_as("admin")


@pytest.fixture
def planner(login_as) -> ApiClient:
    return login_as("planner")


@pytest.fixture
def corpus_ids(planner: ApiClient) -> list[int]:
    """Nine synthetic documents: three per theme, across categories."""
    categories = ["job_market", "institutional", "academic"]
    return [
        upload_text(planner, f"synthetic {theme} {n}.txt", text, categories[n % 3])
        for n, (theme, text) in enumerate(corpus(documents_per_theme=3, sentences=20))
    ]


def create(client: ApiClient, document_ids: list[int], **extra):
    return client.post(
        "/api/sessions",
        json={"session_name": "Synthetic session", "document_ids": document_ids, **extra},
    )


# ---------------------------------------------------------------------------- create


def test_defaults_report_settings_limit_and_nuc_core(planner: ApiClient, admin: ApiClient) -> None:
    before = planner.get("/api/sessions/defaults").get_json()["data"]
    upload_core(admin)
    after = planner.get("/api/sessions/defaults").get_json()["data"]

    assert before["parameters"]["weights"] == {"ner": 0.40, "topic": 0.35, "novelty": 0.25}
    assert before["parameters"]["similarity_threshold"] == 0.80
    assert before["max_documents"] == 50
    assert before["nuc_core_version"] is None
    assert after["nuc_core_version"]["version_label"] == "Synthetic core v1"


def test_create_snapshots_parameters_and_links_documents(
    planner: ApiClient, corpus_ids: list[int]
) -> None:
    response = create(
        planner,
        corpus_ids[:3],
        parameters={
            "weights": {"ner": 0.5, "topic": 0.3, "novelty": 0.2},
            "max_recommendations": 5,
        },
    )

    assert response.status_code == 201
    data = response.get_json()["data"]
    assert data["status"] == "pending"
    assert [d["id"] for d in data["documents"]] == corpus_ids[:3]
    config = data["parameter_config"]
    assert config["weights"] == {"ner": 0.5, "topic": 0.3, "novelty": 0.2}
    assert config["max_recommendations"] == 5
    assert config["similarity_threshold"] == 0.80  # default kept
    assert config["sbert_model"] == "all-MiniLM-L6-v2"
    actions = db.session.scalars(select(AuditLog.action_type)).all()
    assert "session.created" in actions and "session.run" not in actions


@pytest.mark.parametrize(
    ("body", "field_or_message"),
    [
        ({"parameters": {"weights": {"ner": 0.5, "topic": 0.5, "novelty": 0.5}}}, "sum to 1.0"),
        ({"parameters": {"similarity_threshold": 1.5}}, "similarity_threshold"),
        ({"parameters": {"max_recommendations": 0}}, "max_recommendations"),
        ({"session_name": ""}, "session_name"),
    ],
)
def test_create_validates_the_request(
    planner: ApiClient, corpus_ids: list[int], body: dict, field_or_message: str
) -> None:
    payload = {"session_name": "S", "document_ids": corpus_ids[:1], **body}

    response = planner.post("/api/sessions", json=payload)

    assert response.status_code == 422
    assert field_or_message in str(response.get_json()["error"]["details"])


def test_create_rejects_documents_that_cannot_be_analysed(
    planner: ApiClient, admin: ApiClient, corpus_ids: list[int]
) -> None:
    core_version = upload_core(admin)
    core_document = admin.get("/api/nuc-core").get_json()["data"]["active"]["document"]["id"]
    failed = upload_text(planner, "numbers.txt", "123 456. 789.")
    assert core_version

    response = create(planner, [corpus_ids[0], core_document, failed, 999999, corpus_ids[0]])
    duplicates = response.get_json()["error"]["details"]["fields"]["document_ids"]
    assert "only be selected once" in duplicates[0]

    response = create(planner, [corpus_ids[0], core_document, failed, 999999])
    problems = response.get_json()["error"]["details"]["fields"]["document_ids"]
    assert response.status_code == 422
    assert any("NUC core document" in p for p in problems)
    assert any("not ready (failed)" in p for p in problems)
    assert any("999999 does not exist" in p for p in problems)


def test_create_enforces_the_document_limit(planner: ApiClient, corpus_ids: list[int]) -> None:
    db.session.merge(Setting(key="max_documents_per_session", value=2))
    db.session.commit()

    response = create(planner, corpus_ids[:3])

    assert response.status_code == 422
    assert "at most 2" in response.get_json()["error"]["message"]


def test_create_and_run_needs_an_active_nuc_core(planner: ApiClient, corpus_ids: list[int]) -> None:
    response = create(planner, corpus_ids, run=True)

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "NO_NUC_CORE"
    assert db.session.query(AnalysisSession).count() == 0


# ------------------------------------------------------------------------ full run


def test_full_pipeline_run_produces_ranked_recommendations(
    planner: ApiClient, admin: ApiClient, corpus_ids: list[int]
) -> None:
    upload_core(admin)

    response = create(planner, corpus_ids, run=True)

    assert response.status_code == 201
    session_id = response.get_json()["data"]["id"]
    detail = planner.get(f"/api/sessions/{session_id}").get_json()["data"]
    assert detail["status"] == "completed", detail["error_message"]
    assert detail["current_stage"] == "completed" and detail["progress_percent"] == 100
    assert detail["nuc_core_version"]["version_label"] == "Synthetic core v1"
    assert set(detail["stage_timings"]) >= {
        "validating", "loading", "keywords", "skills", "embeddings", "themes", "overlap", "scoring"
    }  # fmt: skip
    assert detail["topic_count"] >= 2
    assert detail["recommendation_count"] == detail["topic_count"]

    recommendations = db.session.scalars(
        select(Recommendation)
        .where(Recommendation.session_id == session_id)
        .order_by(Recommendation.rank)
    ).all()
    assert [r.rank for r in recommendations] == list(range(1, len(recommendations) + 1))
    composites = [r.composite_score for r in recommendations]
    assert composites == sorted(composites, reverse=True)
    for rec in recommendations:
        assert rec.topic_title == rec.auto_title and rec.topic_description
        assert 0 <= rec.novelty_score <= 1 and 0 <= rec.ner_score <= 1 and 0 <= rec.topic_score <= 1
        assert rec.closest_nuc_passage_id is not None
        evidence = db.session.scalars(
            select(RecommendationEvidence).where(RecommendationEvidence.recommendation_id == rec.id)
        ).all()
        assert 1 <= len(evidence) <= 8
    # Skill names come from the seeded patterns? (none seeded in this test) - keywords must exist.
    assert all(rec.keywords for rec in recommendations)

    results = {r.result_type: r.payload for r in db.session.scalars(select(NLPResult))}
    assert set(results) == {"tfidf", "entities", "topics", "similarity"}
    assert results["tfidf"]["overall"]
    assert set(results["tfidf"]["by_category"]) == {"job_market", "institutional", "academic"}
    assert results["similarity"]["threshold"] == 0.80
    assert len(results["topics"]["topics"]) == detail["topic_count"]


def test_max_recommendations_limits_the_stored_list(
    planner: ApiClient, admin: ApiClient, corpus_ids: list[int]
) -> None:
    upload_core(admin)

    session_id = create(
        planner, corpus_ids, run=True, parameters={"max_recommendations": 1}
    ).get_json()["data"]["id"]

    detail = planner.get(f"/api/sessions/{session_id}").get_json()["data"]
    assert detail["recommendation_count"] == 1
    assert detail["topic_count"] >= 2  # all themes are still reported as evidence


def test_themes_matching_the_nuc_core_are_flagged_as_duplicates(
    planner: ApiClient, admin: ApiClient, corpus_ids: list[int]
) -> None:
    # A synthetic "core" made of security sentences overlaps the security theme.
    upload_core(admin, document_text("security", 20, seed=999))

    session_id = create(planner, corpus_ids, run=True).get_json()["data"]["id"]

    similarity = db.session.scalar(
        select(NLPResult.payload).where(
            NLPResult.session_id == session_id, NLPResult.result_type == "similarity"
        )
    )
    most_similar = max(similarity["candidates"], key=lambda c: c["max_similarity"])
    security_words = {w.lower() for obj in THEMES["security"]["objects"] for w in obj.split()}
    assert set(most_similar["title"].lower().replace(",", "").split()) & security_words
    assert most_similar["overlap_status"] == "Potential Duplicate"
    assert any(c["overlap_status"] == "No Significant Overlap" for c in similarity["candidates"])


# ------------------------------------------------------------------ failures/retry


def test_too_little_text_fails_at_the_themes_stage(planner: ApiClient, admin: ApiClient) -> None:
    upload_core(admin)
    tiny = upload_text(planner, "tiny.txt", document_text("cloud", 6, seed=1))

    session_id = create(planner, [tiny], run=True).get_json()["data"]["id"]

    detail = planner.get(f"/api/sessions/{session_id}").get_json()["data"]
    assert detail["status"] == "failed"
    assert detail["current_stage"] == "themes"
    assert "Too little text to discover themes" in detail["error_message"]
    assert detail["recommendation_count"] == 0


def test_unexpected_errors_are_reported_generically(
    planner: ApiClient, admin: ApiClient, corpus_ids: list[int], monkeypatch
) -> None:
    upload_core(admin)

    def explode(*_args, **_kwargs):
        raise RuntimeError("internal detail")

    monkeypatch.setattr("app.tasks.analysis.run_analysis", explode)
    session_id = create(planner, corpus_ids, run=True).get_json()["data"]["id"]

    detail = planner.get(f"/api/sessions/{session_id}").get_json()["data"]
    assert detail["status"] == "failed"
    assert "failed unexpectedly during the loading stage" in detail["error_message"]
    assert "internal detail" not in detail["error_message"]


def test_retry_runs_a_failed_session_again(
    planner: ApiClient, admin: ApiClient, corpus_ids: list[int], monkeypatch
) -> None:
    upload_core(admin)
    real_run = analysis_service.run_analysis
    calls = {"count": 0}

    def fail_once(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise AnalysisError("Simulated failure.")
        return real_run(*args, **kwargs)

    monkeypatch.setattr("app.tasks.analysis.run_analysis", fail_once)
    session_id = create(planner, corpus_ids, run=True).get_json()["data"]["id"]
    assert planner.get(f"/api/sessions/{session_id}").get_json()["data"]["status"] == "failed"

    response = planner.post(f"/api/sessions/{session_id}/retry")

    assert response.status_code == 202
    detail = planner.get(f"/api/sessions/{session_id}").get_json()["data"]
    assert detail["status"] == "completed"
    assert detail["error_message"] is None and detail["recommendation_count"] > 0


def test_run_and_retry_state_rules(
    planner: ApiClient, admin: ApiClient, corpus_ids: list[int]
) -> None:
    pending_id = create(planner, corpus_ids).get_json()["data"]["id"]

    assert planner.post(f"/api/sessions/{pending_id}/run").status_code == 409  # no NUC core yet
    assert planner.post(f"/api/sessions/{pending_id}/retry").status_code == 409  # not failed

    upload_core(admin)
    assert planner.post(f"/api/sessions/{pending_id}/run").status_code == 202
    again = planner.post(f"/api/sessions/{pending_id}/run")
    assert again.status_code == 409 and "already completed" in again.get_json()["error"]["message"]


# ------------------------------------------------------------------- list/get/delete


def test_list_filters_and_counts(
    planner: ApiClient, admin: ApiClient, corpus_ids: list[int]
) -> None:
    upload_core(admin)
    create(planner, corpus_ids[:2])
    create(planner, corpus_ids, run=True)

    everything = planner.get("/api/sessions").get_json()["data"]
    completed = planner.get("/api/sessions?status=completed").get_json()["data"]["items"]

    assert everything["pagination"]["total"] == 2
    assert len(completed) == 1 and completed[0]["document_count"] == 9
    assert completed[0]["recommendation_count"] > 0
    assert planner.get("/api/sessions?search=nothing-matches").get_json()["data"]["items"] == []


def test_delete_keeps_documents_but_not_while_processing(
    planner: ApiClient, corpus_ids: list[int]
) -> None:
    session_id = create(planner, corpus_ids[:2]).get_json()["data"]["id"]
    db.session.get(AnalysisSession, session_id).status = "processing"
    db.session.commit()
    assert planner.delete(f"/api/sessions/{session_id}").status_code == 409

    db.session.get(AnalysisSession, session_id).status = "failed"
    db.session.commit()
    assert planner.delete(f"/api/sessions/{session_id}").status_code == 200
    assert db.session.get(AnalysisSession, session_id) is None
    assert db.session.query(Document).count() == len(corpus_ids)


def test_unknown_session_is_404(planner: ApiClient) -> None:
    assert planner.get("/api/sessions/424242").status_code == 404


def test_viewers_can_read_but_not_change(
    login_as, planner: ApiClient, corpus_ids: list[int]
) -> None:
    session_id = create(planner, corpus_ids[:1]).get_json()["data"]["id"]
    viewer = login_as("viewer")

    assert viewer.get("/api/sessions").status_code == 200
    assert viewer.get(f"/api/sessions/{session_id}").status_code == 200
    assert create(viewer, corpus_ids[:1]).status_code == 403
    assert viewer.post(f"/api/sessions/{session_id}/run").status_code == 403
    assert viewer.post(f"/api/sessions/{session_id}/retry").status_code == 403
    assert viewer.delete(f"/api/sessions/{session_id}").status_code == 403


# ------------------------------------------------------------- direct pipeline checks


def test_run_analysis_rejects_missing_inputs() -> None:
    from app.services.analysis import AnalysisParameters, run_analysis
    from app.services.recommendations.scoring import ScoreWeights

    parameters = AnalysisParameters(weights=ScoreWeights(0.4, 0.35, 0.25))
    with pytest.raises(AnalysisError, match="no extracted passages"):
        run_analysis([], [], parameters, None, {})  # type: ignore[arg-type]
