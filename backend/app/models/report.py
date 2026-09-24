import enum
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from .enums import enum_column
from .user import utcnow


class ReportFormat(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"


class Report(db.Model):
    """A generated analysis report (spec §16; docs/DECISIONS.md, D8)."""

    __tablename__ = "reports"

    report_id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        sa.ForeignKey("analysis_sessions.session_id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(sa.ForeignKey("users.user_id"), index=True)
    report_format: Mapped[ReportFormat] = mapped_column(enum_column(ReportFormat, "report_format"))
    file_path: Mapped[str] = mapped_column(sa.String(512))
    file_size: Mapped[int] = mapped_column(sa.Integer)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=utcnow)

    session = relationship("AnalysisSession", back_populates="reports")
    author = relationship("User")

    def to_dict(self):
        return {
            "report_id": self.report_id,
            "session_id": self.session_id,
            "session_name": self.session.session_name if self.session else None,
            "user_id": self.user_id,
            "format": self.report_format.value,
            "file_size": self.file_size,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
