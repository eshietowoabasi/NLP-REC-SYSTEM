"""Authentication endpoints: sign-up, login, logout, current user, password change, CSRF."""

from __future__ import annotations

from flask import Blueprint, Response, current_app, g, session
from flask_login import current_user, login_user, logout_user
from flask_wtf.csrf import generate_csrf
from sqlalchemy import select

from app.audit import AuditAction, record_audit
from app.auth.accounts import authenticate, change_own_password, create_user
from app.auth.decorators import login_required
from app.extensions import db
from app.models import Programme, UserRole
from app.schemas.auth import ChangePasswordRequest, LoginRequest
from app.schemas.users import RegisterRequest, UserCreate, UserOut
from app.tasks.queue import enqueue
from app.utils.errors import ApiError
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


def auto_load_catalogue() -> None:
    """Create the catalogue's programmes and, at most once an hour, queue loading their NUC
    cores. Never fails the request: sign-up must work even if this cannot run."""
    if not current_app.config.get("AUTO_LOAD_NUC_CATALOGUE", True):
        return
    from app.nuc_catalogue import BUNDLED_CATALOGUE, catalogue_status, ensure_catalogue_programmes

    try:
        ensure_catalogue_programmes(BUNDLED_CATALOGUE)
        redis = current_app.extensions["redis"]
        if redis.get("nuc-catalogue:auto-load"):
            return
        if catalogue_status(BUNDLED_CATALOGUE)["missing"] == 0:
            return
        if redis.set("nuc-catalogue:auto-load", "1", nx=True, ex=3600):
            enqueue("app.tasks.catalogue.load_bundled_catalogue", timeout=1800)
    except Exception:  # noqa: BLE001 - logged; the list below still answers
        db.session.rollback()
        current_app.logger.exception("Could not prepare the NUC catalogue")


@bp.get("/register/programmes")
def register_programmes() -> tuple[Response, int]:
    """The programmes a new account can choose (active ones, by name). No login needed.

    Every NUC programme shipped with SkillBridge is listed: missing ones are created here, and
    their NUC cores are queued for processing once (see ``auto_load_catalogue``).
    """
    auto_load_catalogue()
    programmes = db.session.scalars(
        select(Programme).where(Programme.is_active.is_(True)).order_by(Programme.name)
    )
    return success(
        [{"id": p.id, "name": p.name, "discipline_code": p.discipline_code} for p in programmes]
    )


@bp.post("/register")
def register() -> tuple[Response, int]:
    """Create a planner account for the chosen programmes and log it in.

    Anyone can sign up as a planner; admins can deactivate accounts or change roles later.
    """
    data = parse_body(RegisterRequest)
    active = set(
        db.session.scalars(
            select(Programme.id).where(
                Programme.id.in_(data.programme_ids), Programme.is_active.is_(True)
            )
        )
    )
    if active != set(data.programme_ids):
        raise ApiError(
            "VALIDATION_ERROR",
            "Some fields are invalid.",
            422,
            {"fields": {"programme_ids": ["Choose programmes from the list."]}},
        )
    user = create_user(
        UserCreate(
            username=data.username,
            email=data.email,
            full_name=data.full_name,
            role=UserRole.PLANNER,
            password=data.password,
            programme_ids=data.programme_ids,
        )
    )
    reset_session()
    login_user(user)
    session.permanent = True
    db.session.commit()
    return success({"user": user_json(user), "csrf_token": generate_csrf()}, 201)


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
