from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from .enums import DocumentStatus, FileType, SourceCategory, enum_column
from .user import utcnow


class Document(db.Model):
    __tablename__ = "documents"

    document_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(sa.ForeignKey("users.user_id"), index=True)
    title: Mapped[str] = mapped_column(sa.String(255))
    file_path: Mapped[str] = mapped_column(sa.String(512))
    file_type: Mapped[FileType] = mapped_column(enum_column(FileType, "file_type"))
    source_category: Mapped[SourceCategory] = mapped_column(
        enum_column(SourceCategory, "source_category"), index=True
    )
    processing_status: Mapped[DocumentStatus] = mapped_column(
        enum_column(DocumentStatus, "document_status"), default=DocumentStatus.UPLOADED
    )
    upload_timestamp: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)
    # Additions beyond the spec's core fields, needed for §7.2 diagnosability.
    original_filename: Mapped[str | None] = mapped_column(sa.String(255))
    file_size: Mapped[int | None] = mapped_column(sa.Integer)
    error_message: Mapped[str | None] = mapped_column(sa.Text)
    # Parsing output (docs/DECISIONS.md, D10). Text is deferred: list views never load it.
    content_hash: Mapped[str | None] = mapped_column(sa.String(64), unique=True)
    extracted_text: Mapped[str | None] = mapped_column(sa.Text, deferred=True)
    word_count: Mapped[int | None] = mapped_column(sa.Integer)
    page_count: Mapped[int | None] = mapped_column(sa.Integer)

    owner = relationship("User", back_populates="documents")
    session_links = relationship(
        "DocumentSession", back_populates="document", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "document_id": self.document_id,
            "user_id": self.user_id,
            "title": self.title,
            "file_type": self.file_type.value,
            "source_category": self.source_category.value,
            "processing_status": self.processing_status.value,
            "upload_timestamp": self.upload_timestamp.isoformat() if self.upload_timestamp else None,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "error_message": self.error_message,
            "word_count": self.word_count,
            "page_count": self.page_count,
        }
