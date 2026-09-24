"""Tests for GET /api/health."""

from __future__ import annotations

import json

from flask import Flask
from flask.testing import FlaskClient

from app.routes import health
from tests.conftest import FakeRedis


def test_health_ok_when_all_services_reachable(client: FlaskClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert body["data"]["checks"] == {"database": "ok", "redis": "ok"}
    assert body["data"]["version"]
    # Envelope fields keep their natural order rather than being sorted alphabetically.
    assert list(json.loads(response.data)) == ["success", "data"]


def test_health_503_when_redis_unreachable(app: Flask, client: FlaskClient) -> None:
    app.extensions["redis"] = FakeRedis(reachable=False)

    response = client.get("/api/health")

    assert response.status_code == 503
    body = response.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert body["error"]["details"]["checks"] == {"database": "ok", "redis": "unavailable"}


def test_health_503_when_database_unreachable(client: FlaskClient, monkeypatch) -> None:
    # Patch only for this request, so the test database can still be cleaned up afterwards.
    with monkeypatch.context() as patch:
        patch.setattr(health.db.session, "execute", _raise_operational_error)
        response = client.get("/api/health")

    assert response.status_code == 503
    assert response.get_json()["error"]["details"]["checks"]["database"] == "unavailable"


def _raise_operational_error(*_args, **_kwargs):
    raise RuntimeError("database down")
