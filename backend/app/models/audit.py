"""Audit trail of important actions."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.utils.time import utcnow

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(db.Model):
    """One audited action. ``user_id`` is null for anonymous actions such as failed logins.

    ``entity_id`` is a string so it can also hold non-integer keys (e.g. setting names).
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(sa.ForeignKey("users.id"), index=True)
    action_type: Mapped[str] = mapped_column(sa.String(64), index=True)
    entity_type: Mapped[str | None] = mapped_column(sa.String(64))
    entity_id: Mapped[str | None] = mapped_column(sa.String(64))
    detail: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=sa.text("'{}'::jsonb")
    )
    ip_address: Mapped[str | None] = mapped_column(sa.String(45))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, server_default=sa.func.now(), index=True
    )

    user: Mapped[User | None] = relationship()
