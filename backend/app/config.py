"""Environment-specific configuration.

Secrets and connection strings come from environment variables (spec §14);
nothing sensitive is hard-coded here.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg2://nlprs:nlprs@localhost:5432/nlprs"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploads (spec §7.2)
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(PROJECT_ROOT / "data" / "raw"))
    MAX_DOCUMENT_BYTES = 25 * 1024 * 1024
    MAX_CONTENT_LENGTH = MAX_DOCUMENT_BYTES + 1024 * 1024  # allow form overhead
    MAX_DOCUMENTS_PER_SESSION = 50
    ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

    # Session cookie auth (see docs/DECISIONS.md, D2)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_HTTPONLY = True

    BCRYPT_ROUNDS = 12


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")
    BCRYPT_ROUNDS = 4  # fast hashing in tests


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True

    @classmethod
    def validate(cls):
        if not os.environ.get("SECRET_KEY"):
            raise RuntimeError("SECRET_KEY must be set in production")
        if not os.environ.get("DATABASE_URL"):
            raise RuntimeError("DATABASE_URL must be set in production")


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
