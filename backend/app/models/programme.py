"""Academic programmes/disciplines analysed by SkillBridge."""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.utils.time import utcnow


class Programme(db.Model):
    """A discipline or academic programme analysed by SkillBridge."""

    __tablename__ = "programmes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(160), unique=True, index=True)
    discipline_code: Mapped[str | None] = mapped_column(sa.String(32), unique=True)
    faculty: Mapped[str | None] = mapped_column(sa.String(160))
    description: Mapped[str | None] = mapped_column(sa.Text)
    country: Mapped[str] = mapped_column(sa.String(80), default="Nigeria", server_default="Nigeria")
    is_active: Mapped[bool] = mapped_column(default=True, server_default=sa.true(), index=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, server_default=sa.func.now()
    )
