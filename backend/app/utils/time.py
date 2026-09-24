"""Time helpers. All timestamps are timezone-aware and in UTC."""

from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Current time as an aware UTC datetime."""
    return datetime.now(UTC)
