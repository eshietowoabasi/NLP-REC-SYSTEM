"""Document, passage and NUC core schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, computed_field, field_validator

from app.models.enums import DocumentStatus, FileType, SessionStatus, SourceCategory
from app.schemas.common import PaginationQuery, RequestModel, ResponseModel
from app.utils.labels import document_label

# Categories a planner can choose when uploading; ``nuc_core`` has its own admin screen.
UPLOAD_CATEGORIES = (
    SourceCategory.JOB_MARKET,
    SourceCategory.INSTITUTIONAL,
    SourceCategory.POLICY,
    SourceCategory.ACADEMIC,
)


class UserRef(ResponseModel):
    id: int
    full_name: str


class DocumentOut(ResponseModel):
    id: int
    title: str
    original_filename: str
    file_type: FileType
    file_size: int
    source_category: SourceCategory
    processing_status: DocumentStatus
    error_message: str | None
    source: str | None
    source_url: str | None
    published_on: date | None
    page_count: int | None
    word_count: int | None
    uploaded_at: datetime
    parsed_at: datetime | None
    uploaded_by: UserRef

    @computed_field  # type: ignore[prop-decorator]
    @property
    def label(self) -> str:
        """Readable reference: "Title, job advert (MyJobMag, Sep 2026)"."""
        return document_label(self.title, self.source_category, self.source, self.published_on)


class DocumentEdit(RequestModel):
    """Details shown wherever the document is referenced (any subset)."""

    title: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
        | None
    ) = None
    source: Annotated[str, StringConstraints(strip_whitespace=True, max_length=128)] | None = None
    source_url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1024)] | None = (
        None
    )
    published_on: date | None = None

    @field_validator("source_url")
    @classmethod
    def _http(cls, value: str | None) -> str | None:
        if value and not value.lower().startswith(("http://", "https://")):
            raise ValueError("Enter a web address starting with http:// or https://.")
        return value or None


class PassageOut(ResponseModel):
    id: int
    position: int
    page_number: int | None
    text: str


class SessionRef(ResponseModel):
    id: int
    session_name: str
    status: SessionStatus
    created_at: datetime


class DocumentDetailOut(DocumentOut):
    passage_count: int
    preview: list[PassageOut]
    sessions: list[SessionRef]
    # NUC core documents are managed on the NUC core screen, not the document library.
    is_nuc_core: bool


class DocumentListQuery(PaginationQuery):
    category: SourceCategory | None = None
    # Archived documents are hidden unless status=archived is requested.
    status: DocumentStatus | None = None
    search: str | None = Field(default=None, max_length=100)


class PassageListQuery(PaginationQuery):
    per_page: int = Field(default=50, ge=1, le=100)


class RejectedFile(ResponseModel):
    filename: str
    reason: str


class NucCoreVersionOut(ResponseModel):
    id: int
    version_label: str
    is_active: bool
    created_at: datetime
    uploaded_by: UserRef
    document: DocumentOut


class NucCourseOut(BaseModel):
    """A course of the NUC core; ``excluded`` courses are not compared with themes."""

    id: int
    code: str
    title: str
    units: int | None
    page_number: int | None
    excluded: bool


VersionLabel = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


class NucCoreUploadForm(RequestModel):
    version_label: VersionLabel
