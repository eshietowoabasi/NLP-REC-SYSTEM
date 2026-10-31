"""Validation models for labour-market harvesting."""

from pydantic import BaseModel, Field, field_validator


class HarvestProfileUpdate(BaseModel):
    search_terms: list[str] = Field(
        default_factory=list,
        max_length=40,
    )

    field_slugs: list[str] = Field(
        default_factory=list,
        max_length=20,
    )

    @field_validator(
        "search_terms",
        "field_slugs",
        mode="before",
    )
    @classmethod
    def clean_list(cls, value):
        if value is None:
            return []

        if not isinstance(value, list):
            return value

        cleaned = []

        for item in value:
            text = str(item).strip().lower()

            if text and text not in cleaned:
                cleaned.append(text)

        return cleaned


class HarvestRunRequest(BaseModel):
    target_count: int = Field(
        default=10,
        ge=1,
        le=30,
    )

    pages_per_field: int = Field(
        default=2,
        ge=1,
        le=5,
    )
