"""Server-side role-based access control (spec §14)."""
from functools import wraps

from flask_login import current_user

from ..models import Role
from .errors import ApiError

# Roles allowed to modify data; Viewer is read-only.
WRITE_ROLES = (Role.ADMIN, Role.PLANNER)


def roles_required(*roles):
    allowed = set(roles)

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                raise ApiError("Authentication required", code="UNAUTHORIZED", status_code=401)
            if allowed and current_user.role not in allowed:
                raise ApiError("You do not have permission for this action", code="FORBIDDEN", status_code=403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def login_required(view):
    return roles_required()(view)
