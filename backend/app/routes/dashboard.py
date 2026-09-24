"""Overview for the dashboard page (spec §13 /dashboard)."""
from flask import Blueprint, jsonify
from flask_login import current_user
from sqlalchemy import func, select

from ..extensions import db
from ..models import AnalysisSession, Document, Recommendation, SessionStatus, SourceCategory
from ..services.analysis import core_reference_available
from ..utils.rbac import login_required

bp = Blueprint("dashboard", __name__)


@bp.get("/summary")
@login_required
def summary():
    by_category = dict(db.session.execute(
        select(Document.source_category, func.count()).group_by(Document.source_category)
    ).all())
    by_status = dict(db.session.execute(
        select(AnalysisSession.status, func.count()).group_by(AnalysisSession.status)
    ).all())
    pending_reviews = db.session.execute(
        select(func.count())
        .select_from(Recommendation)
        .join(AnalysisSession)
        .where(Recommendation.planner_decision.is_(None), AnalysisSession.user_id == current_user.user_id)
    ).scalar_one()
    recent = db.session.execute(
        select(AnalysisSession).order_by(AnalysisSession.created_at.desc(), AnalysisSession.session_id.desc()).limit(5)
    ).scalars().all()
    return jsonify({
        "success": True,
        "documents": {
            "total": sum(by_category.values()),
            "by_category": {c.value: by_category.get(c, 0) for c in SourceCategory},
        },
        "sessions": {
            "total": sum(by_status.values()),
            "by_status": {s.value: by_status.get(s, 0) for s in SessionStatus},
        },
        "my_pending_reviews": pending_reviews,
        "core_reference_available": core_reference_available(),
        "recent_sessions": [s.to_dict() for s in recent],
    })
