"""User accounts."""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.enums import UserRole, enum_type
from app.utils.time import utcnow

if TYPE_CHECKING:
    from app.models.programme import Programme


def new_session_token() -> str:
    """Random token identifying the current credentials of a user in the session cookie."""
    return secrets.token_hex(32)


class User(UserMixin, db.Model):
    """A person who can log in. Users are deactivated, never deleted.

    ``session_token`` is what the session cookie stores (see :meth:`get_id`). Rotating it
    (on password change, password reset or deactivation) invalidates every existing session
    of that user.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(sa.String(64), unique=True)
    email: Mapped[str] = mapped_column(sa.String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(sa.String(255))
    full_name: Mapped[str] = mapped_column(sa.String(128))
    role: Mapped[UserRole] = mapped_column(enum_type(UserRole, "role"), default=UserRole.VIEWER)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    session_token: Mapped[str] = mapped_column(
        sa.String(64), unique=True, default=new_session_token
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, server_default=sa.func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    # Programmes a planner or viewer may see and work on (admins see all; see app/access.py).
    programmes: Mapped[list[Programme]] = relationship(
        secondary="programme_members", order_by="Programme.name", lazy="selectin"
    )

    def get_id(self) -> str:
        """Identifier stored in the session cookie by Flask-Login."""
        return self.session_token

    def rotate_session_token(self) -> None:
        """Invalidate all existing sessions of this user."""
        self.session_token = new_session_token()

    def has_role(self, *roles: UserRole | str) -> bool:
        return self.role in {UserRole(role) for role in roles}

    def __repr__(self) -> str:
        return f"<User {self.id} {self.username} ({self.role})>"
