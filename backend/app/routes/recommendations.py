"""Recommendations: ranked list, detail with evidence, edits and planner decisions.

The system only proposes; planners accept, reject or flag each recommendation. Nothing here
changes the curriculum itself.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from flask import Blueprint, Response
from flask_login import current_user
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.audit import AuditAction, record_audit
from app.auth.decorators import EDITOR_ROLES, login_required, role_required
from app.extensions import db
from app.models import (
    AnalysisSession,
    Document,
    NucCoreVersion,
    OverlapStatus,
    Passage,
    PlannerDecision,
    Recommendation,
    RecommendationEvidence,
)
from app.schemas.documents import UserRef
from app.schemas.review import (
    DecisionIn,
    DocumentRef,
    EvidenceOut,
    MappingOut,
    NucPassageOut,
    RecommendationEdit,
    RecommendationListQuery,
    RecommendationOut,
    SessionContext,
)
from app.utils.errors import ApiError
from app.utils.responses import success
from app.utils.time import utcnow
from app.utils.validation import parse_body, parse_query

bp = Blueprint("recommendations", __name__)


def recommendation_json(rec: Recommendation) -> dict[str, Any]:
    return RecommendationOut(
        id=rec.id,
        session_id=rec.session_id,
        rank=rec.rank,
        topic_id=rec.topic_id,
        auto_title=rec.auto_title,
        topic_title=rec.topic_title,
        topic_description=rec.topic_description,
        keywords=rec.keywords or [],
        skills=rec.skills or [],
        ner_score=rec.ner_score,
        topic_score=rec.topic_score,
        novelty_score=rec.novelty_score,
        composite_score=rec.composite_score,
        max_similarity=rec.max_similarity,
        overlap_status=rec.overlap_status,
        planner_decision=rec.planner_decision,
        planner_notes=rec.planner_notes,
        decided_at=rec.decided_at,
        decided_by=UserRef.model_validate(rec.decided_by) if rec.decided_by else None,
        has_mapping=rec.mapping is not None,
    ).model_dump(mode="json")


def get_recommendation_or_404(recommendation_id: int) -> Recommendation:
    rec = db.session.get(Recommendation, recommendation_id)
    if rec is None:
        raise ApiError("NOT_FOUND", "Recommendation not found.", 404)
    return rec


@bp.get("/sessions/<int:session_id>/recommendations")
@login_required
def list_recommendations(session_id: int) -> tuple[Response, int]:
    """All recommendations of a session in rank order, with review progress.

    Filters: ``decision`` (all, undecided, accepted, rejected, flagged) and ``hide_duplicates``.
    The list is bounded by the session's ``max_recommendations`` (≤ 100), so it is not paginated.
    """
    if db.session.get(AnalysisSession, session_id) is None:
        raise ApiError("NOT_FOUND", "Analysis session not found.", 404)
    params = parse_query(RecommendationListQuery)
    all_recs = list(
        db.session.scalars(
            select(Recommendation)
            .where(Recommendation.session_id == session_id)
            .options(selectinload(Recommendation.mapping), selectinload(Recommendation.decided_by))
            .order_by(Recommendation.rank)
        )
    )
    decisions = Counter(
        rec.planner_decision.value if rec.planner_decision else "undecided" for rec in all_recs
    )
    shown = all_recs
    if params.decision == "undecided":
        shown = [r for r in shown if r.planner_decision is None]
    elif params.decision != "all":
        shown = [r for r in shown if r.planner_decision == params.decision]
    if params.hide_duplicates:
        shown = [r for r in shown if r.overlap_status != OverlapStatus.POTENTIAL_DUPLICATE]
    return success(
        {
            "items": [recommendation_json(rec) for rec in shown],
            "counts": {
                "total": len(all_recs),
                "reviewed": len(all_recs) - decisions["undecided"],
                "undecided": decisions["undecided"],
                "accepted": decisions["accepted"],
                "rejected": decisions["rejected"],
                "flagged": decisions["flagged"],
                "potential_duplicates": sum(
                    r.overlap_status == OverlapStatus.POTENTIAL_DUPLICATE for r in all_recs
                ),
            },
        }
    )


@bp.get("/recommendations/<int:recommendation_id>")
@login_required
def get_recommendation(recommendation_id: int) -> tuple[Response, int]:
    """Full detail: scores, evidence passages, the closest NUC passage and the mapping."""
    rec = get_recommendation_or_404(recommendation_id)
    session = db.session.get(AnalysisSession, rec.session_id)
    rows = db.session.execute(
        select(RecommendationEvidence, Passage, Document)
        .join(Passage, Passage.id == RecommendationEvidence.passage_id)
        .join(Document, Document.id == Passage.document_id)
        .where(RecommendationEvidence.recommendation_id == rec.id)
        .order_by(RecommendationEvidence.relevance_score.desc())
    ).all()
    evidence = [
        EvidenceOut(
            passage_id=passage.id,
            relevance_score=link.relevance_score,
            text=passage.text,
            page_number=passage.page_number,
            position=passage.position,
            document=DocumentRef.model_validate(document),
        ).model_dump(mode="json")
        for link, passage, document in rows
    ]

    closest = None
    if rec.closest_nuc_passage_id:
        passage = db.session.get(Passage, rec.closest_nuc_passage_id)
        if passage is not None:
            version = (
                db.session.get(NucCoreVersion, session.nuc_core_version_id)
                if session and session.nuc_core_version_id
                else None
            )
            closest = NucPassageOut(
                id=passage.id,
                text=passage.text,
                page_number=passage.page_number,
                document_title=passage.document.title,
                version_label=version.version_label if version else None,
            ).model_dump(mode="json")

    config = (session.parameter_config if session else None) or {}
    data = recommendation_json(rec)
    data.update(
        {
            "evidence": evidence,
            "closest_nuc_passage": closest,
            "session": SessionContext(
                id=rec.session_id,
                session_name=session.session_name if session else "",
                weights=config.get("weights", {}),
                similarity_threshold=float(config.get("similarity_threshold", 0.8)),
            ).model_dump(mode="json"),
            "mapping": (
                MappingOut.model_validate(rec.mapping).model_dump(mode="json")
                if rec.mapping
                else None
            ),
        }
    )
    return success(data)


@bp.patch("/recommendations/<int:recommendation_id>")
@role_required(*EDITOR_ROLES)
def edit_recommendation(recommendation_id: int) -> tuple[Response, int]:
    """Change the title and/or description (the machine title stays in ``auto_title``)."""
    rec = get_recommendation_or_404(recommendation_id)
    data = parse_body(RecommendationEdit)
    changes: dict[str, Any] = {}
    if data.topic_title is not None and data.topic_title != rec.topic_title:
        changes["topic_title"] = {"from": rec.topic_title, "to": data.topic_title}
        rec.topic_title = data.topic_title
    if data.topic_description is not None and data.topic_description != rec.topic_description:
        changes["topic_description"] = {"changed": True}
        rec.topic_description = data.topic_description
    if changes:
        record_audit(AuditAction.RECOMMENDATION_EDITED, "recommendation", rec.id, changes)
    db.session.commit()
    return success(recommendation_json(rec))


@bp.patch("/recommendations/<int:recommendation_id>/decision")
@role_required(*EDITOR_ROLES)
def decide(recommendation_id: int) -> tuple[Response, int]:
    """Accept, reject or flag a recommendation (``null`` clears the decision)."""
    rec = get_recommendation_or_404(recommendation_id)
    data = parse_body(DecisionIn)
    if rec.mapping is not None and data.decision != PlannerDecision.ACCEPTED:
        raise ApiError(
            "CONFLICT",
            "This recommendation is mapped to a course. Remove the course mapping before "
            "changing the decision.",
            409,
        )
    previous = rec.planner_decision.value if rec.planner_decision else None
    rec.planner_decision = data.decision
    rec.planner_notes = data.notes or None
    rec.decided_by_id = current_user.id if data.decision else None
    rec.decided_at = utcnow() if data.decision else None
    record_audit(
        AuditAction.RECOMMENDATION_DECIDED,
        "recommendation",
        rec.id,
        {
            "from": previous,
            "to": data.decision.value if data.decision else None,
            "title": rec.topic_title,
            "notes": bool(data.notes),
        },
    )
    db.session.commit()
    return success(recommendation_json(rec))
