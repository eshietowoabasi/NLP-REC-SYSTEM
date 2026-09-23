from flask import Blueprint, jsonify, request
from flask_login import current_user, login_user, logout_user

from ..extensions import db, login_manager
from ..models import User
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
    if user is None or not user.is_active or not user.check_password(password):
        record_audit("LOGIN_FAILED", "User", user.user_id if user else None, {"username": username})
        # Same message for unknown user / wrong password to avoid account enumeration.
        raise ApiError("Invalid username or password", code="INVALID_CREDENTIALS", status_code=401)

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
