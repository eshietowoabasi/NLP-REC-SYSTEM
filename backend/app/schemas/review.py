"""Recommendation review and curriculum mapping schemas."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.models.enums import OverlapStatus, PlannerDecision, SourceCategory
from app.schemas.common import RequestModel, ResponseModel
from app.schemas.documents import UserRef

# --------------------------------------------------------------------- recommendations


class RecommendationOut(ResponseModel):
    id: int
    session_id: int
    rank: int
    topic_id: int
    auto_title: str
    topic_title: str
    topic_description: str
    keywords: list[dict[str, Any]]
    skills: list[dict[str, Any]]
    ner_score: float
    topic_score: float
    novelty_score: float
    composite_score: float
    max_similarity: float
    overlap_status: OverlapStatus
    planner_decision: PlannerDecision | None
    planner_notes: str | None
    decided_at: datetime | None
    decided_by: UserRef | None
    has_mapping: bool


class RecommendationListQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    decision: Literal["all", "undecided", "accepted", "rejected", "flagged"] = "all"
    hide_duplicates: bool = False


class DocumentRef(ResponseModel):
    id: int
    title: str
    source_category: SourceCategory


class EvidenceOut(BaseModel):
    passage_id: int
    relevance_score: float
    text: str
    page_number: int | None
    position: int
    document: DocumentRef


class NucPassageOut(BaseModel):
    id: int
    text: str
    page_number: int | None
    document_title: str
    version_label: str | None


class SessionContext(BaseModel):
    id: int
    session_name: str
    weights: dict[str, float]
    similarity_threshold: float


Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Description = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)
]


class RecommendationEdit(RequestModel):
    topic_title: Title | None = None
    topic_description: Description | None = None

    @model_validator(mode="after")
    def _something(self) -> RecommendationEdit:
        if self.topic_title is None and self.topic_description is None:
            raise ValueError("Provide a new title or description.")
        return self


class DecisionIn(RequestModel):
    """``decision: null`` clears the decision (back to undecided)."""

    decision: PlannerDecision | None
    notes: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None


# ----------------------------------------------------------------------------- mapping

COURSE_CODE = re.compile(r"^([A-Z]{2,4})\s*(\d{3}[A-Z]?)$")


def _course_code(value: str) -> str:
    match = COURSE_CODE.match(" ".join(value.upper().split()))
    if not match:
        raise ValueError("Use a course code like “CSC 419” (2–4 letters, then 3 digits).")
    return f"{match.group(1)} {match.group(2)}"


def _clean_list(values: list[str]) -> list[str]:
    cleaned = [" ".join(v.split()) for v in values if v and v.strip()]
    if len({v.lower() for v in cleaned}) != len(cleaned):
        raise ValueError("Remove duplicate entries.")
    return cleaned


CourseCode = Annotated[str, AfterValidator(_course_code)]
Prerequisite = Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)]
Outcome = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


class MappingIn(RequestModel):
    course_code: CourseCode
    course_title: Title
    credit_units: Literal[1, 2, 3]
    prerequisites: Annotated[list[Prerequisite], AfterValidator(_clean_list)] = Field(
        default_factory=list, max_length=10
    )
    learning_outcomes: Annotated[list[Outcome], AfterValidator(_clean_list)] = Field(
        min_length=1, max_length=15
    )


class MappingOut(ResponseModel):
    id: int
    recommendation_id: int
    course_code: str
    course_title: str
    credit_units: int
    prerequisites: list[str]
    learning_outcomes: list[str]
    created_by: UserRef
    created_at: datetime
    updated_at: datetime


class RecommendationRef(BaseModel):
    id: int
    rank: int
    topic_title: str
    composite_score: float
    overlap_status: OverlapStatus
