"""Health endpoint used by the frontend status indicator, Docker and monitoring."""

from __future__ import annotations

import logging

from flask import Blueprint, Response, current_app
from sqlalchemy import text

from app.extensions import db, get_redis
from app.utils.responses import error, success

logger = logging.getLogger(__name__)

bp = Blueprint("health", __name__)


def check_database() -> bool:
    """Return True if the database answers a trivial query."""
    try:
        db.session.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.warning("Health check: database unreachable", exc_info=True)
        db.session.rollback()
        return False


def check_redis() -> bool:
    """Return True if Redis answers PING."""
    try:
        return bool(get_redis().ping())
    except Exception:
        logger.warning("Health check: redis unreachable", exc_info=True)
        return False


@bp.get("/health")
def health() -> tuple[Response, int]:
    """Report API liveness and the reachability of Postgres and Redis.

    Returns 200 when every dependency is reachable, otherwise 503 with the per-service
    results in ``error.details.checks``.
    """
    checks = {
        "database": "ok" if check_database() else "unavailable",
        "redis": "ok" if check_redis() else "unavailable",
    }
    if all(state == "ok" for state in checks.values()):
        return success(
            {
                "status": "ok",
                "version": current_app.config["APP_VERSION"],
                "checks": checks,
            }
        )
    return error(
        "SERVICE_UNAVAILABLE",
        "One or more backend services are unavailable.",
        503,
        {"version": current_app.config["APP_VERSION"], "checks": checks},
    )
