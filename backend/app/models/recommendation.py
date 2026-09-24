import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from .enums import OverlapStatus, PlannerDecision, enum_column

SCORE_FIELDS = ("ner_score", "topic_score", "novelty_score", "composite_score", "max_similarity")


class Recommendation(db.Model):
    __tablename__ = "recommendations"
    __table_args__ = tuple(
        sa.CheckConstraint(f"{field} >= 0 AND {field} <= 1", name=f"{field}_range")
        for field in SCORE_FIELDS
    )

    rec_id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        sa.ForeignKey("analysis_sessions.session_id", ondelete="CASCADE"), index=True
    )
    topic_title: Mapped[str] = mapped_column(sa.String(255))
    topic_description: Mapped[str | None] = mapped_column(sa.Text)
    ner_score: Mapped[float] = mapped_column(sa.Float)
    topic_score: Mapped[float] = mapped_column(sa.Float)
    novelty_score: Mapped[float] = mapped_column(sa.Float)
    composite_score: Mapped[float] = mapped_column(sa.Float, index=True)
    # Kept alongside novelty (= 1 - max_similarity) so overlap results are auditable.
    max_similarity: Mapped[float | None] = mapped_column(sa.Float)
    overlap_status: Mapped[OverlapStatus] = mapped_column(
        enum_column(OverlapStatus, "overlap_status")
    )
    planner_decision: Mapped[PlannerDecision | None] = mapped_column(
        enum_column(PlannerDecision, "planner_decision")
    )
    planner_notes: Mapped[str | None] = mapped_column(sa.Text)
    # Position in the ranked list (1 = top). Potential duplicates rank after novel topics.
    rank: Mapped[int | None] = mapped_column(sa.Integer)
    # Traceability (spec §16): source topic, passages, documents, skills, closest core segments.
    evidence: Mapped[dict | None] = mapped_column(sa.JSON, deferred=True)

    session = relationship("AnalysisSession", back_populates="recommendations")
    curriculum_maps = relationship(
        "CurriculumMap", back_populates="recommendation", cascade="all, delete-orphan"
    )

    def to_dict(self, include_evidence=False):
        data = {
            "rec_id": self.rec_id,
            "rank": self.rank,
            "session_id": self.session_id,
            "topic_title": self.topic_title,
            "topic_description": self.topic_description,
            "ner_score": self.ner_score,
            "topic_score": self.topic_score,
            "novelty_score": self.novelty_score,
            "composite_score": self.composite_score,
            "max_similarity": self.max_similarity,
            "overlap_status": self.overlap_status.value,
            "planner_decision": self.planner_decision.value if self.planner_decision else None,
            "planner_notes": self.planner_notes,
        }
        if include_evidence:
            data["evidence"] = self.evidence
        return data
