"""HTTP routes. Every blueprint is mounted under ``/api``."""

from __future__ import annotations

from flask import Flask

from app.routes import health

API_PREFIX = "/api"


def register_blueprints(app: Flask) -> None:
    """Mount all API blueprints on ``app``."""
    app.register_blueprint(health.bp, url_prefix=API_PREFIX)
