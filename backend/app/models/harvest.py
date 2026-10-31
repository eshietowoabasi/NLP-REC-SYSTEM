"""Labour-market collection runs."""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.utils.time import utcnow


class JobHarvestRun(db.Model):
    """One labour-market collection attempt for a programme."""

    __tablename__ = "job_harvest_runs"

    id: Mapped[int] = mapped_column(primary_key=True)

    programme_id: Mapped[int] = mapped_column(
        sa.ForeignKey("programmes.id", ondelete="CASCADE"),
        index=True,
    )

    requested_by_id: Mapped[int] = mapped_column(
        sa.ForeignKey("users.id"),
        index=True,
    )

    status: Mapped[str] = mapped_column(
        sa.String(24),
        default="queued",
        server_default="queued",
        index=True,
    )

    target_count: Mapped[int] = mapped_column(
        default=10,
        server_default="10",
    )

    pages_per_field: Mapped[int] = mapped_column(
        default=2,
        server_default="2",
    )

    examined_count: Mapped[int] = mapped_column(
        default=0,
        server_default="0",
    )

    found_count: Mapped[int] = mapped_column(
        default=0,
        server_default="0",
    )

    imported_count: Mapped[int] = mapped_column(
        default=0,
        server_default="0",
    )

    skipped_count: Mapped[int] = mapped_column(
        default=0,
        server_default="0",
    )

    error_message: Mapped[str | None] = mapped_column(
        sa.Text
    )

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=utcnow,
        server_default=sa.func.now(),
    )

    started_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )

    programme = relationship("Programme")
    requested_by = relationship("User")
