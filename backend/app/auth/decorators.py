"""Server-side access control for API routes.

Every protected route uses one of these decorators; hiding controls in the frontend is only
cosmetic. Anonymous requests get 401, authenticated users without the required role get 403.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from flask_login import current_user

from app.models.enums import UserRole
from app.utils.errors import ApiError

P = ParamSpec("P")
R = TypeVar("R")

ALL_ROLES = (UserRole.ADMIN, UserRole.PLANNER, UserRole.VIEWER)
EDITOR_ROLES = (UserRole.ADMIN, UserRole.PLANNER)


def _require_authenticated() -> None:
    if not current_user.is_authenticated:
        raise ApiError("UNAUTHORIZED", "Please log in to continue.", 401)


def login_required(view: Callable[P, R]) -> Callable[P, R]:
    """Allow any logged-in, active user."""

    @wraps(view)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        _require_authenticated()
        return view(*args, **kwargs)

    return wrapper


def role_required(*roles: UserRole | str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Allow only logged-in users whose role is one of ``roles``.

    Example::

        @bp.post("/documents")
        @role_required("admin", "planner")
        def upload(): ...
    """
    allowed = {UserRole(role) for role in roles}
    if not allowed:
        raise ValueError("role_required needs at least one role")

    def decorator(view: Callable[P, R]) -> Callable[P, R]:
        @wraps(view)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            _require_authenticated()
            if current_user.role not in allowed:
                raise ApiError(
                    "FORBIDDEN", "You do not have permission to perform this action.", 403
                )
            return view(*args, **kwargs)

        return wrapper

    return decorator
