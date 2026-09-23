from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from .user import utcnow


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    log_id: Mapped[int] = mapped_column(primary_key=True)
    # Nullable so failed logins / system actions can still be recorded.
    user_id: Mapped[int | None] = mapped_column(sa.ForeignKey("users.user_id"), index=True)
    action_type: Mapped[str] = mapped_column(sa.String(64), index=True)
    entity_type: Mapped[str | None] = mapped_column(sa.String(64))
    entity_id: Mapped[int | None] = mapped_column(sa.Integer)
    detail: Mapped[dict | None] = mapped_column(sa.JSON)
    action_timestamp: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=utcnow, index=True
    )

    user = relationship("User", back_populates="audit_logs")

    def to_dict(self):
        return {
            "log_id": self.log_id,
            "user_id": self.user_id,
            "action_type": self.action_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "detail": self.detail,
            "action_timestamp": self.action_timestamp.isoformat() if self.action_timestamp else None,
        }
