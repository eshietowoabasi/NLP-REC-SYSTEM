from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from .enums import SessionStatus, enum_column
from .user import utcnow

PIPELINE_STAGES = (
    "queued", "parsing", "preprocessing", "keywords", "entities", "embeddings", "topics",
    "overlap", "scoring", "saving",
)


class AnalysisSession(db.Model):
    __tablename__ = "analysis_sessions"

    session_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(sa.ForeignKey("users.user_id"), index=True)
    session_name: Mapped[str] = mapped_column(sa.String(255))
    status: Mapped[SessionStatus] = mapped_column(
        enum_column(SessionStatus, "session_status"), default=SessionStatus.PENDING
    )
    parameter_config: Mapped[dict] = mapped_column(sa.JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    # Progress reporting for async runs (spec §15).
    progress_stage: Mapped[str | None] = mapped_column(sa.String(64))
    # Updated when a run is queued and at every stage; lets the sweeper spot runs whose
    # worker died (docs/DECISIONS.md, "Stuck sessions").
    heartbeat_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(sa.Text)
    # Corpus-level NLP output (keywords, skill demand, topics) and run metadata
    # (models, timings, warnings). Per-document output lives in NLPResult.
    corpus_results: Mapped[dict | None] = mapped_column(sa.JSON, deferred=True)
    pipeline_info: Mapped[dict | None] = mapped_column(sa.JSON)

    owner = relationship("User", back_populates="sessions")
    document_links = relationship(
        "DocumentSession",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="DocumentSession.processing_order",
    )
    recommendations = relationship(
        "Recommendation", back_populates="session", cascade="all, delete-orphan"
    )
    reports = relationship("Report", back_populates="session", cascade="all, delete-orphan")

    def progress(self):
        stage = self.progress_stage
        if self.status is not SessionStatus.PROCESSING or stage not in PIPELINE_STAGES:
            return {"stage": stage, "step": None, "total_steps": len(PIPELINE_STAGES) - 1}
        return {"stage": stage, "step": PIPELINE_STAGES.index(stage), "total_steps": len(PIPELINE_STAGES) - 1}

    def to_dict(self, include_documents=False):
        data = {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "session_name": self.session_name,
            "status": self.status.value,
            "parameter_config": self.parameter_config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress(),
            "error_message": self.error_message,
            "pipeline_info": self.pipeline_info,
        }
        if include_documents:
            data["document_ids"] = [link.document_id for link in self.document_links]
        return data


class DocumentSession(db.Model):
    """Junction for the Document M—N AnalysisSession relationship (spec §11.1)."""

    __tablename__ = "document_sessions"
    __table_args__ = (sa.UniqueConstraint("document_id", "session_id", name="uq_document_session"),)

    doc_session_id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        sa.ForeignKey("documents.document_id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[int] = mapped_column(
        sa.ForeignKey("analysis_sessions.session_id", ondelete="CASCADE"), index=True
    )
    processing_order: Mapped[int] = mapped_column(sa.Integer, default=0)

    document = relationship("Document", back_populates="session_links")
    session = relationship("AnalysisSession", back_populates="document_links")
    nlp_results = relationship(
        "NLPResult", back_populates="doc_session", cascade="all, delete-orphan"
    )
