"""Admin endpoints. Every route requires the ``admin`` role."""

from __future__ import annotations

from flask import Blueprint, Response
from flask_login import current_user
from sqlalchemy import or_, select

from app.auth.accounts import create_user, update_user
from app.auth.decorators import role_required
from app.extensions import db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.users import UserCreate, UserListQuery, UserOut, UserUpdate
from app.utils.errors import ApiError
from app.utils.responses import success
from app.utils.validation import paginate, parse_body, parse_query

bp = Blueprint("admin", __name__, url_prefix="/admin")


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
