"""Report schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import ReportFormat, ReportStatus
from app.schemas.common import PaginationQuery, RequestModel, ResponseModel
from app.schemas.documents import UserRef

SectionKey = Literal[
    "corpus_summary",
    "nlp_findings",
    "overlap",
    "recommendations",
    "decisions",
    "proposed_courses",
]


class ReportCreate(RequestModel):
    format: ReportFormat
    sections: list[SectionKey] = Field(min_length=1)

    @field_validator("sections")
    @classmethod
    def _unique(cls, sections: list[str]) -> list[str]:
        if len(set(sections)) != len(sections):
            raise ValueError("Each section can only be chosen once.")
        return sections


class ReportListQuery(PaginationQuery):
    session_id: int | None = Field(default=None, ge=1)
    status: ReportStatus | None = None
    format: ReportFormat | None = None


class ReportSessionRef(ResponseModel):
    id: int
    session_name: str


class ReportOut(BaseModel):
    id: int
    session: ReportSessionRef
    format: ReportFormat
    sections: list[str]
    status: ReportStatus
    error_message: str | None
    file_size: int | None
    created_by: UserRef
    created_at: datetime
    completed_at: datetime | None
