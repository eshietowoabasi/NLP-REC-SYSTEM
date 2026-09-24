"""User administration and audit log review (spec §13 /admin/users, /admin/audit; §14)."""
import re
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import current_user
from sqlalchemy import select

from ..extensions import db
from ..models import AuditLog, Role, User
from ..utils.audit import record_audit
from ..utils.errors import ConflictError, NotFoundError, ValidationError
from ..utils.pagination import paginate
from ..utils.params import parse_enum
from ..utils.rbac import roles_required

bp = Blueprint("admin", __name__)

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,64}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


def _validate_password(password, errors):
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        errors["password"] = f"At least {MIN_PASSWORD_LENGTH} characters"


def _get_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found")
    return user


@bp.get("/users")
@roles_required(Role.ADMIN)
def list_users():
    query = select(User).order_by(User.username)
    if q := request.args.get("q", "").strip():
        query = query.where(User.username.ilike(f"%{q}%") | User.email.ilike(f"%{q}%"))
    return jsonify(paginate(query, User.to_dict, default_per_page=50))


@bp.post("/users")
@roles_required(Role.ADMIN)
def create_user():
    payload = request.get_json(silent=True) or {}
    errors = {}
    username = (payload.get("username") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    if not USERNAME_RE.match(username):
        errors["username"] = "3-64 letters, digits, '.', '_' or '-'"
    if not EMAIL_RE.match(email):
        errors["email"] = "Invalid email address"
    _validate_password(payload.get("password"), errors)
    role = Role.VIEWER
    if "role" in payload:
        try:
            role = Role(payload["role"])
        except ValueError:
            errors["role"] = f"Must be one of: {', '.join(r.value for r in Role)}"
    if errors:
        raise ValidationError("Invalid user", details=errors)
    if db.session.execute(select(User).where((User.username == username) | (User.email == email))).first():
        raise ConflictError("A user with that username or email already exists", code="USER_EXISTS")

    user = User(username=username, email=email, role=role,
                department_id=payload.get("department_id") if isinstance(payload.get("department_id"), int) else None)
    user.set_password(payload["password"])
    db.session.add(user)
    db.session.flush()
    record_audit("USER_CREATE", "User", user.user_id, {"username": username, "role": role.value}, commit=False)
    db.session.commit()
    return jsonify({"success": True, "user": user.to_dict()}), 201


@bp.patch("/users/<int:user_id>")
@roles_required(Role.ADMIN)
def update_user(user_id):
    user = _get_user(user_id)
    payload = request.get_json(silent=True) or {}
    errors, changes = {}, {}
    if "role" in payload:
        role = parse_enum(Role, payload["role"], "role")
        if user.user_id == current_user.user_id and role is not Role.ADMIN:
            errors["role"] = "You cannot remove your own Admin role"
        changes["role"] = [user.role.value, role.value]
        user.role = role
    if "is_active" in payload:
        if not isinstance(payload["is_active"], bool):
            errors["is_active"] = "Must be true or false"
        elif user.user_id == current_user.user_id and not payload["is_active"]:
            errors["is_active"] = "You cannot deactivate your own account"
        else:
            changes["is_active"] = [user.is_active, payload["is_active"]]
            user.is_active = payload["is_active"]
    if "email" in payload:
        email = (payload["email"] or "").strip().lower()
        if not EMAIL_RE.match(email):
            errors["email"] = "Invalid email address"
        elif db.session.execute(select(User).where(User.email == email, User.user_id != user.user_id)).first():
            errors["email"] = "Already in use"
        else:
            user.email = email
            changes["email"] = "updated"
    if "password" in payload:
        _validate_password(payload["password"], errors)
        if "password" not in errors:
            user.set_password(payload["password"])
            changes["password"] = "reset"
    if errors:
        db.session.rollback()
        raise ValidationError("Invalid update", details=errors)
    if not changes:
        raise ValidationError("Nothing to update")
    record_audit("USER_UPDATE", "User", user.user_id, changes, commit=False)
    db.session.commit()
    return jsonify({"success": True, "user": user.to_dict()})


@bp.get("/audit")
@roles_required(Role.ADMIN)
def audit_log():
    query = select(AuditLog).order_by(AuditLog.action_timestamp.desc(), AuditLog.log_id.desc())
    if user_id := request.args.get("user_id", type=int):
        query = query.where(AuditLog.user_id == user_id)
    if action := request.args.get("action_type"):
        query = query.where(AuditLog.action_type == action.upper())
    if entity := request.args.get("entity_type"):
        query = query.where(AuditLog.entity_type == entity)
    for arg, op in (("from", "__ge__"), ("to", "__le__")):
        if value := request.args.get(arg):
            try:
                moment = datetime.fromisoformat(value)
            except ValueError:
                raise ValidationError(f"'{arg}' must be an ISO date or datetime")
            query = query.where(getattr(AuditLog.action_timestamp, op)(moment))
    usernames = dict(db.session.execute(select(User.user_id, User.username)).all())

    def serialize(entry):
        return {**entry.to_dict(), "username": usernames.get(entry.user_id)}

    return jsonify(paginate(query, serialize, default_per_page=50))
