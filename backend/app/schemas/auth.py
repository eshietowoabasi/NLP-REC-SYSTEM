"""Authentication request bodies."""

from __future__ import annotations

from pydantic import Field, model_validator

from app.schemas.common import NewPassword, RequestModel


class LoginRequest(RequestModel):
    """Log in with a username or an email address."""

    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordRequest(RequestModel):
    """Change one's own password; the current password must be supplied."""

    current_password: str = Field(min_length=1, max_length=256)
    new_password: NewPassword

    @model_validator(mode="after")
    def _differs(self) -> ChangePasswordRequest:
        if self.new_password == self.current_password:
            raise ValueError("The new password must be different from the current one.")
        return self
