"""Uploaded documents, NUC core reference versions and the passages extracted from them."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.enums import DocumentStatus, FileType, SourceCategory, enum_type
from app.utils.time import utcnow

if TYPE_CHECKING:
    from app.models.user import User


class Document(db.Model):
    """A source document. The file lives on the storage volume under ``stored_filename``."""

    __tablename__ = "documents"
    __table_args__ = (
        sa.CheckConstraint("file_size > 0", name="file_size_positive"),
        sa.Index("ix_documents_category_status", "source_category", "processing_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    uploaded_by_id: Mapped[int] = mapped_column(sa.ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(sa.String(255))
    original_filename: Mapped[str] = mapped_column(sa.String(255))
    stored_filename: Mapped[str] = mapped_column(sa.String(64), unique=True)
    file_type: Mapped[FileType] = mapped_column(enum_type(FileType, "file_type"))
    file_size: Mapped[int] = mapped_column(sa.BigInteger)
    # SHA-256 of the file content, used to reject duplicate uploads.
    content_hash: Mapped[str] = mapped_column(sa.String(64), index=True)
    source_category: Mapped[SourceCategory] = mapped_column(
        enum_type(SourceCategory, "source_category")
    )
    processing_status: Mapped[DocumentStatus] = mapped_column(
        enum_type(DocumentStatus, "processing_status"), default=DocumentStatus.UPLOADED
    )
    error_message: Mapped[str | None] = mapped_column(sa.Text)
    page_count: Mapped[int | None]
    word_count: Mapped[int | None]
    uploaded_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, server_default=sa.func.now()
    )
    parsed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))

    uploaded_by: Mapped[User] = relationship()
    passages: Mapped[list[Passage]] = relationship(
        back_populates="document", order_by="Passage.position", cascade="all, delete-orphan"
    )


class NucCoreVersion(db.Model):
    """A version of the NUC CCMAS core reference. At most one version is active at a time."""

    __tablename__ = "nuc_core_versions"
    __table_args__ = (
        # Partial unique index: only one row may have is_active = true.
        sa.Index(
            "uq_nuc_core_versions_single_active",
            "is_active",
            unique=True,
            postgresql_where=sa.text("is_active"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(sa.ForeignKey("documents.id"), unique=True)
    version_label: Mapped[str] = mapped_column(sa.String(64))
    is_active: Mapped[bool] = mapped_column(default=False, server_default=sa.false())
    uploaded_by_id: Mapped[int] = mapped_column(sa.ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, server_default=sa.func.now()
    )

    document: Mapped[Document] = relationship()
    uploaded_by: Mapped[User] = relationship()


class Passage(db.Model):
    """A group of 3-5 consecutive sentences: the unit of analysis.

    ``text`` keeps the original wording and casing (NER, SBERT, BERTopic, evidence display);
    ``normalised_text`` is the lowercased, lemmatised, stop-word-free version used only for
    TF-IDF. ``embedding`` has no fixed dimension so the SBERT model can be changed;
    ``embedding_model`` records which model produced it.
    """

    __tablename__ = "passages"
    __table_args__ = (sa.UniqueConstraint("document_id", "position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        sa.ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int]
    page_number: Mapped[int | None]
    text: Mapped[str] = mapped_column(sa.Text)
    normalised_text: Mapped[str] = mapped_column(sa.Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector())
    embedding_model: Mapped[str | None] = mapped_column(sa.String(128))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, server_default=sa.func.now()
    )

    document: Mapped[Document] = relationship(back_populates="passages")
