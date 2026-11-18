"""Who may see which programme's data.

Admins see every programme. Planners and viewers see only the programmes an admin assigned to
them (``programme_members``); what they may *do* there is still decided by their role
(``@role_required``). General documents, which belong to no programme, are visible to
everyone.

Reviews (analysis sessions) are personal: a planner sees only the reviews they started, so ten
planners in one programme never see or change each other's work. Viewers (read-only) see every
review in their programmes, and admins see everything.

Anything outside a user's programmes answers 404, as if it did not exist, so the API does not
reveal other departments' work. Sessions created before programmes existed have no
``programme_id`` and count as the default programme's.
"""

from __future__ import annotations

from flask_login import current_user
from sqlalchemy import ColumnElement, and_, false, or_, select, true

from app.extensions import db
from app.models import AnalysisSession, Document, Programme, UserRole
from app.utils.errors import ApiError


def programme_scope() -> set[int] | None:
    """Ids of the programmes the signed-in user may see, or None for all (admins)."""
    if current_user.role == UserRole.ADMIN:
        return None
    return {programme.id for programme in current_user.programmes}


def _default_programme_id() -> int | None:
    return db.session.scalar(
        select(Programme.id).where(Programme.is_active.is_(True)).order_by(Programme.id).limit(1)
    )


def can_see_programme(programme_id: int | None) -> bool:
    """True if the user may see this programme's data (None: general, visible to all)."""
    scope = programme_scope()
    return scope is None or programme_id is None or programme_id in scope


def require_programme(programme_id: int, message: str = "Programme not found.") -> None:
    """404 unless the user may see this programme."""
    if not can_see_programme(programme_id):
        raise ApiError("NOT_FOUND", message, 404)


def programme_condition() -> ColumnElement[bool]:
    """WHERE clause keeping the programmes the user may see."""
    scope = programme_scope()
    if scope is None:
        return true()
    return Programme.id.in_(scope) if scope else false()


def document_condition() -> ColumnElement[bool]:
    """WHERE clause keeping documents of the user's programmes and general documents."""
    scope = programme_scope()
    if scope is None:
        return true()
    general = Document.programme_id.is_(None)
    return or_(general, Document.programme_id.in_(scope)) if scope else general


def own_reviews_only() -> bool:
    """True when the user sees only the reviews they started (planners)."""
    return current_user.role == UserRole.PLANNER


def session_condition() -> ColumnElement[bool]:
    """WHERE clause keeping the sessions the user may see: in their programmes (legacy ones
    count as the default's) and, for planners, started by them."""
    scope = programme_scope()
    if scope is None:
        return true()
    if not scope:
        return false()
    condition = AnalysisSession.programme_id.in_(scope)
    default_id = _default_programme_id()
    if default_id in scope:
        condition = or_(condition, AnalysisSession.programme_id.is_(None))
    if own_reviews_only():
        condition = and_(condition, AnalysisSession.created_by_id == current_user.id)
    return condition


def in_programme_condition(programme_id: int) -> ColumnElement[bool]:
    """WHERE clause keeping one programme's sessions (legacy ones when it is the default)."""
    condition = AnalysisSession.programme_id == programme_id
    if programme_id == _default_programme_id():
        condition = or_(condition, AnalysisSession.programme_id.is_(None))
    return condition


def session_programme_id(session: AnalysisSession) -> int | None:
    """The session's programme, counting a legacy session (no programme) as the default's."""
    return session.programme_id if session.programme_id is not None else _default_programme_id()


def _may_see(session: AnalysisSession) -> bool:
    if not can_see_programme(session_programme_id(session)):
        return False
    return not own_reviews_only() or session.created_by_id == current_user.id


def get_visible_session(session_id: int) -> AnalysisSession:
    """The analysis session, or 404 if it does not exist, is outside the user's programmes or,
    for a planner, was started by someone else."""
    session = db.session.get(AnalysisSession, session_id)
    if session is None or not _may_see(session):
        raise ApiError("NOT_FOUND", "Analysis session not found.", 404)
    return session


def can_see_session(session_id: int) -> bool:
    """True if the session exists and the user may see it (see :func:`get_visible_session`)."""
    session = db.session.get(AnalysisSession, session_id)
    return session is not None and _may_see(session)


def get_visible_document(document_id: int) -> Document:
    """The document, or 404 if it does not exist or belongs to a programme the user cannot see."""
    document = db.session.get(Document, document_id)
    if document is None or not can_see_programme(document.programme_id):
        raise ApiError("NOT_FOUND", "Document not found.", 404)
    return document


def visible_documents(document_ids: list[int]) -> set[int]:
    """The subset of ``document_ids`` the user may see."""
    if not document_ids:
        return set()
    return set(
        db.session.scalars(
            select(Document.id).where(Document.id.in_(document_ids), document_condition())
        )
    )


__all__ = [
    "can_see_programme",
    "can_see_session",
    "document_condition",
    "get_visible_document",
    "get_visible_session",
    "programme_condition",
    "in_programme_condition",
    "own_reviews_only",
    "programme_scope",
    "require_programme",
    "session_condition",
    "session_programme_id",
    "visible_documents",
]
