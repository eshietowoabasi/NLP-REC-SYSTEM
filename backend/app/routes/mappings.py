"""Curriculum mapping (spec §4, §16): accepted recommendations -> proposed courses."""
from flask import Blueprint, jsonify, request
from sqlalchemy import select

from ..extensions import db
from ..models import CurriculumMap, PlannerDecision, Recommendation
from ..schemas.mapping import validate_mapping
from ..utils.audit import record_audit
from ..utils.errors import ConflictError, NotFoundError
from ..utils.rbac import WRITE_ROLES, login_required, roles_required
from .recommendations import ensure_can_review, get_recommendation_or_404
from .results import _completed_session

rec_bp = Blueprint("recommendation_mappings", __name__)
bp = Blueprint("mappings", __name__)
sessions_bp = Blueprint("session_mappings", __name__)


def _map_dict(mapping):
    rec = mapping.recommendation
    return {**mapping.to_dict(), "topic_title": rec.topic_title, "session_id": rec.session_id}


def _check_code_free(session_id, course_code, exclude_map_id=None):
    """A course code identifies one proposed course within a session."""
    query = (
        select(CurriculumMap.map_id)
        .join(Recommendation)
        .where(Recommendation.session_id == session_id, CurriculumMap.course_code == course_code)
    )
    if exclude_map_id:
        query = query.where(CurriculumMap.map_id != exclude_map_id)
    existing = db.session.execute(query).first()
    if existing:
        raise ConflictError(
            f"Course code {course_code} is already used in this session",
            code="COURSE_CODE_IN_USE",
            details={"map_id": existing.map_id},
        )


def get_mapping_or_404(map_id):
    mapping = db.session.get(CurriculumMap, map_id)
    if mapping is None:
        raise NotFoundError("Curriculum mapping not found")
    return mapping


@rec_bp.get("/<int:rec_id>/mapping")
@login_required
def list_for_recommendation(rec_id):
    rec = get_recommendation_or_404(rec_id)
    return jsonify({"success": True, "items": [_map_dict(m) for m in rec.curriculum_maps]})


@rec_bp.post("/<int:rec_id>/mapping")
@roles_required(*WRITE_ROLES)
def create_mapping(rec_id):
    rec = get_recommendation_or_404(rec_id)
    ensure_can_review(rec.session)
    if rec.planner_decision is not PlannerDecision.ACCEPTED:
        raise ConflictError("Only accepted recommendations can be mapped to a course", code="NOT_ACCEPTED")
    data = validate_mapping(request.get_json(silent=True))
    _check_code_free(rec.session_id, data["course_code"])
    mapping = CurriculumMap(rec_id=rec.rec_id, **data)
    db.session.add(mapping)
    db.session.flush()
    record_audit("MAPPING_CREATE", "CurriculumMap", mapping.map_id,
                 {"rec_id": rec.rec_id, "course_code": mapping.course_code}, commit=False)
    db.session.commit()
    return jsonify({"success": True, "mapping": _map_dict(mapping)}), 201


@bp.get("/<int:map_id>")
@login_required
def get_mapping(map_id):
    return jsonify({"success": True, "mapping": _map_dict(get_mapping_or_404(map_id))})


@bp.put("/<int:map_id>")
@roles_required(*WRITE_ROLES)
def update_mapping(map_id):
    mapping = get_mapping_or_404(map_id)
    ensure_can_review(mapping.recommendation.session)
    data = validate_mapping(request.get_json(silent=True))
    _check_code_free(mapping.recommendation.session_id, data["course_code"], exclude_map_id=map_id)
    for key, value in data.items():
        setattr(mapping, key, value)
    record_audit("MAPPING_UPDATE", "CurriculumMap", mapping.map_id, {"course_code": mapping.course_code}, commit=False)
    db.session.commit()
    return jsonify({"success": True, "mapping": _map_dict(mapping)})


@bp.delete("/<int:map_id>")
@roles_required(*WRITE_ROLES)
def delete_mapping(map_id):
    mapping = get_mapping_or_404(map_id)
    ensure_can_review(mapping.recommendation.session)
    record_audit("MAPPING_DELETE", "CurriculumMap", mapping.map_id,
                 {"rec_id": mapping.rec_id, "course_code": mapping.course_code}, commit=False)
    db.session.delete(mapping)
    db.session.commit()
    return jsonify({"success": True})


@sessions_bp.get("/<int:session_id>/mappings")
@login_required
def list_for_session(session_id):
    _completed_session(session_id)
    mappings = db.session.execute(
        select(CurriculumMap)
        .join(Recommendation)
        .where(Recommendation.session_id == session_id)
        .order_by(CurriculumMap.course_code)
    ).scalars().all()
    return jsonify({"success": True, "session_id": session_id, "items": [_map_dict(m) for m in mappings]})
