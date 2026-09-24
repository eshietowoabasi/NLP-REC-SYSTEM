"""Shared pytest fixtures.

Tests that need the application run against a dedicated PostgreSQL database (the development
database name + ``_test``, e.g. ``nlprs_test``) on the same server. It is created automatically
if it does not exist, rebuilt from the Alembic migrations at the start of every test run, and
emptied after each test. As a safeguard, the suite refuses to run against any database whose
name does not end in ``_test``.

All users and data created here are synthetic test fixtures.
"""

from __future__ import annotations

import zlib
from collections.abc import Callable, Iterator
from typing import Any

# Load the repository .env (as the flask CLI does) before app.config reads the environment.
from flask.cli import load_dotenv

load_dotenv()

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from flask import Flask  # noqa: E402
from flask.testing import FlaskClient  # noqa: E402
from flask_migrate import upgrade  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from werkzeug.test import TestResponse  # noqa: E402

from app import create_app  # noqa: E402
from app.auth.passwords import hash_password  # noqa: E402
from app.config import TestingConfig  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import User, UserRole  # noqa: E402

TEST_PASSWORD = "Test-password-123"


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


def reset_schema(app: Flask) -> None:
    """Drop everything in the test database and rebuild it with the Alembic migrations."""
    with app.app_context():
        with db.engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
        upgrade()
        db.engine.dispose()


def empty_all_tables() -> None:
    """Delete every row from the application tables (keeps the schema and Alembic version).

    DELETE in reverse dependency order is much faster than TRUNCATE for tables this small.
    """
    for table in reversed(db.metadata.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()


@pytest.fixture(scope="session")
def _test_database() -> str:
    url = TestingConfig.SQLALCHEMY_DATABASE_URI or ""
    ensure_test_database(url)
    reset_schema(create_app("testing"))
    return url


class FakeEncoder:
    """Deterministic stand-in for the SBERT model: a hashed bag of words, L2-normalised.

    Texts sharing words get similar vectors, which is enough to test storage and similarity
    plumbing without loading a 90 MB model in every test.
    """

    model_name = "test-fake-encoder"
    dimension = 32

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = np.zeros((len(texts), self.dimension), dtype=np.float32)
        for row, sample in enumerate(texts):
            for word in sample.lower().split():
                vectors[row, zlib.crc32(word.encode()) % self.dimension] += 1.0
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.where(norms == 0, 1, norms)


@pytest.fixture(autouse=True)
def fake_encoder(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Use FakeEncoder everywhere except in tests marked ``real_models``."""
    if "real_models" in request.keywords:
        return
    monkeypatch.setattr("app.tasks.ingestion.get_encoder", lambda _name: FakeEncoder())


@pytest.fixture
def app(_test_database: str, tmp_path) -> Iterator[Flask]:
    application = create_app("testing")
    application.extensions["redis"] = FakeRedis()
    application.config["STORAGE_DIR"] = str(tmp_path / "storage")
    with application.app_context():
        yield application
        db.session.rollback()
        empty_all_tables()
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


class ApiClient:
    """Test client that behaves like the frontend: keeps the cookie jar and CSRF token.

    State-changing requests carry the ``X-CSRFToken`` header unless ``csrf=False``.
    """

    def __init__(self, client: FlaskClient) -> None:
        self.client = client
        self.csrf_token: str | None = None

    def refresh_csrf(self) -> str:
        response = self.get("/api/auth/csrf")
        token: str = response.get_json()["data"]["csrf_token"]
        self.csrf_token = token
        return token

    def request(self, method: str, url: str, *, csrf: bool = True, **kwargs: Any) -> TestResponse:
        headers = dict(kwargs.pop("headers", {}) or {})
        if csrf and method.upper() not in ("GET", "HEAD", "OPTIONS"):
            headers["X-CSRFToken"] = self.csrf_token or self.refresh_csrf()
        # A fresh app context per request, as in production. Otherwise the test's own app
        # context would be reused and `g` (logged-in user, cached CSRF token) would leak
        # between requests and between clients.
        with self.client.application.app_context():
            response = self.client.open(url, method=method.upper(), headers=headers, **kwargs)
        body = response.get_json(silent=True)
        data = body.get("data") if isinstance(body, dict) else None
        if isinstance(data, dict) and "csrf_token" in data:
            self.csrf_token = data["csrf_token"]
        return response

    def get(self, url: str, **kwargs: Any) -> TestResponse:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> TestResponse:
        return self.request("POST", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> TestResponse:
        return self.request("PATCH", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> TestResponse:
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> TestResponse:
        return self.request("DELETE", url, **kwargs)

    def login(self, identifier: str, password: str = TEST_PASSWORD) -> TestResponse:
        return self.post("/api/auth/login", json={"identifier": identifier, "password": password})


@pytest.fixture
def api(app: Flask) -> ApiClient:
    """An anonymous API client."""
    return ApiClient(app.test_client())


@pytest.fixture
def make_user(app: Flask) -> Callable[..., User]:
    """Factory for synthetic users: ``make_user("planner", username="p1")``."""

    def _make(
        role: UserRole | str = UserRole.VIEWER,
        *,
        username: str | None = None,
        password: str = TEST_PASSWORD,
        is_active: bool = True,
        **fields: Any,
    ) -> User:
        role = UserRole(role)
        username = username or f"test-{role.value}-{db.session.query(User).count() + 1}"
        user = User(
            username=username,
            email=fields.pop("email", f"{username}@example.com"),
            full_name=fields.pop("full_name", f"Test {role.value.title()}"),
            role=role,
            is_active=is_active,
            password_hash=hash_password(password),
            **fields,
        )
        db.session.add(user)
        db.session.commit()
        return user

    return _make


@pytest.fixture
def login_as(app: Flask, make_user: Callable[..., User]) -> Callable[..., ApiClient]:
    """Return a logged-in ApiClient for a new user with ``role``."""

    def _login(role: UserRole | str, **user_fields: Any) -> ApiClient:
        user = make_user(role, **user_fields)
        client = ApiClient(app.test_client())
        response = client.login(user.username)
        assert response.status_code == 200, response.get_json()
        client.user = user  # type: ignore[attr-defined]
        return client

    return _login
