"""Evidence results, recommendation review and curriculum mapping (SYNTHETIC data)."""

from __future__ import annotations

import io

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import (
    AuditLog,
    CurriculumMap,
    Setting,
)
from tests.conftest import ApiClient
from tests.corpus import NUC_CORE_TEXT, corpus
from tests.review_data import ReviewSession, build_review_session


@pytest.fixture
def review(make_user) -> ReviewSession:
    """A completed session with three recommendations, built directly in the database."""
    return build_review_session(make_user("planner", username="owner"))


@pytest.fixture
def planner(login_as) -> ApiClient:
    return login_as("planner")


MAPPING = {
    "course_code": " csc  419 ",
    "course_title": "Cloud Security Engineering",
    "credit_units": 3,
    "prerequisites": ["CSC 301", " CSC 302 "],
    "learning_outcomes": ["Secure cloud workloads", "Operate Kubernetes clusters"],
}


def accept(client: ApiClient, rec_id: int):
    return client.patch(f"/api/recommendations/{rec_id}/decision", json={"decision": "accepted"})


# --------------------------------------------------------------------------- results


def test_results_endpoints_return_enriched_payloads(
    planner: ApiClient, review: ReviewSession
) -> None:
    sid = review.session.id

    keywords = planner.get(f"/api/sessions/{sid}/keywords").get_json()["data"]
    policy_only = planner.get(f"/api/sessions/{sid}/keywords?category=policy").get_json()["data"]
    entities = planner.get(f"/api/sessions/{sid}/entities").get_json()["data"]
    topics = planner.get(f"/api/sessions/{sid}/topics").get_json()["data"]
    similarity = planner.get(f"/api/sessions/{sid}/similarity").get_json()["data"]

    assert keywords["overall"][0]["term"] == "cloud"
    assert set(policy_only["by_category"]) == {"policy"}
    assert entities["skills"][0]["name"] == "Kubernetes"
    assert topics["topics"][0]["samples"][0]["document_title"] == "Synthetic cloud advert"
    assert similarity["candidates"][0]["closest_nuc_passage"]["page_number"] == 4
    assert similarity["nuc_core_version"]["version_label"] == "Synthetic core"


def test_results_need_a_completed_session(planner: ApiClient, review: ReviewSession) -> None:
    review.session.status = "processing"
    db.session.commit()

    response = planner.get(f"/api/sessions/{review.session.id}/keywords")

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "RESULTS_NOT_READY"
    assert planner.get("/api/sessions/9999/topics").status_code == 404
    review.session.status = "completed"
    db.session.commit()
    assert (
        planner.get(f"/api/sessions/{review.session.id}/keywords?category=bogus").status_code == 422
    )


def test_results_endpoints_after_a_real_pipeline_run(login_as) -> None:
    """End to end: upload, run the real pipeline, read every evidence endpoint."""
    admin = login_as("admin")
    admin.post(
        "/api/nuc-core",
        data={
            "version_label": "v1",
            "file": (io.BytesIO((NUC_CORE_TEXT * 3).encode()), "core.txt"),
        },
        content_type="multipart/form-data",
    )
    ids = []
    for n, (theme, text) in enumerate(corpus(3, 20)):
        response = admin.post(
            "/api/documents",
            data={
                "files": [(io.BytesIO(text.encode()), f"{theme}{n}.txt")],
                "categories": ["job_market"],
            },
            content_type="multipart/form-data",
        )
        ids.append(response.get_json()["data"]["accepted"][0]["id"])
    sid = admin.post(
        "/api/sessions", json={"session_name": "E2E", "document_ids": ids, "run": True}
    ).get_json()["data"]["id"]

    for name in ("keywords", "entities", "topics", "similarity"):
        assert admin.get(f"/api/sessions/{sid}/{name}").status_code == 200
    recs = admin.get(f"/api/sessions/{sid}/recommendations").get_json()["data"]
    detail = admin.get(f"/api/recommendations/{recs['items'][0]['id']}").get_json()["data"]
    assert detail["evidence"] and detail["evidence"][0]["document"]["title"]
    assert detail["closest_nuc_passage"]["version_label"] == "v1"


# ------------------------------------------------------------------- recommendations


