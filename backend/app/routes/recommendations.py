"""Ranked recommendations, overlap results and planner decisions (spec §10, §11.2, §13.1)."""
from flask import Blueprint, jsonify, request
from flask_login import current_user
from sqlalchemy import select
from sqlalchemy.orm import undefer

from ..extensions import db
from ..models import OverlapStatus, PlannerDecision, Recommendation, Role
from ..utils.audit import record_audit
from ..utils.errors import ApiError, ConflictError, NotFoundError, ValidationError
from ..utils.params import parse_enum
from ..utils.rbac import WRITE_ROLES, login_required, roles_required
from .results import _completed_session

sessions_bp = Blueprint("session_recommendations", __name__)
bp = Blueprint("recommendations", __name__)

MAX_NOTES_LENGTH = 2000


def ensure_can_review(session):
    """Reviewing (decisions, renames, mappings) is for the session owner or an Admin."""
    if current_user.role is not Role.ADMIN and session.user_id != current_user.user_id:
        raise ApiError("Only the session owner or an Admin can review its recommendations",
                       code="FORBIDDEN", status_code=403)


def get_recommendation_or_404(rec_id, with_evidence=False):
    options = [undefer(Recommendation.evidence)] if with_evidence else []
    rec = db.session.get(Recommendation, rec_id, options=options)
    if rec is None:
        raise NotFoundError("Recommendation not found")
    return rec


@sessions_bp.get("/<int:session_id>/recommendations")
@login_required
def list_recommendations(session_id):
    _completed_session(session_id)
    query = select(Recommendation).where(Recommendation.session_id == session_id).order_by(Recommendation.rank)
    if status := request.args.get("overlap_status"):
        query = query.where(Recommendation.overlap_status == parse_enum(OverlapStatus, status, "overlap_status"))
    if decision := request.args.get("decision"):
        if decision == "pending":
            query = query.where(Recommendation.planner_decision.is_(None))
        else:
            query = query.where(Recommendation.planner_decision == parse_enum(PlannerDecision, decision, "decision"))
    if request.args.get("include_evidence") in ("1", "true"):
        query = query.options(undefer(Recommendation.evidence))
        items = [r.to_dict(include_evidence=True) for r in db.session.execute(query).scalars()]
    else:
        items = [r.to_dict() for r in db.session.execute(query).scalars()]
    return jsonify({"success": True, "session_id": session_id, "items": items})


@sessions_bp.get("/<int:session_id>/similarity")
@login_required
def similarity(session_id):
    """Overlap results: each recommendation's closest NUC core segments (spec §9)."""
    session = _completed_session(session_id)
    recs = db.session.execute(
        select(Recommendation)
        .where(Recommendation.session_id == session_id)
        .order_by(Recommendation.rank)
        .options(undefer(Recommendation.evidence))
    ).scalars().all()
    info = session.pipeline_info or {}
    return jsonify({
        "success": True,
        "session_id": session_id,
        "similarity_threshold": session.parameter_config["similarity_threshold"],
        "core_document_ids": info.get("core_document_ids", []),
        "core_segment_count": info.get("core_segment_count"),
        "items": [
            {
                "rec_id": r.rec_id,
                "topic_title": r.topic_title,
                "max_similarity": r.max_similarity,
                "novelty_score": r.novelty_score,
                "overlap_status": r.overlap_status.value,
                "core_matches": (r.evidence or {}).get("core_matches", []),
            }
            for r in recs
        ],
    })


@bp.get("/<int:rec_id>")
@login_required
def get_recommendation(rec_id):
    rec = get_recommendation_or_404(rec_id, with_evidence=True)
    return jsonify({"success": True, "recommendation": rec.to_dict(include_evidence=True)})


@bp.patch("/<int:rec_id>/decision")
@roles_required(*WRITE_ROLES)
def decide(rec_id):
    """Accept, reject or flag a recommendation, or send null to clear the decision."""
    rec = get_recommendation_or_404(rec_id)
    ensure_can_review(rec.session)

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or "decision" not in payload:
        raise ValidationError("decision is required", details={"decision": "Accepted, Rejected, Flagged or null"})
    decision = None if payload["decision"] is None else parse_enum(PlannerDecision, payload["decision"], "decision")

    notes = payload.get("notes", rec.planner_notes)
    if notes is not None:
        if not isinstance(notes, str):
            raise ValidationError("notes must be a string", details={"notes": "Must be a string"})
        notes = notes.strip()[:MAX_NOTES_LENGTH] or None

    # Spec §9: a potential duplicate of the 70% core needs an explicit justification.
    if decision is PlannerDecision.ACCEPTED and rec.overlap_status is OverlapStatus.POTENTIAL_DUPLICATE and not notes:
        raise ValidationError(
            "Accepting a potential duplicate of the NUC core requires planner notes explaining why",
            code="JUSTIFICATION_REQUIRED",
            details={"notes": "Required when accepting a Potential Duplicate"},
        )

    if rec.curriculum_maps and decision is not PlannerDecision.ACCEPTED:
        raise ConflictError(
            "This recommendation is mapped to a course; delete the mapping before changing the decision",
            code="MAPPING_EXISTS",
            details={"map_ids": [m.map_id for m in rec.curriculum_maps]},
        )

    previous = rec.planner_decision.value if rec.planner_decision else None
    rec.planner_decision = decision
    rec.planner_notes = notes
    record_audit("RECOMMENDATION_DECISION", "Recommendation", rec.rec_id,
                 {"from": previous, "to": decision.value if decision else None, "session_id": rec.session_id},
                 commit=False)
    db.session.commit()
    return jsonify({"success": True, "recommendation": rec.to_dict()})


@bp.patch("/<int:rec_id>")
@roles_required(*WRITE_ROLES)
def update_recommendation(rec_id):
    """Rename a recommendation or edit its description (docs/DECISIONS.md, D5)."""
    rec = get_recommendation_or_404(rec_id)
    ensure_can_review(rec.session)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not {"topic_title", "topic_description"} & set(payload):
        raise ValidationError("Provide topic_title and/or topic_description")
    changes = {}
    if "topic_title" in payload:
        title = payload["topic_title"]
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > 255:
            raise ValidationError("Invalid topic_title", details={"topic_title": "1-255 characters"})
        changes["topic_title"] = (rec.topic_title, title.strip())
        rec.topic_title = title.strip()
    if "topic_description" in payload:
        description = payload["topic_description"]
        if description is not None and (not isinstance(description, str) or len(description) > 5000):
            raise ValidationError("Invalid topic_description", details={"topic_description": "Up to 5000 characters"})
        changes["topic_description"] = "updated"
        rec.topic_description = description.strip() if description else None
    record_audit("RECOMMENDATION_EDIT", "Recommendation", rec.rec_id,
                 {k: (list(v) if isinstance(v, tuple) else v) for k, v in changes.items()}, commit=False)
    db.session.commit()
    return jsonify({"success": True, "recommendation": rec.to_dict()})
