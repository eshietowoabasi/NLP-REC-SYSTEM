"""Programme schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import StringConstraints

from app.schemas.common import RequestModel, ResponseModel


class ProgrammeCreate(RequestModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=160)]
    discipline_code: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=32)] | None
    ) = None
    faculty: Annotated[str, StringConstraints(strip_whitespace=True, max_length=160)] | None = None
    description: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None
    ) = None
    country: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)
    ] = "Nigeria"


class ProgrammeUpdate(RequestModel):
    """Any subset of a programme's details; ``is_active: false`` retires it."""

    name: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=160)]
        | None
    ) = None
    discipline_code: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=32)] | None
    ) = None
    faculty: Annotated[str, StringConstraints(strip_whitespace=True, max_length=160)] | None = None
    description: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None
    ) = None
    is_active: bool | None = None


class ProgrammeListQuery(RequestModel):
    # Retired programmes are listed only on request (admin management screen).
    include_inactive: bool = False


class ProgrammeOut(ResponseModel):
    id: int
    name: str
    discipline_code: str | None
    faculty: str | None
    description: str | None
    country: str
    is_active: bool
    created_at: datetime


class ProgrammeRef(ResponseModel):
    id: int
    name: str
    discipline_code: str | None
