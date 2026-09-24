"""Application configuration.

One class per environment. The active class is chosen by the ``APP_ENV`` environment
variable (``development`` | ``testing`` | ``production``). Secrets are only ever read from
the environment; nothing sensitive has a usable default in production.
"""

from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


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

    STORAGE_DIR: str = _env("STORAGE_DIR", str(BACKEND_DIR / "storage")) or ""

    # Upper bound for a whole multipart request. The per-file limit (25 MB) is enforced
    # separately during upload validation.
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024

    TESTING = False
    DEBUG = False


class DevelopmentConfig(BaseConfig):
    """Local development: debug on, a fixed insecure key allowed."""

    DEBUG = True
    SECRET_KEY = _env("SECRET_KEY", "dev-insecure-secret-key")


class TestingConfig(BaseConfig):
    """Automated tests: isolated database, no external services required."""

    TESTING = True
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = _env("TEST_DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_ENGINE_OPTIONS: dict = {}
    REDIS_URL = _env("TEST_REDIS_URL", "redis://localhost:6379/15") or ""


class ProductionConfig(BaseConfig):
    """Production: every secret must come from the environment."""

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
