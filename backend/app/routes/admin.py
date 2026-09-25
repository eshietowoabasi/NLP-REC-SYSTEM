"""Admin endpoints. Every route requires the ``admin`` role.

Users, system settings, skill patterns, domain stop words and the audit log (with CSV export).
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterator
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import sqlalchemy as sa
from flask import Blueprint, Response
from flask_login import current_user
from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import selectinload

from app.audit import AuditAction, record_audit
from app.auth.accounts import create_user, update_user
from app.auth.decorators import role_required
from app.extensions import db
from app.models.audit import AuditLog
from app.models.configuration import Setting, SkillPattern, StopWord
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.admin import (
    AuditLogOut,
    AuditLogQuery,
    SettingOut,
    SettingsUpdate,
    SkillPatternIn,
    SkillPatternListQuery,
    SkillPatternOut,
    SkillPatternUpdate,
    StopWordIn,
    StopWordListQuery,
    StopWordOut,
    StopWordUpdate,
    check_pattern,
)
from app.schemas.documents import UserRef
from app.schemas.users import UserCreate, UserListQuery, UserOut, UserUpdate
from app.settings import SETTING_DEFINITIONS
from app.utils.errors import ApiError
from app.utils.responses import success
from app.utils.time import utcnow
from app.utils.validation import paginate, parse_body, parse_query

bp = Blueprint("admin", __name__, url_prefix="/admin")

MAX_EXPORT_ROWS = 100_000


def _user_json(user: User) -> dict:
    return UserOut.model_validate(user).model_dump(mode="json")


@bp.get("/users")
@role_required(UserRole.ADMIN)
def list_users() -> tuple[Response, int]:
    """List users. Filters: ``role``, ``is_active`` (true/false), ``search``."""
    params = parse_query(UserListQuery)
    query = select(User).order_by(User.created_at.desc(), User.id.desc())
    if params.role is not None:
        query = query.where(User.role == params.role)
    if params.is_active is not None:
        query = query.where(User.is_active.is_(params.is_active == "true"))
    if params.search:
        pattern = f"%{params.search}%"
        query = query.where(
            or_(
                User.username.ilike(pattern),
                User.email.ilike(pattern),
                User.full_name.ilike(pattern),
            )
        )
    users, meta = paginate(query, params.page, params.per_page)
    return success({"items": [_user_json(user) for user in users], "pagination": meta})


@bp.post("/users")
@role_required(UserRole.ADMIN)
def add_user() -> tuple[Response, int]:
    """Create a user with an initial password."""
    user = create_user(parse_body(UserCreate))
    db.session.commit()
    return success(_user_json(user), 201)


@bp.patch("/users/<int:user_id>")
@role_required(UserRole.ADMIN)
def edit_user(user_id: int) -> tuple[Response, int]:
    """Change a user's name, email, role or active flag, or reset their password."""
    user = db.session.get(User, user_id)
    if user is None:
        raise ApiError("NOT_FOUND", "User not found.", 404)
    data = parse_body(UserUpdate)
    update_user(current_user._get_current_object(), user, data)
    db.session.commit()
    return success(_user_json(user))


# ------------------------------------------------------------------------------ settings


def _settings_json() -> list[dict[str, Any]]:
    rows = {row.key: row for row in db.session.scalars(select(Setting))}
    user_ids = {row.updated_by_id for row in rows.values() if row.updated_by_id}
    users = (
        {u.id: u for u in db.session.scalars(select(User).where(User.id.in_(user_ids)))}
        if user_ids
        else {}
    )
    result = []
    for definition in SETTING_DEFINITIONS:
        row = rows.get(definition.key)
        editor = users.get(row.updated_by_id) if row and row.updated_by_id else None
        result.append(
            SettingOut(
                key=definition.key,
                value=row.value if row else definition.default,
                default=definition.default,
                description=definition.description,
                updated_at=row.updated_at if row else None,
                updated_by=UserRef.model_validate(editor) if editor else None,
            ).model_dump(mode="json")
        )
    return result


