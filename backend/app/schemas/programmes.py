"""Programme schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import StringConstraints

from app.schemas.common import RequestModel, ResponseModel


class ProgrammeCreate(RequestModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=160)]
    discipline_code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=32)] | None = None
    faculty: Annotated[str, StringConstraints(strip_whitespace=True, max_length=160)] | None = None
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None
    country: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)] = "Nigeria"


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
