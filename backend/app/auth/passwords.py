"""Password hashing with bcrypt."""

from __future__ import annotations

from functools import cache

import bcrypt
from flask import current_app, has_app_context

MIN_PASSWORD_LENGTH = 8
# bcrypt only uses the first 72 bytes of a password; longer ones are rejected, not truncated.
MAX_PASSWORD_BYTES = 72
DEFAULT_ROUNDS = 12


def _rounds() -> int:
    """The configured bcrypt cost (``BCRYPT_ROUNDS``)."""
    return current_app.config["BCRYPT_ROUNDS"] if has_app_context() else DEFAULT_ROUNDS


@cache
def _dummy_hash(rounds: int) -> bytes:
    """Hash checked when a login names an unknown user, so the response time does not reveal
    whether the account exists. It uses the same cost as real hashes."""
    return bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt(rounds))


def password_problem(password: str) -> str | None:
    """Return why ``password`` is unacceptable, or None if it is fine."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return f"Password must be at most {MAX_PASSWORD_BYTES} bytes."
    return None


def hash_password(password: str) -> str:
    """Return a bcrypt hash of ``password`` using the configured cost."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(_rounds())).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    """Check ``password`` against ``password_hash`` in constant time.

    With ``password_hash=None`` (unknown user) a dummy hash is checked so the call takes
    as long as a real check, then False is returned.
    """
    candidate = password.encode("utf-8")
    if len(candidate) > MAX_PASSWORD_BYTES:
        return False
    if password_hash is None:
        bcrypt.checkpw(candidate, _dummy_hash(_rounds()))
        return False
    return bcrypt.checkpw(candidate, password_hash.encode())
