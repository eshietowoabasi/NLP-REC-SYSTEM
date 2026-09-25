"""Admin schemas: system settings, skill patterns, stop words and the audit log."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Annotated, Any

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    StringConstraints,
    ValidationInfo,
    field_validator,
    model_validator,
)

from app.models.enums import SkillLabel
from app.schemas.common import PaginationQuery, RequestModel, ResponseModel
from app.schemas.documents import UserRef
from app.schemas.sessions import WeightsIn

# ------------------------------------------------------------------------------ settings


class RangeIn(RequestModel):
    min: int
    max: int

    @model_validator(mode="after")
    def _ordered(self) -> RangeIn:
        if self.min > self.max:
            raise ValueError("The minimum cannot be larger than the maximum.")
        return self


class SentenceRange(RangeIn):
    min: int = Field(ge=1, le=10)
    max: int = Field(ge=1, le=10)


class WordRange(RangeIn):
    min: int = Field(ge=20, le=500)
    max: int = Field(ge=20, le=500)


ModelName = Annotated[
    str, StringConstraints(strip_whitespace=True, pattern=r"^[A-Za-z0-9._/-]{1,128}$")
]


class SettingsUpdate(RequestModel):
    """Any subset of the settings; only the fields sent are changed.

    ``credit_unit_allowance: null`` clears the allowance.
    """

    score_weights: WeightsIn | None = None
    similarity_threshold: float | None = Field(default=None, gt=0, lt=1)
    max_recommendations: int | None = Field(default=None, ge=1, le=100)
    passage_sentences: SentenceRange | None = None
    passage_words: WordRange | None = None
    sbert_model: ModelName | None = None
    spacy_model: ModelName | None = None
    min_topic_size: int | None = Field(default=None, ge=2, le=100)
    evidence_per_recommendation: int | None = Field(default=None, ge=1, le=20)
    max_documents_per_session: int | None = Field(default=None, ge=1, le=200)
    credit_unit_allowance: int | None = Field(default=None, ge=1, le=300)

    @model_validator(mode="after")
    def _something(self) -> SettingsUpdate:
        if not self.model_fields_set:
            raise ValueError("Send at least one setting to change.")
        nullable = {"credit_unit_allowance"}
        for key in self.model_fields_set - nullable:
            if getattr(self, key) is None:
                raise ValueError(f"{key} cannot be empty.")
        return self

    @field_validator("spacy_model")
    @classmethod
    def _installed(cls, name: str | None) -> str | None:
        """Only spaCy pipelines installed on the server can be used."""
        if name is None:
            return name
        from spacy.util import is_package

        if not is_package(name):
            raise ValueError(f"The spaCy pipeline '{name}' is not installed on the server.")
        return name

    def changes(self) -> dict[str, Any]:
        """The sent settings as JSON-ready values."""
        values = self.model_dump(mode="json", include=self.model_fields_set)
        return {key: values[key] for key in self.model_fields_set}


class SettingOut(BaseModel):
    key: str
    value: Any
    default: Any
    description: str
    updated_at: datetime | None
    updated_by: UserRef | None


# ------------------------------------------------------------------------ skill patterns

PatternToken = dict[str, Any]
CanonicalName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)
]
Phrase = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


def check_pattern(label: str, pattern: str | list[PatternToken]) -> None:
    """Raise ValueError unless spaCy's EntityRuler accepts the pattern."""
    from app.services.ner.skills import validate_pattern

    problem = validate_pattern(label, pattern)
    if problem:
        raise ValueError(problem)


class SkillPatternIn(RequestModel):
    """A phrase (matched case-insensitively) or a spaCy token pattern (1–10 token dicts)."""

    label: SkillLabel
    pattern: Phrase | Annotated[list[PatternToken], Field(min_length=1, max_length=10)]
    canonical_name: CanonicalName

    @field_validator("pattern")
    @classmethod
    def _valid_pattern(
        cls, pattern: str | list[PatternToken], info: ValidationInfo
    ) -> str | list[PatternToken]:
        label = info.data.get("label")  # validated first (field order)
        if label is not None:
            check_pattern(str(label), pattern)
        return pattern


class SkillPatternUpdate(RequestModel):
    label: SkillLabel | None = None
    pattern: Phrase | Annotated[list[PatternToken], Field(min_length=1, max_length=10)] | None = (
        None
    )
    canonical_name: CanonicalName | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def _something(self) -> SkillPatternUpdate:
        if not self.model_fields_set:
            raise ValueError("Send at least one field to change.")
        for key in self.model_fields_set:
            if getattr(self, key) is None:
                raise ValueError(f"{key} cannot be empty.")
        return self


class SkillPatternListQuery(PaginationQuery):
    label: SkillLabel | None = None
    is_active: bool | None = None
    search: str | None = Field(default=None, max_length=100)


class SkillPatternOut(ResponseModel):
    id: int
    label: SkillLabel
    pattern: str | list[PatternToken]
    canonical_name: str
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------- stop words

_WORD = re.compile(r"^[a-z0-9][a-z0-9+#.'\-]{0,63}$")


def _stop_word(value: str) -> str:
    word = value.strip().lower()
    if not _WORD.match(word):
        raise ValueError(
            "Enter a single word (letters, digits and + # . ' - only, up to 64 characters)."
        )
    return word


Word = Annotated[str, AfterValidator(_stop_word)]


class StopWordIn(RequestModel):
    word: Word


class StopWordUpdate(RequestModel):
    is_active: bool


class StopWordListQuery(PaginationQuery):
    is_active: bool | None = None
    search: str | None = Field(default=None, max_length=64)


class StopWordOut(ResponseModel):
    id: int
    word: str
    is_active: bool
    created_at: datetime


# ----------------------------------------------------------------------------- audit log


class AuditLogQuery(PaginationQuery):
    user_id: int | None = Field(default=None, ge=1)
    action: str | None = Field(default=None, max_length=64)
    entity_type: str | None = Field(default=None, max_length=64)
    date_from: date | None = None
    date_to: date | None = None

    @model_validator(mode="after")
    def _ordered(self) -> AuditLogQuery:
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("The start date must be on or before the end date.")
        return self


class AuditLogOut(BaseModel):
    id: int
    created_at: datetime
    user: UserRef | None
    action_type: str
    entity_type: str | None
    entity_id: str | None
    detail: dict[str, Any]
    ip_address: str | None
