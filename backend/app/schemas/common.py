"""Schemas and field types shared across the API."""

from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.auth.passwords import password_problem
from app.utils.validation import DEFAULT_PER_PAGE, MAX_PER_PAGE


class RequestModel(BaseModel):
    """Base for request bodies: unknown fields are rejected, strings are trimmed."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ResponseModel(BaseModel):
    """Base for responses built from ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class PaginationQuery(BaseModel):
    """``?page=&per_page=`` for list endpoints."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=DEFAULT_PER_PAGE, ge=1, le=MAX_PER_PAGE)


def _check_password(value: str) -> str:
    problem = password_problem(value)
    if problem:
        raise ValueError(problem)
    return value


# A new password: at least 8 characters, at most 72 bytes (the bcrypt limit).
NewPassword = Annotated[str, AfterValidator(_check_password)]
