"""Recommendations, their evidence passages and the courses they are mapped to."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.enums import OverlapStatus, PlannerDecision, enum_type
from app.utils.time import utcnow

if TYPE_CHECKING:
    from app.models.document import Passage
    from app.models.user import User

_SCORE_COLUMNS = ("ner_score", "topic_score", "novelty_score", "composite_score")


class Recommendation(db.Model):
    """A ranked candidate course topic produced by a session.

    ``auto_title`` is the machine-generated title and never changes; ``topic_title`` starts as
    a copy and can be edited by planners.
    """

    __tablename__ = "recommendations"
    __table_args__ = (
        sa.UniqueConstraint("session_id", "rank"),
        *(
            sa.CheckConstraint(f"{column} BETWEEN 0 AND 1", name=f"{column}_range")
            for column in _SCORE_COLUMNS
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        sa.ForeignKey("analysis_sessions.id", ondelete="CASCADE"), index=True
    )
    rank: Mapped[int]
    topic_id: Mapped[int] = mapped_column(comment="BERTopic topic number within the session")
    auto_title: Mapped[str] = mapped_column(sa.String(255))
    topic_title: Mapped[str] = mapped_column(sa.String(255))
    topic_description: Mapped[str] = mapped_column(sa.Text)
    keywords: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    skills: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    ner_score: Mapped[float]
    topic_score: Mapped[float]
    novelty_score: Mapped[float]
    composite_score: Mapped[float]
    max_similarity: Mapped[float]
    closest_nuc_passage_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("passages.id", ondelete="SET NULL")
    )
    overlap_status: Mapped[OverlapStatus] = mapped_column(
        enum_type(OverlapStatus, "overlap_status")
    )
    planner_decision: Mapped[PlannerDecision | None] = mapped_column(
        enum_type(PlannerDecision, "planner_decision"), index=True
    )
    planner_notes: Mapped[str | None] = mapped_column(sa.Text)
    decided_by_id: Mapped[int | None] = mapped_column(sa.ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, server_default=sa.func.now()
    )

    closest_nuc_passage: Mapped[Passage | None] = relationship()
    decided_by: Mapped[User | None] = relationship()
    evidence: Mapped[list[RecommendationEvidence]] = relationship(
        back_populates="recommendation",
        order_by="RecommendationEvidence.relevance_score.desc()",
        cascade="all, delete-orphan",
    )
    mapping: Mapped[CurriculumMap | None] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan"
    )


class RecommendationEvidence(db.Model):
    """A passage supporting a recommendation, with how representative it is of the topic."""

    __tablename__ = "recommendation_evidence"
    __table_args__ = (sa.UniqueConstraint("recommendation_id", "passage_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(
        sa.ForeignKey("recommendations.id", ondelete="CASCADE"), index=True
    )
    passage_id: Mapped[int] = mapped_column(sa.ForeignKey("passages.id"), index=True)
    relevance_score: Mapped[float]

    recommendation: Mapped[Recommendation] = relationship(back_populates="evidence")
    passage: Mapped[Passage] = relationship()


class CurriculumMap(db.Model):
    """The proposed course an accepted recommendation is mapped to (one per recommendation)."""

    __tablename__ = "curriculum_maps"
    __table_args__ = (sa.CheckConstraint("credit_units IN (1, 2, 3)", name="credit_units_allowed"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(
        sa.ForeignKey("recommendations.id", ondelete="CASCADE"), unique=True
    )
    course_code: Mapped[str] = mapped_column(sa.String(16))
    course_title: Mapped[str] = mapped_column(sa.String(255))
    credit_units: Mapped[int]
    prerequisites: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=sa.text("'[]'::jsonb")
    )
    learning_outcomes: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=sa.text("'[]'::jsonb")
    )
    created_by_id: Mapped[int] = mapped_column(sa.ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=sa.func.now()
    )

    recommendation: Mapped[Recommendation] = relationship(back_populates="mapping")
    created_by: Mapped[User] = relationship()
