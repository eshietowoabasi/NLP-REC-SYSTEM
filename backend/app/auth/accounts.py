"""Account rules: authentication, password changes and admin user management.

Functions here add audit entries to the current transaction but do not commit; the calling
route commits once, so a change and its audit entry are saved together.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select

from app.audit import AuditAction, record_audit
from app.auth.passwords import hash_password, verify_password
from app.extensions import db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.users import UserCreate, UserUpdate
from app.utils.errors import ApiError
from app.utils.time import utcnow

INVALID_CREDENTIALS = "Invalid username/email or password."


def find_by_identifier(identifier: str) -> User | None:
    """Look a user up by username or email (case-insensitive)."""
    needle = identifier.strip().lower()
    return db.session.scalar(
        select(User).where(
            or_(func.lower(User.username) == needle, func.lower(User.email) == needle)
        )
    )


def authenticate(identifier: str, password: str) -> User:
    """Return the user for valid credentials, otherwise raise.

    Unknown users and wrong passwords get the same message (no account enumeration). A
    deactivated account is only reported as such after a correct password. Failed attempts
    are audited and committed immediately, because the request itself will fail.
    """
    user = find_by_identifier(identifier)
    # verify_password runs first even for unknown users, so timing is the same either way.
    if not verify_password(password, user.password_hash if user else None) or user is None:
        record_audit(
            AuditAction.LOGIN_FAILED,
            "user",
            user.id if user else None,
            {"identifier": identifier[:255], "reason": "invalid_credentials"},
            user_id=user.id if user else None,
        )
        db.session.commit()
        raise ApiError("INVALID_CREDENTIALS", INVALID_CREDENTIALS, 401)
    if not user.is_active:
        record_audit(
            AuditAction.LOGIN_FAILED,
            "user",
            user.id,
            {"identifier": identifier[:255], "reason": "account_deactivated"},
            user_id=user.id,
        )
        db.session.commit()
        raise ApiError(
            "ACCOUNT_DEACTIVATED",
            "This account has been deactivated. Contact an administrator.",
            403,
        )
    user.last_login_at = utcnow()
    record_audit(AuditAction.LOGIN, "user", user.id, user_id=user.id)
    return user


def change_own_password(user: User, current_password: str, new_password: str) -> None:
    """Change ``user``'s password after checking the current one; ends their other sessions."""
    if not verify_password(current_password, user.password_hash):
        raise ApiError(
            "VALIDATION_ERROR",
            "Some fields are invalid.",
            422,
            {"fields": {"current_password": ["Current password is incorrect."]}},
        )
    user.password_hash = hash_password(new_password)
    user.rotate_session_token()
    record_audit(AuditAction.PASSWORD_CHANGED, "user", user.id)


def _ensure_unique(username: str | None, email: str | None, exclude_id: int | None = None) -> None:
    conflicts: dict[str, list[str]] = {}
    checks = (("username", User.username, username), ("email", User.email, email))
    for field, column, value in checks:
        if value is None:
            continue
        query = select(User.id).where(func.lower(column) == value.lower())
        if exclude_id is not None:
            query = query.where(User.id != exclude_id)
        if db.session.scalar(query) is not None:
            conflicts[field] = [f"This {field} is already in use."]
    if conflicts:
        raise ApiError(
            "CONFLICT", "A user with these details already exists.", 409, {"fields": conflicts}
        )


def create_user(data: UserCreate) -> User:
    """Create a user (admin action)."""
    _ensure_unique(data.username, data.email)
    user = User(
        username=data.username,
        email=data.email,
        full_name=data.full_name,
        role=data.role,
        password_hash=hash_password(data.password),
    )
    db.session.add(user)
    db.session.flush()
    record_audit(
        AuditAction.USER_CREATED,
        "user",
        user.id,
        {"username": user.username, "role": user.role.value},
    )
    return user


def update_user(actor: User, user: User, data: UserUpdate) -> User:
    """Apply an admin's changes to ``user``, auditing each kind of change.

    Admins cannot change their own role or deactivate themselves, which guarantees that at
    least one active admin always remains.
    """
    is_self = actor.id == user.id
    if is_self and data.role is not None and data.role != user.role:
        raise ApiError("SELF_MODIFICATION", "You cannot change your own role.", 422)
    if is_self and data.is_active is False:
        raise ApiError("SELF_MODIFICATION", "You cannot deactivate your own account.", 422)

    _ensure_unique(None, data.email, exclude_id=user.id)

    changes: dict[str, Any] = {}
    if data.full_name is not None and data.full_name != user.full_name:
        changes["full_name"] = {"from": user.full_name, "to": data.full_name}
        user.full_name = data.full_name
    if data.email is not None and data.email != user.email:
        changes["email"] = {"from": user.email, "to": data.email}
        user.email = data.email
    if changes:
        record_audit(AuditAction.USER_UPDATED, "user", user.id, {"changes": changes})

    if data.role is not None and data.role != user.role:
        record_audit(
            AuditAction.USER_ROLE_CHANGED,
            "user",
            user.id,
            {"from": user.role.value, "to": UserRole(data.role).value},
        )
        user.role = data.role

    if data.is_active is not None and data.is_active != user.is_active:
        user.is_active = data.is_active
        if data.is_active:
            record_audit(AuditAction.USER_ACTIVATED, "user", user.id)
        else:
            user.rotate_session_token()  # log the user out everywhere
            record_audit(AuditAction.USER_DEACTIVATED, "user", user.id)

    if data.new_password is not None:
        user.password_hash = hash_password(data.new_password)
        user.rotate_session_token()
        record_audit(AuditAction.USER_PASSWORD_RESET, "user", user.id)

    return user
