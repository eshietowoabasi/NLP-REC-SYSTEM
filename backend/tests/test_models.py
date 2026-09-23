import pytest
from sqlalchemy.exc import IntegrityError, StatementError

from app.models import (
    AnalysisSession,
    CurriculumMap,
    Document,
    DocumentSession,
    FileType,
    NLPResult,
    OverlapStatus,
    PlannerDecision,
    Recommendation,
    Role,
    SessionStatus,
    SourceCategory,
)


def _document(user, title="Job ads 2025"):
    return Document(
        user_id=user.user_id,
        title=title,
        file_path=f"/data/raw/{title}.pdf",
        file_type=FileType.PDF,
        source_category=SourceCategory.JOB_MARKET,
    )


def _recommendation(session, **overrides):
    values = dict(
        session_id=session.session_id,
        topic_title="Cloud Security Engineering",
        ner_score=0.82,
        topic_score=0.76,
        novelty_score=0.91,
        composite_score=0.83,
        max_similarity=0.09,
        overlap_status=OverlapStatus.NO_SIGNIFICANT_OVERLAP,
    )
    values.update(overrides)
    return Recommendation(**values)


@pytest.fixture()
def graph(db, make_user):
    user = make_user()
    doc = _document(user)
    session = AnalysisSession(user_id=user.user_id, session_name="2026 Review")
    db.session.add_all([doc, session])
    db.session.commit()
    return user, doc, session


def test_user_password_is_hashed_with_bcrypt(make_user):
    user = make_user(password="correct horse")
    assert user.password_hash.startswith("$2")
    assert "correct horse" not in user.password_hash
    assert user.check_password("correct horse")
    assert not user.check_password("wrong")


def test_defaults(graph):
    user, doc, session = graph
    assert user.role is Role.PLANNER
    assert session.status is SessionStatus.PENDING
    assert doc.processing_status.value == "Uploaded"
    assert session.created_at is not None and doc.upload_timestamp is not None


def test_full_relationship_graph(db, graph):
    user, doc, session = graph
    link = DocumentSession(document_id=doc.document_id, session_id=session.session_id, processing_order=1)
    db.session.add(link)
    db.session.flush()
    db.session.add(NLPResult(doc_session_id=link.doc_session_id, tfidf_keywords=[["python", 0.4]], embedding=[0.1, 0.2]))
    rec = _recommendation(session, planner_decision=PlannerDecision.ACCEPTED)
    db.session.add(rec)
    db.session.flush()
    db.session.add(CurriculumMap(rec_id=rec.rec_id, course_code="CSC 413", course_title="Cloud Security", credit_units=3, learning_outcomes=["Explain IAM"]))
    db.session.commit()

    assert user.documents == [doc] and user.sessions == [session]
    assert session.document_links[0].document is doc
    assert link.nlp_results[0].embedding == [0.1, 0.2]
    assert session.recommendations[0].curriculum_maps[0].course_code == "CSC 413"
    assert rec.to_dict()["planner_decision"] == "Accepted"


def test_document_can_only_be_linked_to_a_session_once(db, graph):
    _, doc, session = graph
    db.session.add(DocumentSession(document_id=doc.document_id, session_id=session.session_id))
    db.session.commit()
    db.session.add(DocumentSession(document_id=doc.document_id, session_id=session.session_id))
    with pytest.raises(IntegrityError):
        db.session.commit()


@pytest.mark.parametrize("units", [0, 4, 6])
def test_credit_units_restricted_to_1_2_3(db, graph, units):
    _, _, session = graph
    rec = _recommendation(session)
    db.session.add(rec)
    db.session.flush()
    db.session.add(CurriculumMap(rec_id=rec.rec_id, course_code="CSC 499", course_title="X", credit_units=units))
    with pytest.raises(IntegrityError):
        db.session.commit()


@pytest.mark.parametrize("field", ["ner_score", "topic_score", "novelty_score", "composite_score", "max_similarity"])
@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_scores_must_be_between_0_and_1(db, graph, field, value):
    _, _, session = graph
    db.session.add(_recommendation(session, **{field: value}))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_enum_rejects_unknown_values(db, graph):
    user, _, _ = graph
    doc = _document(user, "bad")
    doc.source_category = "Social Media"
    db.session.add(doc)
    with pytest.raises(StatementError):
        db.session.commit()


def test_deleting_session_cascades(db, graph):
    _, doc, session = graph
    db.session.add(DocumentSession(document_id=doc.document_id, session_id=session.session_id))
    db.session.add(_recommendation(session))
    db.session.commit()
    db.session.delete(session)
    db.session.commit()
    assert db.session.query(DocumentSession).count() == 0
    assert db.session.query(Recommendation).count() == 0
    assert db.session.get(Document, doc.document_id) is not None
