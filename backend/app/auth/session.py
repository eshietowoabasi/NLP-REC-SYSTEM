"""Flask-Login integration: how the session cookie is turned back into a user."""

from __future__ import annotations

from flask import Flask
from sqlalchemy import select

from app.extensions import db, login_manager
from app.models.user import User
from app.utils.errors import ApiError


def init_login_manager(app: Flask) -> None:
    """Configure Flask-Login for a JSON API (401 instead of a login-page redirect)."""
    login_manager.init_app(app)
    login_manager.session_protection = "basic"

    @login_manager.user_loader
    def load_user(session_token: str) -> User | None:
        # Deactivated users and rotated tokens (password changed/reset) are rejected here,
        # which ends their existing sessions immediately.
        return db.session.scalar(
            select(User).where(User.session_token == session_token, User.is_active.is_(True))
        )

    @login_manager.unauthorized_handler
    def unauthorized() -> None:
        raise ApiError("UNAUTHORIZED", "Please log in to continue.", 401)