@bp.get("/settings")
@role_required(UserRole.ADMIN)
def get_settings() -> tuple[Response, int]:
    """Every setting with its current value, default and description."""
    return success({"settings": _settings_json()})


@bp.put("/settings")
@role_required(UserRole.ADMIN)
def update_settings() -> tuple[Response, int]:
    """Change any subset of the settings. New values apply to sessions created afterwards
    (passage size and embedding model: to documents uploaded afterwards)."""
    data = parse_body(SettingsUpdate)
    changed: dict[str, Any] = {}
    for key, value in data.changes().items():
        row = db.session.get(Setting, key)
        previous = (
            row.value if row else next(d.default for d in SETTING_DEFINITIONS if d.key == key)
        )
        if previous == value:
            continue
        if row is None:
            row = Setting(key=key)
            db.session.add(row)
        row.value = value
        row.updated_by_id = current_user.id
        row.updated_at = utcnow()
        changed[key] = {"from": previous, "to": value}
    if changed:
        record_audit(AuditAction.SETTINGS_UPDATED, "setting", ",".join(changed)[:64], changed)
    db.session.commit()
    return success({"settings": _settings_json(), "changed": sorted(changed)})


# ------------------------------------------------------------------------ skill patterns


def _pattern_text() -> sa.ColumnElement[str]:
    """The pattern as text: the phrase itself, or the JSON of a token pattern."""
    return SkillPattern.pattern.op("#>>", return_type=sa.Text)(sa.literal_column("'{}'::text[]"))


def _check_pattern_unique(label: str, pattern: Any, exclude_id: int | None = None) -> None:
    if isinstance(pattern, str):
        same = sa.and_(
            sa.func.jsonb_typeof(SkillPattern.pattern) == "string",
            sa.func.lower(_pattern_text()) == pattern.lower(),
        )
    else:
        same = SkillPattern.pattern == sa.cast(json.dumps(pattern), JSONB)
    query = select(SkillPattern.id).where(SkillPattern.label == label, same)
    if exclude_id is not None:
        query = query.where(SkillPattern.id != exclude_id)
    if db.session.scalar(query) is not None:
        raise ApiError(
            "CONFLICT",
            "This pattern already exists for that label.",
            409,
            {"fields": {"pattern": ["This pattern already exists for that label."]}},
        )


def _pattern_json(pattern: SkillPattern) -> dict[str, Any]:
    return SkillPatternOut.model_validate(pattern).model_dump(mode="json")


def _get_pattern_or_404(pattern_id: int) -> SkillPattern:
    pattern = db.session.get(SkillPattern, pattern_id)
    if pattern is None:
        raise ApiError("NOT_FOUND", "Skill pattern not found.", 404)
    return pattern


@bp.get("/skill-patterns")
@role_required(UserRole.ADMIN)
def list_skill_patterns() -> tuple[Response, int]:
    """Skill patterns by canonical name. Filters: ``label``, ``is_active``, ``search``."""
    params = parse_query(SkillPatternListQuery)
    query = select(SkillPattern).order_by(
        sa.func.lower(SkillPattern.canonical_name), SkillPattern.id
    )
    if params.label is not None:
        query = query.where(SkillPattern.label == params.label)
    if params.is_active is not None:
        query = query.where(SkillPattern.is_active.is_(params.is_active))
    if params.search:
        like = f"%{params.search}%"
        query = query.where(
            or_(SkillPattern.canonical_name.ilike(like), _pattern_text().ilike(like))
        )
    patterns, meta = paginate(query, params.page, params.per_page)
    return success({"items": [_pattern_json(p) for p in patterns], "pagination": meta})


