"""Shared pytest fixtures.

Tests that need the application run against a dedicated PostgreSQL database (the development
database name + ``_test``, e.g. ``nlprs_test``) on the same server. It is created automatically
if it does not exist. As a safeguard, the suite refuses to run against any database whose name
does not end in ``_test``.
"""

from __future__ import annotations

from collections.abc import Iterator

# Load the repository .env (as the flask CLI does) before app.config reads the environment.
from flask.cli import load_dotenv

load_dotenv()

import pytest  # noqa: E402
from flask import Flask  # noqa: E402
from flask.testing import FlaskClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

from app import create_app  # noqa: E402
from app.config import TestingConfig  # noqa: E402
from app.extensions import db  # noqa: E402


class FakeRedis:
    """Stand-in for the Redis client so tests do not need a running Redis server."""

    def __init__(self, reachable: bool = True) -> None:
        self.reachable = reachable

    def ping(self) -> bool:
        if not self.reachable:
            raise ConnectionError("redis unreachable")
        return True


def ensure_test_database(url: str) -> None:
    """Create the test database if it is missing; refuse anything not named ``*_test``."""
    target = make_url(url)
    if not (target.database or "").endswith("_test"):
        pytest.exit(
            f"Refusing to run tests against database '{target.database}': "
            "the test database name must end in '_test'.",
            returncode=2,
        )
    admin_engine = create_engine(target.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            exists = conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": target.database},
            )
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{target.database}"'))
    except OperationalError as exc:
        pytest.exit(
            f"Cannot connect to PostgreSQL at {target.host}:{target.port} ({exc.orig}). "
            "Start it with: docker compose -f docker-compose.services.yml up -d",
            returncode=3,
        )
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session")
def _test_database() -> str:
    url = TestingConfig.SQLALCHEMY_DATABASE_URI or ""
    ensure_test_database(url)
    return url


@pytest.fixture
def app(_test_database: str) -> Iterator[Flask]:
    application = create_app("testing")
    application.extensions["redis"] = FakeRedis()
    with application.app_context():
        yield application
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()
