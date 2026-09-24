"""Analysis sessions, the documents they use and their session-level NLP results."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.enums import NLPResultType, SessionStatus, enum_type
from app.utils.time import utcnow

if TYPE_CHECKING:
    from app.models.document import Document, NucCoreVersion
    from app.models.user import User


class AnalysisSession(db.Model):
    """One run of the pipeline over a chosen set of documents with its own parameters."""

    __tablename__ = "analysis_sessions"
    __table_args__ = (
        sa.CheckConstraint("progress_percent BETWEEN 0 AND 100", name="progress_percent_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    created_by_id: Mapped[int] = mapped_column(sa.ForeignKey("users.id"), index=True)
    session_name: Mapped[str] = mapped_column(sa.String(200))
    status: Mapped[SessionStatus] = mapped_column(
        enum_type(SessionStatus, "status"), default=SessionStatus.PENDING, index=True
    )
    current_stage: Mapped[str | None] = mapped_column(sa.String(32))
    progress_percent: Mapped[int] = mapped_column(default=0, server_default="0")
    parameter_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=sa.text("'{}'::jsonb")
    )
    # Set when the session runs: the NUC core baseline it was compared against.
    nuc_core_version_id: Mapped[int | None] = mapped_column(sa.ForeignKey("nuc_core_versions.id"))
    error_message: Mapped[str | None] = mapped_column(sa.Text)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, server_default=sa.func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))

    created_by: Mapped[User] = relationship()
    nuc_core_version: Mapped[NucCoreVersion | None] = relationship()
    document_links: Mapped[list[DocumentSession]] = relationship(
        back_populates="session",
        order_by="DocumentSession.processing_order",
        cascade="all, delete-orphan",
    )


class DocumentSession(db.Model):
    """Junction between a session and the documents it analyses.

    The document foreign key is RESTRICT: a document used by any session cannot be deleted.
    """

    __tablename__ = "document_sessions"
    __table_args__ = (sa.UniqueConstraint("document_id", "session_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        sa.ForeignKey("documents.id", ondelete="RESTRICT"), index=True
    )
    session_id: Mapped[int] = mapped_column(
        sa.ForeignKey("analysis_sessions.id", ondelete="CASCADE"), index=True
    )
    processing_order: Mapped[int]

    document: Mapped[Document] = relationship()
    session: Mapped[AnalysisSession] = relationship(back_populates="document_links")


class NLPResult(db.Model):
    """Session-level output of one pipeline stage, shown on the Evidence Dashboard."""

    __tablename__ = "nlp_results"
    __table_args__ = (sa.UniqueConstraint("session_id", "result_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        sa.ForeignKey("analysis_sessions.id", ondelete="CASCADE"), index=True
    )
    result_type: Mapped[NLPResultType] = mapped_column(enum_type(NLPResultType, "result_type"))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, server_default=sa.func.now()
    )
