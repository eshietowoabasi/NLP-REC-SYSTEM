"""Document, passage and NUC core schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field, StringConstraints

from app.models.enums import DocumentStatus, FileType, SessionStatus, SourceCategory
from app.schemas.common import PaginationQuery, RequestModel, ResponseModel

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
    page_count: int | None
    word_count: int | None
    uploaded_at: datetime
    parsed_at: datetime | None
    uploaded_by: UserRef


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


VersionLabel = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


class NucCoreUploadForm(RequestModel):
    version_label: VersionLabel
