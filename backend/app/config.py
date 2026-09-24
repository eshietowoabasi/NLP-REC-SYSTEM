"""Application configuration.

One class per environment. The active class is chosen by the ``APP_ENV`` environment
variable (``development`` | ``testing`` | ``production``). Secrets are only ever read from
the environment; nothing sensitive has a usable default in production.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from flask.cli import load_dotenv
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parent.parent

# The settings below are read from the environment when this module is imported, so the
# repository .env must be loaded first. This makes every entry point (flask CLI, the RQ worker,
# Gunicorn, tests) see the same values. Variables already set (e.g. by Docker) take precedence,
# and without a .env file (as in the Docker images) this does nothing.
load_dotenv()


def _env(name: str, default: str | None = None) -> str | None:
    """Return an environment variable, treating an empty string as unset."""
    value = os.environ.get(name)
    return value if value not in (None, "") else default


class BaseConfig:
    """Settings shared by every environment."""

    APP_NAME = "NLP-RS"
    APP_VERSION = "0.1.0"

    SECRET_KEY: str | None = _env("SECRET_KEY")
    LOG_LEVEL: str = _env("LOG_LEVEL", "INFO") or "INFO"

    SQLALCHEMY_DATABASE_URI: str | None = _env(
        "DATABASE_URL", "postgresql+psycopg://nlprs:nlprs@localhost:5432/nlprs"
    )
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REDIS_URL: str = _env("REDIS_URL", "redis://localhost:6379/0") or ""
    RQ_QUEUE_NAME = "default"
    JOB_TIMEOUT_SECONDS = 900
    # Verify outgoing HTTPS (model downloads) against the OS certificate store; see utils/tls.py.
    USE_SYSTEM_CERTS = (_env("USE_SYSTEM_CERTS", "false") or "").lower() == "true"
    # Run background jobs synchronously instead of through Redis (tests only).
    TASKS_EAGER = False

    STORAGE_DIR: str = _env("STORAGE_DIR", str(BACKEND_DIR / "storage")) or ""

    # Upper bound for a whole multipart request. The per-file limit (25 MB) is enforced
    # separately during upload validation.
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024

    # Session cookie (Flask-Login stores the user's session token in it).
    SESSION_COOKIE_NAME = "nlprs_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # CSRF: token valid for the whole session, sent in the X-CSRFToken header.
    WTF_CSRF_TIME_LIMIT = None
    WTF_CSRF_HEADERS = ["X-CSRFToken"]

    BCRYPT_ROUNDS = 12

    # Number of reverse proxies (Nginx) in front of Flask whose X-Forwarded-* headers are
    # trusted, so audit logs record the client IP rather than the proxy's.
    PROXY_COUNT = int(_env("PROXY_COUNT", "1") or "1")

    TESTING = False
    DEBUG = False


class DevelopmentConfig(BaseConfig):
    """Local development: debug on, a fixed insecure key allowed."""

    DEBUG = True
    SECRET_KEY = _env("SECRET_KEY", "dev-insecure-secret-key")


def resolve_test_database_url() -> str:
    """URL of the test database: ``TEST_DATABASE_URL``, else the dev database name + ``_test``.

    The test database lives on the same PostgreSQL server as the development database but is
    a separate database, so tests never read or modify development data.
    """
    explicit = _env("TEST_DATABASE_URL")
    if explicit:
        return explicit
    base = make_url(BaseConfig.SQLALCHEMY_DATABASE_URI or "")
    return base.set(database=f"{base.database}_test").render_as_string(hide_password=False)


class TestingConfig(BaseConfig):
    """Automated tests: a dedicated ``*_test`` PostgreSQL database and Redis DB 15."""

    TESTING = True
    SECRET_KEY = "test-secret-key"
    BCRYPT_ROUNDS = 4  # fast hashing; the algorithm is the same
    TASKS_EAGER = True
    SQLALCHEMY_DATABASE_URI = resolve_test_database_url()
    # Same Redis server as development, but logical database 15.
    REDIS_URL = _env("TEST_REDIS_URL") or BaseConfig.REDIS_URL.rsplit("/", 1)[0] + "/15"


class ProductionConfig(BaseConfig):
    """Production: every secret must come from the environment; cookies only over HTTPS."""

    SESSION_COOKIE_SECURE = True

    @classmethod
    def validate(cls) -> None:
        """Refuse to start with missing or placeholder secrets."""
        missing = [name for name in ("SECRET_KEY", "DATABASE_URL", "REDIS_URL") if not _env(name)]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
        secret = _env("SECRET_KEY") or ""
        if len(secret) < 32 or secret.startswith("change-me"):
            raise RuntimeError("SECRET_KEY must be a random string of at least 32 characters.")


CONFIGS: dict[str, type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None = None) -> type[BaseConfig]:
    """Resolve a config class from an explicit name or the ``APP_ENV`` variable."""
    key = (name or _env("APP_ENV", "development") or "development").lower()
    try:
        config = CONFIGS[key]
    except KeyError as exc:
        raise RuntimeError(
            f"Unknown APP_ENV '{key}'. Expected one of: {', '.join(CONFIGS)}."
        ) from exc
    if config is ProductionConfig:
        ProductionConfig.validate()
    return config
