"""Academic programmes/disciplines analysed by SkillBridge."""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.enums import NucDiscipline, enum_type
from app.utils.time import utcnow

# Which programmes a planner or viewer works on. Admins need no rows: they see everything.
programme_members = sa.Table(
    "programme_members",
    db.metadata,
    sa.Column(
        "user_id", sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    ),
    sa.Column(
        "programme_id",
        sa.ForeignKey("programmes.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
)


class Programme(db.Model):
    """A discipline or academic programme analysed by SkillBridge."""

    __tablename__ = "programmes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(160), unique=True, index=True)
    discipline_code: Mapped[str | None] = mapped_column(sa.String(32), unique=True)
    faculty: Mapped[str | None] = mapped_column(sa.String(160))
    # The NUC CCMAS discipline: chooses the programme's skills list (plus general skills).
    nuc_discipline: Mapped[NucDiscipline | None] = mapped_column(
        enum_type(NucDiscipline, "nuc_discipline"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(sa.Text)
    job_search_terms: Mapped[list[str]] = mapped_column(
        sa.JSON, default=list, server_default=sa.text("'[]'::json"), nullable=False
    )
    job_field_slugs: Mapped[list[str]] = mapped_column(
        sa.JSON, default=list, server_default=sa.text("'[]'::json"), nullable=False
    )
    country: Mapped[str] = mapped_column(sa.String(80), default="Nigeria", server_default="Nigeria")
    is_active: Mapped[bool] = mapped_column(default=True, server_default=sa.true(), index=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, server_default=sa.func.now()
    )
