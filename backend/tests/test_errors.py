"""Tests that every error reaches the client in the standard JSON envelope."""

from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

from app.utils.errors import ApiError


def test_unknown_route_returns_404_envelope(client: FlaskClient) -> None:
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    body = response.get_json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["details"] == {}


def test_wrong_method_returns_405_envelope(client: FlaskClient) -> None:
    response = client.post("/api/health")

    assert response.status_code == 405
    assert response.get_json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_api_error_is_rendered_with_its_code_and_details(app: Flask) -> None:
    @app.get("/api/_raise-api-error")
    def _raise() -> None:
        raise ApiError("CONFLICT", "Document is in use.", 409, {"sessions": [1]})

    response = app.test_client().get("/api/_raise-api-error")

    assert response.status_code == 409
    assert response.get_json()["error"] == {
        "code": "CONFLICT",
        "message": "Document is in use.",
        "details": {"sessions": [1]},
    }


def test_unexpected_error_hides_internal_details(app: Flask) -> None:
    @app.get("/api/_raise-unexpected")
    def _raise() -> None:
        raise ValueError("secret internal detail")

    response = app.test_client().get("/api/_raise-unexpected")

    assert response.status_code == 500
    error = response.get_json()["error"]
    assert error["code"] == "INTERNAL_ERROR"
    assert "secret" not in error["message"]
