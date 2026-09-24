"""Database-level rules of the data model (constraints enforced by PostgreSQL itself)."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    AnalysisSession,
    CurriculumMap,
    Document,
    DocumentSession,
    NucCoreVersion,
    OverlapStatus,
    Passage,
    Recommendation,
    User,
)


@pytest.fixture
def owner(make_user: Callable[..., User]) -> User:
    return make_user("planner")


def make_document(owner: User, name: str = "doc", **fields) -> Document:
    """Synthetic document row (no file on disk is needed for model tests)."""
    document = Document(
        uploaded_by_id=owner.id,
        title=f"Test {name}",
        original_filename=f"{name}.txt",
        stored_filename=f"{name}-stored.txt",
        file_type="txt",
        file_size=fields.pop("file_size", 100),
        content_hash=f"hash-of-{name}",
        source_category=fields.pop("source_category", "job_market"),
        **fields,
    )
    db.session.add(document)
    db.session.commit()
    return document


def make_recommendation(session: AnalysisSession, rank: int = 1) -> Recommendation:
    recommendation = Recommendation(
        session_id=session.id,
        rank=rank,
        topic_id=rank,
        auto_title="Cloud Security",
        topic_title="Cloud Security",
        topic_description="Synthetic test topic.",
        ner_score=0.5,
        topic_score=0.5,
        novelty_score=0.5,
        composite_score=0.5,
        max_similarity=0.5,
        overlap_status=OverlapStatus.NO_SIGNIFICANT_OVERLAP,
    )
    db.session.add(recommendation)
    db.session.commit()
    return recommendation


def assert_rejected(statement: Callable[[], None]) -> None:
    with pytest.raises(IntegrityError):
        statement()
        db.session.flush()
    db.session.rollback()


def test_user_role_is_restricted_by_a_check_constraint(owner: User) -> None:
    assert_rejected(lambda: db.session.execute(text("UPDATE users SET role = 'superuser'")))


def test_file_size_must_be_positive(owner: User) -> None:
    assert_rejected(lambda: make_document(owner, file_size=0))


def test_credit_units_must_be_1_2_or_3(owner: User) -> None:
    session = AnalysisSession(created_by_id=owner.id, session_name="Test")
    db.session.add(session)
    db.session.commit()
    recommendation = make_recommendation(session)

    for units in (1, 2, 3):
        mapping = CurriculumMap(
            recommendation_id=recommendation.id,
            course_code="CSC 499",
            course_title="Test Course",
            credit_units=units,
            created_by_id=owner.id,
        )
        db.session.add(mapping)
        db.session.commit()
        db.session.delete(mapping)
        db.session.commit()

    assert_rejected(
        lambda: db.session.add(
            CurriculumMap(
                recommendation_id=recommendation.id,
                course_code="CSC 499",
                course_title="Test Course",
                credit_units=4,
                created_by_id=owner.id,
            )
        )
    )


def test_scores_must_be_between_0_and_1(owner: User) -> None:
    session = AnalysisSession(created_by_id=owner.id, session_name="Test")
    db.session.add(session)
    db.session.commit()
    recommendation = make_recommendation(session)

    assert_rejected(
        lambda: db.session.execute(
            text("UPDATE recommendations SET novelty_score = 1.2 WHERE id = :id"),
            {"id": recommendation.id},
        )
    )


def test_only_one_nuc_core_version_can_be_active(owner: User) -> None:
    first = make_document(owner, "nuc1", source_category="nuc_core")
    second = make_document(owner, "nuc2", source_category="nuc_core")
    db.session.add(
        NucCoreVersion(
            document_id=first.id, version_label="v1", is_active=True, uploaded_by_id=owner.id
        )
    )
    db.session.commit()

    # Inactive versions are unlimited...
    db.session.add(
        NucCoreVersion(
            document_id=second.id, version_label="v2", is_active=False, uploaded_by_id=owner.id
        )
    )
    db.session.commit()

    # ...but a second active one is rejected.
    assert_rejected(
        lambda: db.session.execute(
            text("UPDATE nuc_core_versions SET is_active = true WHERE version_label = 'v2'")
        )
    )


def test_document_used_by_a_session_cannot_be_deleted(owner: User) -> None:
    document = make_document(owner)
    session = AnalysisSession(created_by_id=owner.id, session_name="Test")
    db.session.add(session)
    db.session.flush()
    db.session.add(
        DocumentSession(document_id=document.id, session_id=session.id, processing_order=1)
    )
    db.session.commit()

    assert_rejected(
        lambda: db.session.execute(
            text("DELETE FROM documents WHERE id = :id"), {"id": document.id}
        )
    )


def test_deleting_a_session_removes_its_links_but_keeps_documents(owner: User) -> None:
    document = make_document(owner)
    session = AnalysisSession(created_by_id=owner.id, session_name="Test")
    session.document_links.append(DocumentSession(document_id=document.id, processing_order=1))
    db.session.add(session)
    db.session.commit()

    db.session.delete(session)
    db.session.commit()

    assert db.session.query(DocumentSession).count() == 0
    assert db.session.get(Document, document.id) is not None


def test_passage_embedding_round_trips_through_pgvector(owner: User) -> None:
    document = make_document(owner)
    passage = Passage(
        document_id=document.id,
        position=0,
        page_number=1,
        text="Synthetic passage about Python and cloud computing.",
        normalised_text="synthetic passage python cloud computing",
        embedding=[0.1, 0.2, 0.3],
        embedding_model="test-model",
    )
    db.session.add(passage)
    db.session.commit()
    db.session.expire_all()

    stored = db.session.get(Passage, passage.id)
    assert [round(float(value), 4) for value in stored.embedding] == [0.1, 0.2, 0.3]
    assert document.passages[0].id == passage.id


def test_passage_positions_are_unique_per_document(owner: User) -> None:
    document = make_document(owner)
    for _ in range(2):
        db.session.add(
            Passage(document_id=document.id, position=0, text="Same.", normalised_text="same")
        )
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_session_progress_must_be_0_to_100(owner: User) -> None:
    assert_rejected(
        lambda: db.session.add(
            AnalysisSession(created_by_id=owner.id, session_name="Test", progress_percent=101)
        )
    )
