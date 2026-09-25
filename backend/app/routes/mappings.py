"""Curriculum mapping: turning accepted recommendations into proposed courses."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, Response
from flask_login import current_user
from sqlalchemy import select

from app.audit import AuditAction, record_audit
from app.auth.decorators import EDITOR_ROLES, login_required, role_required
from app.extensions import db
from app.models import AnalysisSession, CurriculumMap, PlannerDecision, Recommendation
from app.routes.recommendations import get_recommendation_or_404
from app.schemas.review import MappingIn, MappingOut, RecommendationRef
from app.settings import get_setting
from app.utils.errors import ApiError
from app.utils.responses import success
from app.utils.validation import parse_body

bp = Blueprint("mappings", __name__)


def mapping_json(mapping: CurriculumMap) -> dict[str, Any]:
    return MappingOut.model_validate(mapping).model_dump(mode="json")


def check_code_unique(session_id: int, course_code: str, exclude_id: int | None = None) -> None:
    """A course code can only be used once within a session's proposed curriculum."""
    query = (
        select(CurriculumMap.id)
        .join(Recommendation, Recommendation.id == CurriculumMap.recommendation_id)
        .where(Recommendation.session_id == session_id, CurriculumMap.course_code == course_code)
    )
    if exclude_id is not None:
        query = query.where(CurriculumMap.id != exclude_id)
    if db.session.scalar(query) is not None:
        raise ApiError(
            "CONFLICT",
            f"{course_code} is already used by another course in this session.",
            409,
            {"fields": {"course_code": [f"{course_code} is already used in this session."]}},
        )


def get_mapping_or_404(mapping_id: int) -> CurriculumMap:
    mapping = db.session.get(CurriculumMap, mapping_id)
    if mapping is None:
        raise ApiError("NOT_FOUND", "Course mapping not found.", 404)
    return mapping


def apply(mapping: CurriculumMap, data: MappingIn) -> dict[str, Any]:
    """Copy the form onto the mapping; returns the changed fields (for the audit log)."""
    changes: dict[str, Any] = {}
    for field in (
        "course_code",
        "course_title",
        "credit_units",
        "prerequisites",
        "learning_outcomes",
    ):
        value = getattr(data, field)
        if getattr(mapping, field) != value:
            changes[field] = value
            setattr(mapping, field, value)
    return changes


@bp.post("/recommendations/<int:recommendation_id>/mapping")
@role_required(*EDITOR_ROLES)
def create_mapping(recommendation_id: int) -> tuple[Response, int]:
    """Map an accepted recommendation to a proposed course (one course per recommendation)."""
    rec = get_recommendation_or_404(recommendation_id)
    if rec.planner_decision != PlannerDecision.ACCEPTED:
        raise ApiError("CONFLICT", "Only accepted recommendations can be mapped to a course.", 409)
    if rec.mapping is not None:
        raise ApiError(
            "CONFLICT", "This recommendation is already mapped; edit the existing course.", 409
        )
    data = parse_body(MappingIn)
    check_code_unique(rec.session_id, data.course_code)
    mapping = CurriculumMap(recommendation_id=rec.id, created_by_id=current_user.id)
    apply(mapping, data)
    db.session.add(mapping)
    db.session.flush()
    record_audit(
        AuditAction.MAPPING_CREATED,
        "curriculum_map",
        mapping.id,
        {
            "recommendation_id": rec.id,
            "course_code": mapping.course_code,
            "credit_units": mapping.credit_units,
        },
    )
    db.session.commit()
    return success(mapping_json(mapping), 201)


@bp.get("/recommendations/<int:recommendation_id>/mapping")
@login_required
def get_mapping_for(recommendation_id: int) -> tuple[Response, int]:
    rec = get_recommendation_or_404(recommendation_id)
    if rec.mapping is None:
        raise ApiError("NOT_FOUND", "This recommendation is not mapped to a course.", 404)
    return success(mapping_json(rec.mapping))


@bp.put("/mappings/<int:mapping_id>")
@role_required(*EDITOR_ROLES)
def update_mapping(mapping_id: int) -> tuple[Response, int]:
    """Replace the course details of a mapping."""
    mapping = get_mapping_or_404(mapping_id)
    data = parse_body(MappingIn)
    check_code_unique(mapping.recommendation.session_id, data.course_code, exclude_id=mapping.id)
    changes = apply(mapping, data)
    if changes:
        record_audit(
            AuditAction.MAPPING_UPDATED, "curriculum_map", mapping.id, {"changes": list(changes)}
        )
    db.session.commit()
    return success(mapping_json(mapping))


@bp.delete("/mappings/<int:mapping_id>")
@role_required(*EDITOR_ROLES)
def delete_mapping(mapping_id: int) -> tuple[Response, int]:
    mapping = get_mapping_or_404(mapping_id)
    record_audit(
        AuditAction.MAPPING_DELETED,
        "curriculum_map",
        mapping.id,
        {"recommendation_id": mapping.recommendation_id, "course_code": mapping.course_code},
    )
    db.session.delete(mapping)
    db.session.commit()
    return success({"deleted": True})


@bp.get("/sessions/<int:session_id>/curriculum")
@login_required
def proposed_curriculum(session_id: int) -> tuple[Response, int]:
    """Every proposed course of a session, the total credit units and the allowance."""
    session = db.session.get(AnalysisSession, session_id)
    if session is None:
        raise ApiError("NOT_FOUND", "Analysis session not found.", 404)
    rows = db.session.execute(
        select(CurriculumMap, Recommendation)
        .join(Recommendation, Recommendation.id == CurriculumMap.recommendation_id)
        .where(Recommendation.session_id == session_id)
        .order_by(CurriculumMap.course_code)
    ).all()
    total = sum(mapping.credit_units for mapping, _ in rows)
    allowance = get_setting("credit_unit_allowance")
    return success(
        {
            "session": {"id": session.id, "session_name": session.session_name},
            "courses": [
                {
                    **mapping_json(mapping),
                    "recommendation": RecommendationRef(
                        id=rec.id,
                        rank=rec.rank,
                        topic_title=rec.topic_title,
                        composite_score=rec.composite_score,
                        overlap_status=rec.overlap_status,
                    ).model_dump(mode="json"),
                }
                for mapping, rec in rows
            ],
            "total_units": total,
            "credit_unit_allowance": allowance,
            "remaining_units": (allowance - total) if isinstance(allowance, int | float) else None,
        }
    )
