"""NLP-Driven Curriculum Recommendation System (NLP-RS) backend.

``create_app`` is the application factory used by the dev server, Gunicorn, the RQ
worker and the test suite.
"""

from __future__ import annotations

import logging

from flask import Flask

from app.config import get_config
from app.extensions import db, init_redis, migrate
from app.routes import register_blueprints
from app.utils.errors import register_error_handlers


def configure_logging(level: str) -> None:
    """Send application logs to stderr with timestamps (collected by Docker)."""
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def create_app(config_name: str | None = None) -> Flask:
    """Build and configure a Flask application.

    Args:
        config_name: ``development``, ``testing`` or ``production``. Defaults to the
            ``APP_ENV`` environment variable.
    """
    config = get_config(config_name)
    app = Flask(__name__)
    app.config.from_object(config)
    app.json.sort_keys = False  # keep envelope fields in the order they are built
    configure_logging(app.config["LOG_LEVEL"])

    db.init_app(app)
    migrate.init_app(app, db)
    init_redis(app)

    register_blueprints(app)
    register_error_handlers(app)
    return app
