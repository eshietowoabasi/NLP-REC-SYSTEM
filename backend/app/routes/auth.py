from datetime import timedelta

from flask import Blueprint, current_app, jsonify, request, session
from flask_login import current_user, login_user, logout_user
from sqlalchemy import func, select

from ..extensions import db, login_manager
from ..models import AuditLog, User
from ..models.user import utcnow
from ..utils.audit import record_audit
from ..utils.errors import ApiError, ValidationError
from ..utils.rbac import login_required

bp = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_id):
    user = db.session.get(User, int(user_id))
    return user if user and user.is_active else None


@login_manager.unauthorized_handler
def unauthorized():
    raise ApiError("Authentication required", code="UNAUTHORIZED", status_code=401)


def _check_not_locked(user):
    """Refuse logins after too many recent failures (spec §14: protect accounts).

    Failures are counted from the audit log, so the limit holds across all API worker
    processes, and only failures since the last successful login count.
    """
    limit = current_app.config["LOGIN_MAX_FAILURES"]
    window = timedelta(minutes=current_app.config["LOGIN_LOCKOUT_MINUTES"])
    since = utcnow() - window
    last_success = db.session.execute(
        select(func.max(AuditLog.action_timestamp)).where(
            AuditLog.action_type == "LOGIN", AuditLog.entity_type == "User", AuditLog.entity_id == user.user_id)
    ).scalar()
    if last_success is not None and last_success.tzinfo is None:  # SQLite returns naive UTC
        last_success = last_success.replace(tzinfo=since.tzinfo)
    if last_success is not None and last_success > since:
        since = last_success
    failures = db.session.execute(
        select(func.count(), func.min(AuditLog.action_timestamp)).where(
            AuditLog.action_type == "LOGIN_FAILED", AuditLog.entity_type == "User",
            AuditLog.entity_id == user.user_id, AuditLog.action_timestamp > since)
    ).one()
    if failures[0] >= limit:
        oldest = failures[1] if failures[1].tzinfo else failures[1].replace(tzinfo=since.tzinfo)
        retry_minutes = max(1, int(((oldest + window) - utcnow()).total_seconds() // 60) + 1)
        record_audit("LOGIN_BLOCKED", "User", user.user_id, {"failures": failures[0]})
        raise ApiError(
            f"Too many failed sign-in attempts. Try again in {retry_minutes} minute(s) or ask an Admin to reset your password.",
            code="ACCOUNT_LOCKED", status_code=429, details={"retry_after_minutes": retry_minutes},
        )


@bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    if not username or not password:
        raise ValidationError(
            "Username and password are required",
            details={k: "Required" for k, v in (("username", username), ("password", password)) if not v},
        )

    user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
    if user is not None:
        _check_not_locked(user)
    if user is None or not user.is_active or not user.check_password(password):
        record_audit("LOGIN_FAILED", "User", user.user_id if user else None, {"username": username})
        # Same message for unknown user / wrong password to avoid account enumeration.
        raise ApiError("Invalid username or password", code="INVALID_CREDENTIALS", status_code=401)

    session.permanent = True  # PERMANENT_SESSION_LIFETIME applies
    login_user(user, remember=bool(payload.get("remember")))
    record_audit("LOGIN", "User", user.user_id, user_id=user.user_id)
    return jsonify({"success": True, "user": user.to_dict()})


@bp.post("/logout")
@login_required
def logout():
    user_id = current_user.user_id
    logout_user()
    record_audit("LOGOUT", "User", user_id, user_id=user_id)
    return jsonify({"success": True})


@bp.get("/me")
@login_required
def me():
    return jsonify({"success": True, "user": current_user.to_dict()})
