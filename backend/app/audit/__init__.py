"""Audit logging.

Call :func:`record_audit` inside the same transaction as the change it describes, so the
audit entry is committed (or rolled back) together with it.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from flask import has_request_context, request
from flask_login import current_user

from app.extensions import db
from app.models.audit import AuditLog


class AuditAction(StrEnum):
    """Every audited action type. Stored in ``audit_logs.action_type``."""

    LOGIN = "auth.login"
    LOGIN_FAILED = "auth.login_failed"
    LOGOUT = "auth.logout"
    PASSWORD_CHANGED = "auth.password_changed"

    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_ROLE_CHANGED = "user.role_changed"
    USER_ACTIVATED = "user.activated"
    USER_DEACTIVATED = "user.deactivated"
    USER_PASSWORD_RESET = "user.password_reset"

    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_ARCHIVED = "document.archived"
    DOCUMENT_DELETED = "document.deleted"
    NUC_CORE_UPLOADED = "nuc_core.uploaded"

    SESSION_CREATED = "session.created"
    SESSION_RUN = "session.run"
    SESSION_DELETED = "session.deleted"

    RECOMMENDATION_DECIDED = "recommendation.decided"
    RECOMMENDATION_EDITED = "recommendation.edited"
    MAPPING_CREATED = "mapping.created"
    MAPPING_UPDATED = "mapping.updated"
    MAPPING_DELETED = "mapping.deleted"

    REPORT_GENERATED = "report.generated"
    REPORT_DELETED = "report.deleted"
    AUDIT_LOG_EXPORTED = "audit_log.exported"

    SETTINGS_UPDATED = "settings.updated"
    SKILL_PATTERN_CREATED = "skill_pattern.created"
    SKILL_PATTERN_UPDATED = "skill_pattern.updated"
    STOP_WORD_CREATED = "stop_word.created"
    STOP_WORD_UPDATED = "stop_word.updated"


def client_ip() -> str | None:
    """IP address of the current request (``X-Forwarded-For`` is applied by ProxyFix)."""
    return request.remote_addr if has_request_context() else None


def record_audit(
    action: AuditAction,
    entity_type: str | None = None,
    entity_id: int | str | None = None,
    detail: dict[str, Any] | None = None,
    user_id: int | None = None,
) -> AuditLog:
    """Add an audit entry to the current database session (the caller commits).

    ``user_id`` defaults to the logged-in user, if any.
    """
    if user_id is None and has_request_context() and current_user.is_authenticated:
        user_id = current_user.id
    entry = AuditLog(
        user_id=user_id,
        action_type=action.value,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        detail=detail or {},
        ip_address=client_ip(),
    )
    db.session.add(entry)
    return entry
