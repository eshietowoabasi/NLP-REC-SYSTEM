"""NLP-Driven Curriculum Recommendation System (NLP-RS) backend.

``create_app`` is the application factory used by the dev server, Gunicorn, the RQ
worker and the test suite.
"""

from __future__ import annotations

import logging

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from app import models  # noqa: F401  (registers every table for Flask-Migrate)
from app.auth.session import init_login_manager
from app.cli import register_cli
from app.config import BACKEND_DIR, get_config
from app.extensions import csrf, db, init_redis, migrate
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

    if app.config["PROXY_COUNT"] > 0:
        count = app.config["PROXY_COUNT"]
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=count, x_proto=count, x_host=count)

    db.init_app(app)
    migrate.init_app(app, db, directory=str(BACKEND_DIR / "migrations"))
    csrf.init_app(app)
    init_login_manager(app)
    init_redis(app)

    register_blueprints(app)
    register_error_handlers(app)
    register_cli(app)
    return app
