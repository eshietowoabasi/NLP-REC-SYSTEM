"""HTTP routes. Every blueprint is mounted under ``/api``."""

from __future__ import annotations

from flask import Flask

from app.routes import admin, auth, documents, health, nuc_core, sessions

API_PREFIX = "/api"


def register_blueprints(app: Flask) -> None:
    """Mount all API blueprints on ``app``."""
    for module in (health, auth, admin, documents, nuc_core, sessions):
        app.register_blueprint(module.bp, url_prefix=API_PREFIX + (module.bp.url_prefix or ""))