@bp.post("/skill-patterns")
@role_required(UserRole.ADMIN)
def create_skill_pattern() -> tuple[Response, int]:
    """Add a pattern; it is used by sessions run afterwards."""
    data = parse_body(SkillPatternIn)
    _check_pattern_unique(str(data.label), data.pattern)
    pattern = SkillPattern(
        label=data.label, pattern=data.pattern, canonical_name=data.canonical_name
    )
    db.session.add(pattern)
    db.session.flush()
    record_audit(
        AuditAction.SKILL_PATTERN_CREATED,
        "skill_pattern",
        pattern.id,
        {"label": str(data.label), "pattern": data.pattern, "canonical_name": data.canonical_name},
    )
    db.session.commit()
    return success(_pattern_json(pattern), 201)


@bp.patch("/skill-patterns/<int:pattern_id>")
@role_required(UserRole.ADMIN)
def update_skill_pattern(pattern_id: int) -> tuple[Response, int]:
    """Edit a pattern or (de)activate it."""
    pattern = _get_pattern_or_404(pattern_id)
    data = parse_body(SkillPatternUpdate)
    label = str(data.label or pattern.label)
    new_pattern = data.pattern if data.pattern is not None else pattern.pattern
    if data.label is not None or data.pattern is not None:
        try:
            check_pattern(label, new_pattern)
        except ValueError as exc:
            raise ApiError(
                "VALIDATION_ERROR", str(exc), 422, {"fields": {"pattern": [str(exc)]}}
            ) from exc
        _check_pattern_unique(label, new_pattern, exclude_id=pattern.id)
    changes: dict[str, Any] = {}
    for field in ("label", "pattern", "canonical_name", "is_active"):
        value = getattr(data, field)
        if value is not None and value != getattr(pattern, field):
            changes[field] = {"from": _plain(getattr(pattern, field)), "to": _plain(value)}
            setattr(pattern, field, value)
    if changes:
        record_audit(AuditAction.SKILL_PATTERN_UPDATED, "skill_pattern", pattern.id, changes)
    db.session.commit()
    return success(_pattern_json(pattern))


def _plain(value: Any) -> Any:
    """Enum values as plain strings for the audit detail."""
    return getattr(value, "value", value)


# ---------------------------------------------------------------------------- stop words


def _get_stop_word_or_404(word_id: int) -> StopWord:
    word = db.session.get(StopWord, word_id)
    if word is None:
        raise ApiError("NOT_FOUND", "Stop word not found.", 404)
    return word


@bp.get("/stop-words")
@role_required(UserRole.ADMIN)
def list_stop_words() -> tuple[Response, int]:
    """Domain stop words, alphabetically. Filters: ``is_active``, ``search``."""
    params = parse_query(StopWordListQuery)
    query = select(StopWord).order_by(StopWord.word)
    if params.is_active is not None:
        query = query.where(StopWord.is_active.is_(params.is_active))
    if params.search:
        query = query.where(StopWord.word.ilike(f"%{params.search.lower()}%"))
    words, meta = paginate(query, params.page, params.per_page)
    return success(
        {
            "items": [StopWordOut.model_validate(w).model_dump(mode="json") for w in words],
            "pagination": meta,
        }
    )


@bp.post("/stop-words")
@role_required(UserRole.ADMIN)
def create_stop_word() -> tuple[Response, int]:
    """Add a stop word; sessions run afterwards leave it out of keywords and theme words."""
    data = parse_body(StopWordIn)
    if db.session.scalar(select(StopWord.id).where(StopWord.word == data.word)) is not None:
        raise ApiError(
            "CONFLICT",
            f"'{data.word}' is already a stop word.",
            409,
            {"fields": {"word": [f"'{data.word}' is already a stop word."]}},
        )
    word = StopWord(word=data.word)
    db.session.add(word)
    db.session.flush()
    record_audit(AuditAction.STOP_WORD_CREATED, "stop_word", word.id, {"word": word.word})
    db.session.commit()
    return success(StopWordOut.model_validate(word).model_dump(mode="json"), 201)


