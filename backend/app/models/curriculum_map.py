import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db

ALLOWED_CREDIT_UNITS = (1, 2, 3)


class CurriculumMap(db.Model):
    __tablename__ = "curriculum_maps"
    __table_args__ = (
        sa.CheckConstraint("credit_units IN (1, 2, 3)", name="credit_units_allowed"),
    )

    map_id: Mapped[int] = mapped_column(primary_key=True)
    rec_id: Mapped[int] = mapped_column(
        sa.ForeignKey("recommendations.rec_id", ondelete="CASCADE"), index=True
    )
    course_code: Mapped[str] = mapped_column(sa.String(16))
    course_title: Mapped[str] = mapped_column(sa.String(255))
    credit_units: Mapped[int] = mapped_column(sa.Integer)
    prerequisites: Mapped[list | None] = mapped_column(sa.JSON)
    learning_outcomes: Mapped[list | None] = mapped_column(sa.JSON)

    recommendation = relationship("Recommendation", back_populates="curriculum_maps")

    def to_dict(self):
        return {
            "map_id": self.map_id,
            "rec_id": self.rec_id,
            "course_code": self.course_code,
            "course_title": self.course_title,
            "credit_units": self.credit_units,
            "prerequisites": self.prerequisites or [],
            "learning_outcomes": self.learning_outcomes or [],
        }
