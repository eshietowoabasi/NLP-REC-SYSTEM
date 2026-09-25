"""Analysis session schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, StringConstraints, field_validator, model_validator

from app.models.enums import DocumentStatus, SessionStatus, SourceCategory
from app.schemas.common import PaginationQuery, RequestModel, ResponseModel
from app.schemas.documents import UserRef
from app.services.recommendations.scoring import ScoreWeights, WeightsError

SessionName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class WeightsIn(RequestModel):
    ner: float = Field(ge=0, le=1)
    topic: float = Field(ge=0, le=1)
    novelty: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _sums_to_one(self) -> WeightsIn:
        try:
            ScoreWeights(self.ner, self.topic, self.novelty)
        except WeightsError as exc:
            raise ValueError(str(exc)) from exc
        return self


class SessionParameters(RequestModel):
    """Per-session overrides of the default settings; omitted values use the defaults."""

    weights: WeightsIn | None = None
    similarity_threshold: float | None = Field(default=None, gt=0, lt=1)
    max_recommendations: int | None = Field(default=None, ge=1, le=100)


class SessionCreate(RequestModel):
    session_name: SessionName
    document_ids: list[int] = Field(min_length=1)
    parameters: SessionParameters = Field(default_factory=SessionParameters)
    run: bool = False

    @field_validator("document_ids")
    @classmethod
    def _unique(cls, ids: list[int]) -> list[int]:
        if len(set(ids)) != len(ids):
            raise ValueError("Each document can only be selected once.")
        return ids


class SessionListQuery(PaginationQuery):
    status: SessionStatus | None = None
    search: str | None = Field(default=None, max_length=100)


class SessionDocumentOut(ResponseModel):
    id: int
    title: str
    source_category: SourceCategory
    processing_status: DocumentStatus


class NucCoreRef(ResponseModel):
    id: int
    version_label: str


class SessionSummaryOut(ResponseModel):
    id: int
    session_name: str
    status: SessionStatus
    current_stage: str | None
    progress_percent: int
    created_by: UserRef
    document_count: int
    recommendation_count: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class SessionDetailOut(SessionSummaryOut):
    parameter_config: dict[str, Any]
    stage_timings: dict[str, float]
    error_message: str | None
    nuc_core_version: NucCoreRef | None
    documents: list[SessionDocumentOut]
    topic_count: int | None