@bp.patch("/stop-words/<int:word_id>")
@role_required(UserRole.ADMIN)
def update_stop_word(word_id: int) -> tuple[Response, int]:
    """Activate or deactivate a stop word."""
    word = _get_stop_word_or_404(word_id)
    data = parse_body(StopWordUpdate)
    if word.is_active != data.is_active:
        word.is_active = data.is_active
        record_audit(
            AuditAction.STOP_WORD_UPDATED,
            "stop_word",
            word.id,
            {"word": word.word, "is_active": data.is_active},
        )
    db.session.commit()
    return success(StopWordOut.model_validate(word).model_dump(mode="json"))


# ----------------------------------------------------------------------------- audit log


def _audit_query(params: AuditLogQuery) -> sa.Select[tuple[AuditLog]]:
    query = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    if params.user_id is not None:
        query = query.where(AuditLog.user_id == params.user_id)
    if params.action:
        # "auth" selects a whole area (auth.login, auth.logout, ...); "auth.login" one action.
        if "." in params.action:
            query = query.where(AuditLog.action_type == params.action)
        else:
            query = query.where(AuditLog.action_type.like(f"{params.action}.%"))
    if params.entity_type:
        query = query.where(AuditLog.entity_type == params.entity_type)
    if params.date_from:
        query = query.where(AuditLog.created_at >= _utc_midnight(params.date_from))
    if params.date_to:
        query = query.where(AuditLog.created_at < _utc_midnight(params.date_to) + timedelta(days=1))
    return query


def _utc_midnight(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=UTC)


def _audit_json(entry: AuditLog) -> dict[str, Any]:
    return AuditLogOut(
        id=entry.id,
        created_at=entry.created_at,
        user=UserRef.model_validate(entry.user) if entry.user else None,
        action_type=entry.action_type,
        entity_type=entry.entity_type,
        entity_id=entry.entity_id,
        detail=entry.detail or {},
        ip_address=entry.ip_address,
    ).model_dump(mode="json")


@bp.get("/audit-logs")
@role_required(UserRole.ADMIN)
def list_audit_logs() -> tuple[Response, int]:
    """The audit trail, newest first. Filters: ``user_id``, ``action`` (an action such as
    ``auth.login`` or an area such as ``auth``), ``entity_type``, ``date_from``, ``date_to``."""
    params = parse_query(AuditLogQuery)
    entries, meta = paginate(
        _audit_query(params).options(selectinload(AuditLog.user)), params.page, params.per_page
    )
    return success(
        {
            "items": [_audit_json(e) for e in entries],
            "pagination": meta,
            "actions": [action.value for action in AuditAction],
        }
    )


def _csv_cell(value: Any) -> str:
    """Stringify, neutralising spreadsheet formulas (CSV injection)."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


@bp.get("/audit-logs/export")
@role_required(UserRole.ADMIN)
def export_audit_logs() -> Response:
    """The filtered audit trail as CSV (at most 100,000 rows, newest first)."""
    params = parse_query(AuditLogQuery)
    record_audit(
        AuditAction.AUDIT_LOG_EXPORTED,
        "audit_log",
        None,
        params.model_dump(mode="json", exclude={"page", "per_page"}, exclude_none=True),
    )
    db.session.commit()
    query = _audit_query(params).options(selectinload(AuditLog.user)).limit(MAX_EXPORT_ROWS)

    def rows() -> Iterator[str]:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            ["time_utc", "user", "username", "action", "entity_type", "entity_id", "detail", "ip"]
        )
        for entry in db.session.scalars(query.execution_options(yield_per=1000)):
            writer.writerow(
                [
                    entry.created_at.isoformat(),
                    _csv_cell(entry.user.full_name if entry.user else ""),
                    _csv_cell(entry.user.username if entry.user else ""),
                    entry.action_type,
                    _csv_cell(entry.entity_type),
                    _csv_cell(entry.entity_id),
                    _csv_cell(json.dumps(entry.detail or {}, ensure_ascii=False, sort_keys=True)),
                    _csv_cell(entry.ip_address),
                ]
            )
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate()

    filename = f"nlp-rs-audit-log-{utcnow():%Y%m%d-%H%M}.csv"
    return Response(
        "﻿" + "".join(rows()),  # BOM so Excel opens the UTF-8 file correctly
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
