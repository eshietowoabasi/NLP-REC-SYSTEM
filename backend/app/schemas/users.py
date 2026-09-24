"""User schemas (profile and admin user management)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, EmailStr, Field, StringConstraints

from app.models.enums import UserRole
from app.schemas.common import NewPassword, PaginationQuery, RequestModel, ResponseModel


def _lower(value: str) -> str:
    return value.lower()


Username = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=3, max_length=64, pattern=r"^[A-Za-z0-9._-]+$"
    ),
    AfterValidator(_lower),
]
Email = Annotated[EmailStr, AfterValidator(_lower)]
FullName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]


class UserOut(ResponseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class UserCreate(RequestModel):
    username: Username
    email: Email
    full_name: FullName
    role: UserRole
    password: NewPassword


class UserUpdate(RequestModel):
    """Admin changes to a user. Every field is optional; only supplied fields change."""

    full_name: FullName | None = None
    email: Email | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    new_password: NewPassword | None = Field(
        default=None, description="Reset the user's password to this value."
    )


class UserListQuery(PaginationQuery):
    role: UserRole | None = None
    is_active: Literal["true", "false"] | None = None
    search: str | None = Field(default=None, max_length=100)
