"""Admin-managed configuration: settings, custom skill patterns and domain stop words."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db
from app.models.enums import SkillLabel, enum_type
from app.utils.time import utcnow


class Setting(db.Model):
    """A key/value setting. Known keys and their defaults are listed in ``app.settings``."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(sa.String(64), primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB)
    updated_by_id: Mapped[int | None] = mapped_column(sa.ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=sa.func.now()
    )


class SkillPattern(db.Model):
    """A spaCy EntityRuler pattern mapping text to a canonical skill.

    ``pattern`` is either a phrase string (matched case-insensitively) or a spaCy token
    pattern (a list of token attribute dicts), stored as JSON.
    """

    __tablename__ = "skill_patterns"
    __table_args__ = (sa.UniqueConstraint("label", "pattern"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[SkillLabel] = mapped_column(enum_type(SkillLabel, "label"))
    pattern: Mapped[Any] = mapped_column(JSONB)
    canonical_name: Mapped[str] = mapped_column(sa.String(128), index=True)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, server_default=sa.func.now()
    )


class StopWord(db.Model):
    """A domain-specific stop word removed before TF-IDF (in addition to standard lists)."""

    __tablename__ = "stop_words"

    id: Mapped[int] = mapped_column(primary_key=True)
    word: Mapped[str] = mapped_column(sa.String(64), unique=True)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=sa.true())
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, server_default=sa.func.now()
    )
