"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.extensions import db


class FakeRedis:
    """Stand-in for the Redis client so tests do not need a running Redis server."""

    def __init__(self, reachable: bool = True) -> None:
        self.reachable = reachable

    def ping(self) -> bool:
        if not self.reachable:
            raise ConnectionError("redis unreachable")
        return True


@pytest.fixture
def app() -> Iterator[Flask]:
    application = create_app("testing")
    application.extensions["redis"] = FakeRedis()
    with application.app_context():
        yield application
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()