def test_list_in_rank_order_with_counts_and_filters(
    planner: ApiClient, review: ReviewSession
) -> None:
    sid = review.session.id
    accept(planner, review.recommendations[0].id)
    planner.patch(
        f"/api/recommendations/{review.recommendations[2].id}/decision",
        json={"decision": "flagged"},
    )

    data = planner.get(f"/api/sessions/{sid}/recommendations").get_json()["data"]

    assert [r["rank"] for r in data["items"]] == [1, 2, 3]
    assert data["counts"] == {
        "total": 3,
        "reviewed": 2,
        "undecided": 1,
        "accepted": 1,
        "rejected": 0,
        "flagged": 1,
        "potential_duplicates": 1,
    }

    def titles(query: str) -> list[str]:
        items = planner.get(f"/api/sessions/{sid}/recommendations?{query}").get_json()["data"][
            "items"
        ]
        return [r["topic_title"] for r in items]

    assert titles("decision=undecided") == ["Operating Systems"]
    assert titles("decision=accepted") == ["Cloud Security and Kubernetes"]
    assert titles("hide_duplicates=true") == [
        "Cloud Security and Kubernetes",
        "Payment Integration",
    ]
    assert planner.get(f"/api/sessions/{sid}/recommendations?decision=maybe").status_code == 422
    assert planner.get("/api/sessions/9999/recommendations").status_code == 404


def test_detail_includes_evidence_nuc_passage_and_session_context(
    planner: ApiClient, review: ReviewSession
) -> None:
    detail = planner.get(f"/api/recommendations/{review.recommendations[1].id}").get_json()["data"]

    assert detail["overlap_status"] == "Potential Duplicate"
    assert [e["relevance_score"] for e in detail["evidence"]] == pytest.approx([0.9, 0.8, 0.7])
    assert detail["evidence"][0]["document"] == {
        "id": review.documents[0].id,
        "title": "Synthetic cloud advert",
        "source_category": "job_market",
    }
    assert detail["evidence"][0]["page_number"] == 1
    assert detail["closest_nuc_passage"] == {
        "id": review.nuc_passage.id,
        "text": "Synthetic core passage on operating systems.",
        "page_number": 4,
        "document_title": "Synthetic NUC core",
        "version_label": "Synthetic core",
    }
    assert detail["session"]["weights"] == {"ner": 0.4, "topic": 0.35, "novelty": 0.25}
    assert detail["mapping"] is None and detail["has_mapping"] is False
    assert planner.get("/api/recommendations/9999").status_code == 404


def test_edit_title_and_description_keeps_the_machine_title(
    planner: ApiClient, review: ReviewSession
) -> None:
    rec_id = review.recommendations[0].id

    response = planner.patch(
        f"/api/recommendations/{rec_id}",
        json={"topic_title": "  Cloud Security Engineering ", "topic_description": "Edited."},
    )

    data = response.get_json()["data"]
    assert data["topic_title"] == "Cloud Security Engineering"
    assert data["auto_title"] == "Cloud Security and Kubernetes"
    assert data["topic_description"] == "Edited."
    entry = db.session.scalars(
        select(AuditLog).where(AuditLog.action_type == "recommendation.edited")
    ).one()
    assert entry.detail["topic_title"]["from"] == "Cloud Security and Kubernetes"
    assert planner.patch(f"/api/recommendations/{rec_id}", json={}).status_code == 422
    assert (
        planner.patch(f"/api/recommendations/{rec_id}", json={"topic_title": ""}).status_code == 422
    )


def test_decisions_record_who_when_and_notes(planner: ApiClient, review: ReviewSession) -> None:
    rec_id = review.recommendations[1].id

    response = planner.patch(
        f"/api/recommendations/{rec_id}/decision",
        json={"decision": "rejected", "notes": "Already covered by the core."},
    )

    data = response.get_json()["data"]
    assert data["planner_decision"] == "rejected"
    assert data["planner_notes"] == "Already covered by the core."
    assert data["decided_by"]["full_name"] == planner.user.full_name and data["decided_at"]
    cleared = planner.patch(f"/api/recommendations/{rec_id}/decision", json={"decision": None})
    assert cleared.get_json()["data"]["planner_decision"] is None
    assert cleared.get_json()["data"]["decided_at"] is None
    actions = db.session.scalars(
        select(AuditLog.detail).where(AuditLog.action_type == "recommendation.decided")
    ).all()
    assert [(a["from"], a["to"]) for a in actions] == [(None, "rejected"), ("rejected", None)]
    bad = planner.patch(f"/api/recommendations/{rec_id}/decision", json={"decision": "maybe"})
    assert bad.status_code == 422


def test_viewers_cannot_change_recommendations(login_as, review: ReviewSession) -> None:
    viewer = login_as("viewer")
    rec_id = review.recommendations[0].id

    assert viewer.get(f"/api/recommendations/{rec_id}").status_code == 200
    assert (
        viewer.patch(f"/api/recommendations/{rec_id}", json={"topic_title": "x"}).status_code == 403
    )
    assert accept(viewer, rec_id).status_code == 403
    assert viewer.post(f"/api/recommendations/{rec_id}/mapping", json=MAPPING).status_code == 403


# --------------------------------------------------------------------------- mapping


