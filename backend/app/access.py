"""Who may see which programme's data.

Admins see every programme. Planners and viewers see only the programmes an admin assigned to
them (``programme_members``); what they may *do* there is still decided by their role
(``@role_required``). General documents, which belong to no programme, are visible to
everyone.

Anything outside a user's programmes answers 404, as if it did not exist, so the API does not
reveal other departments' work. Sessions created before programmes existed have no
``programme_id`` and count as the default programme's.
"""

from __future__ import annotations

from flask_login import current_user
from sqlalchemy import ColumnElement, false, or_, select, true

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


def session_condition() -> ColumnElement[bool]:
    """WHERE clause keeping sessions of the user's programmes (legacy ones: the default's)."""
    scope = programme_scope()
    if scope is None:
        return true()
    if not scope:
        return false()
    condition = AnalysisSession.programme_id.in_(scope)
    default_id = _default_programme_id()
    if default_id in scope:
        condition = or_(condition, AnalysisSession.programme_id.is_(None))
    return condition


def session_programme_id(session: AnalysisSession) -> int | None:
    """The session's programme, counting a legacy session (no programme) as the default's."""
    return session.programme_id if session.programme_id is not None else _default_programme_id()


def get_visible_session(session_id: int) -> AnalysisSession:
    """The analysis session, or 404 if it does not exist or is outside the user's programmes."""
    session = db.session.get(AnalysisSession, session_id)
    if session is None or not can_see_programme(session_programme_id(session)):
        raise ApiError("NOT_FOUND", "Analysis session not found.", 404)
    return session


def can_see_session(session_id: int) -> bool:
    """True if the session exists and belongs to one of the user's programmes."""
    session = db.session.get(AnalysisSession, session_id)
    return session is not None and can_see_programme(session_programme_id(session))


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
    "programme_scope",
    "require_programme",
    "session_condition",
    "session_programme_id",
    "visible_documents",
]
