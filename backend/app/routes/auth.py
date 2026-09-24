"""Authentication endpoints: login, logout, current user, password change, CSRF token."""

from __future__ import annotations

from flask import Blueprint, Response, current_app, g, session
from flask_login import current_user, login_user, logout_user
from flask_wtf.csrf import generate_csrf

from app.audit import AuditAction, record_audit
from app.auth.accounts import authenticate, change_own_password
from app.auth.decorators import login_required
from app.extensions import db
from app.schemas.auth import ChangePasswordRequest, LoginRequest
from app.schemas.users import UserOut
from app.utils.responses import success
from app.utils.validation import parse_body

bp = Blueprint("auth", __name__, url_prefix="/auth")


def user_json(user: object) -> dict:
    return UserOut.model_validate(user).model_dump(mode="json")


def reset_session() -> None:
    """Clear the session (dropping any previous CSRF secret) and forget the cached token.

    Flask-WTF caches the signed token on ``g`` for the rest of the request, so it must be
    removed too, otherwise :func:`generate_csrf` would return the old, now invalid token.
    """
    session.clear()
    g.pop(current_app.config.get("WTF_CSRF_FIELD_NAME", "csrf_token"), None)


@bp.get("/csrf")
def csrf_token() -> tuple[Response, int]:
    """Return a CSRF token; send it as ``X-CSRFToken`` on every state-changing request."""
    return success({"csrf_token": generate_csrf()})


@bp.post("/login")
def login() -> tuple[Response, int]:
    """Log in with username or email + password; sets the session cookie.

    The session is cleared first, so a fresh CSRF token is issued and returned.
    """
    data = parse_body(LoginRequest)
    user = authenticate(data.identifier, data.password)
    reset_session()
    login_user(user)
    session.permanent = True
    db.session.commit()
    return success({"user": user_json(user), "csrf_token": generate_csrf()})


@bp.post("/logout")
@login_required
def logout() -> tuple[Response, int]:
    """End the current session. Returns a fresh CSRF token for the anonymous session."""
    record_audit(AuditAction.LOGOUT, "user", current_user.id)
    db.session.commit()
    logout_user()
    reset_session()
    return success({"csrf_token": generate_csrf()})


@bp.get("/me")
@login_required
def me() -> tuple[Response, int]:
    """The logged-in user."""
    return success(user_json(current_user))


@bp.post("/change-password")
@login_required
def change_password() -> tuple[Response, int]:
    """Change the logged-in user's password. Other sessions of this user are ended."""
    data = parse_body(ChangePasswordRequest)
    user = current_user._get_current_object()
    change_own_password(user, data.current_password, data.new_password)
    db.session.commit()
    # The session token was rotated; re-issue the cookie so this session stays valid.
    login_user(user)
    return success({"message": "Password changed."})
