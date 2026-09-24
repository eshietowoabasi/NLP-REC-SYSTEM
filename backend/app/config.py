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
    # Check pooled connections before use so a database restart or failover does not
    # surface as errors on the first requests afterwards.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Uploads (spec §7.2)
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(PROJECT_ROOT / "data" / "raw"))
    MAX_DOCUMENT_BYTES = 25 * 1024 * 1024
    MAX_CONTENT_LENGTH = MAX_DOCUMENT_BYTES + 1024 * 1024  # allow form overhead
    MAX_DOCUMENTS_PER_SESSION = 50
    REPORT_FOLDER = os.environ.get("REPORT_FOLDER", str(PROJECT_ROOT / "reports"))
    INSTITUTION_NAME = os.environ.get(
        "INSTITUTION_NAME", "Department of Computer Science, Faculty of Computing, University of Uyo"
    )
    ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

    # Session cookie auth (see docs/DECISIONS.md, D2)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_HTTPONLY = True

    BCRYPT_ROUNDS = 12

    # NLP pipeline (docs/DECISIONS.md, D1)
    SPACY_MODEL = os.environ.get("SPACY_MODEL", "en_core_web_sm")
    EMBEDDING_BACKEND = os.environ.get("EMBEDDING_BACKEND", "sbert")  # sbert | hashing
    SBERT_MODEL = os.environ.get("SBERT_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    TFIDF_TOP_N = 25
    TFIDF_CORPUS_TOP_N = 50

    # Background jobs (docs/DECISIONS.md, D3)
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    CELERY = {
        "broker_url": REDIS_URL,
        "task_ignore_result": True,
        "task_acks_late": True,
        "worker_prefetch_multiplier": 1,
        "broker_connection_retry_on_startup": True,
    }


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")
    BCRYPT_ROUNDS = 4  # fast hashing in tests
    EMBEDDING_BACKEND = "hashing"  # no model downloads in tests
    # Run jobs inline so tests exercise the whole pipeline without Redis.
    CELERY = {"task_always_eager": True, "task_ignore_result": True}


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