def test_only_accepted_recommendations_can_be_mapped(
    planner: ApiClient, review: ReviewSession
) -> None:
    rec_id = review.recommendations[0].id

    refused = planner.post(f"/api/recommendations/{rec_id}/mapping", json=MAPPING)
    accept(planner, rec_id)
    created = planner.post(f"/api/recommendations/{rec_id}/mapping", json=MAPPING)

    assert refused.status_code == 409 and "Only accepted" in refused.get_json()["error"]["message"]
    assert created.status_code == 201
    mapping = created.get_json()["data"]
    assert mapping["course_code"] == "CSC 419"  # normalised
    assert mapping["prerequisites"] == ["CSC 301", "CSC 302"]
    assert (
        planner.get(f"/api/recommendations/{rec_id}/mapping").get_json()["data"]["id"]
        == mapping["id"]
    )
    again = planner.post(f"/api/recommendations/{rec_id}/mapping", json=MAPPING)
    assert again.status_code == 409


@pytest.mark.parametrize(
    ("override", "field"),
    [
        ({"credit_units": 4}, "credit_units"),
        ({"credit_units": 0}, "credit_units"),
        ({"course_code": "Cloud101"}, "course_code"),
        ({"learning_outcomes": []}, "learning_outcomes"),
        ({"learning_outcomes": ["Same", "same"]}, "learning_outcomes"),
        ({"course_title": ""}, "course_title"),
        ({"prerequisites": ["X"] * 11}, "prerequisites"),
    ],
)
def test_mapping_validation(
    planner: ApiClient, review: ReviewSession, override: dict, field: str
) -> None:
    rec_id = review.recommendations[0].id
    accept(planner, rec_id)

    response = planner.post(f"/api/recommendations/{rec_id}/mapping", json={**MAPPING, **override})

    assert response.status_code == 422
    assert field in response.get_json()["error"]["details"]["fields"]


def test_course_codes_are_unique_within_a_session(
    planner: ApiClient, review: ReviewSession
) -> None:
    first, _, third = review.recommendations
    accept(planner, first.id)
    accept(planner, third.id)
    planner.post(f"/api/recommendations/{first.id}/mapping", json=MAPPING)

    clash = planner.post(
        f"/api/recommendations/{third.id}/mapping", json={**MAPPING, "course_code": "CSC419"}
    )

    assert clash.status_code == 409
    assert "course_code" in clash.get_json()["error"]["details"]["fields"]


def test_update_and_delete_mapping(planner: ApiClient, review: ReviewSession) -> None:
    rec_id = review.recommendations[0].id
    accept(planner, rec_id)
    mapping_id = planner.post(f"/api/recommendations/{rec_id}/mapping", json=MAPPING).get_json()[
        "data"
    ]["id"]

    updated = planner.put(f"/api/mappings/{mapping_id}", json={**MAPPING, "credit_units": 2})
    assert updated.get_json()["data"]["credit_units"] == 2

    # The decision cannot change while the course exists.
    blocked = planner.patch(
        f"/api/recommendations/{rec_id}/decision", json={"decision": "rejected"}
    )
    assert (
        blocked.status_code == 409
        and "Remove the course mapping" in blocked.get_json()["error"]["message"]
    )

    assert planner.delete(f"/api/mappings/{mapping_id}").status_code == 200
    assert db.session.get(CurriculumMap, mapping_id) is None
    assert planner.get(f"/api/recommendations/{rec_id}/mapping").status_code == 404
    assert planner.put("/api/mappings/9999", json=MAPPING).status_code == 404
    actions = db.session.scalars(
        select(AuditLog.action_type).where(AuditLog.entity_type == "curriculum_map")
    ).all()
    assert actions == ["mapping.created", "mapping.updated", "mapping.deleted"]


def test_proposed_curriculum_totals_and_allowance(
    planner: ApiClient, review: ReviewSession
) -> None:
    first, _, third = review.recommendations
    for rec, code, units in ((first, "CSC 419", 3), (third, "CSC 421", 2)):
        accept(planner, rec.id)
        planner.post(
            f"/api/recommendations/{rec.id}/mapping",
            json={**MAPPING, "course_code": code, "credit_units": units},
        )

    without = planner.get(f"/api/sessions/{review.session.id}/curriculum").get_json()["data"]
    db.session.merge(Setting(key="credit_unit_allowance", value=12))
    db.session.commit()
    with_allowance = planner.get(f"/api/sessions/{review.session.id}/curriculum").get_json()["data"]

    assert [c["course_code"] for c in without["courses"]] == ["CSC 419", "CSC 421"]
    assert without["courses"][0]["recommendation"]["topic_title"] == "Cloud Security and Kubernetes"
    assert without["total_units"] == 5
    assert without["credit_unit_allowance"] is None and without["remaining_units"] is None
    assert with_allowance["credit_unit_allowance"] == 12 and with_allowance["remaining_units"] == 7
    assert planner.get("/api/sessions/9999/curriculum").status_code == 404
