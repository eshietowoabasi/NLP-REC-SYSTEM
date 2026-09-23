from datetime import datetime, timezone

import bcrypt
import sqlalchemy as sa
from flask import current_app
from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from .enums import Role, enum_column


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(sa.String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(sa.String(128))
    email: Mapped[str] = mapped_column(sa.String(255), unique=True, index=True)
    role: Mapped[Role] = mapped_column(enum_column(Role, "user_role"), default=Role.VIEWER)
    department_id: Mapped[int | None] = mapped_column(sa.Integer)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True)

    documents = relationship("Document", back_populates="owner")
    sessions = relationship("AnalysisSession", back_populates="owner")
    audit_logs = relationship("AuditLog", back_populates="user")

    def set_password(self, password: str) -> None:
        rounds = current_app.config.get("BCRYPT_ROUNDS", 12)
        self.password_hash = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt(rounds)
        ).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), self.password_hash.encode("utf-8"))

    def get_id(self) -> str:  # Flask-Login
        return str(self.user_id)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "department_id": self.department_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
