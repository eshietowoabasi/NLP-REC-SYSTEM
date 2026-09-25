"""Dashboard summary (SYNTHETIC data)."""

from __future__ import annotations

from app.extensions import db
from app.models import AnalysisSession, CurriculumMap
from tests.review_data import build_review_session, make_document


def test_empty_system(login_as) -> None:
    data = login_as("viewer").get("/api/dashboard/summary").get_json()["data"]

    assert data["documents"]["total"] == 0
    assert data["sessions"] == {
        "total": 0,
        "by_status": {"pending": 0, "processing": 0, "completed": 0, "failed": 0},
    }
    assert data["recommendations"]["pending_review"] == 0
    assert data["courses_mapped"] == 0
    assert data["nuc_core_version"] is None
    assert data["recent_sessions"] == []


def test_counts_documents_sessions_reviews_and_courses(login_as, make_user) -> None:
    owner = make_user("planner", username="owner")
    review = build_review_session(owner)
    archived = make_document(owner.id, "Synthetic archived advert")
    archived.processing_status = "archived"
    failed = make_document(owner.id, "Synthetic broken upload", "academic")
    failed.processing_status = "failed"
    first, second, _ = review.recommendations
    first.planner_decision = "accepted"
    second.planner_decision = "rejected"
    db.session.add(
        CurriculumMap(
            recommendation_id=first.id,
            course_code="CSC 419",
            course_title="Cloud",
            credit_units=3,
            prerequisites=[],
            learning_outcomes=["x"],
            created_by_id=owner.id,
        )
    )
    db.session.add(AnalysisSession(created_by_id=owner.id, session_name="Synthetic draft"))
    db.session.commit()

    data = login_as("viewer").get("/api/dashboard/summary").get_json()["data"]

    # The NUC core and the archived document are not library documents.
    assert data["documents"] == {
        "total": 3,
        "ready": 2,
        "processing": 0,
        "failed": 1,
        "by_category": {"job_market": 1, "policy": 1, "academic": 1},
    }
    assert data["sessions"]["total"] == 2
    assert data["sessions"]["by_status"]["completed"] == 1
    assert data["recommendations"] == {
        "total": 3,
        "pending_review": 1,
        "accepted": 1,
        "rejected": 1,
        "flagged": 0,
    }
    assert data["courses_mapped"] == 1
    assert data["nuc_core_version"]["version_label"] == "Synthetic core"
    assert [s["session_name"] for s in data["recent_sessions"]] == [
        "Synthetic draft",
        "Synthetic review",
    ]
    assert data["recent_sessions"][1]["recommendation_count"] == 3


def test_requires_login(api) -> None:
    assert api.get("/api/dashboard/summary").status_code == 401
