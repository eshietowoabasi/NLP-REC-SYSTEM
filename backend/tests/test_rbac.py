"""Role-based access control is enforced on the server for every protected route."""

from __future__ import annotations

import pytest
from flask import Flask

from app.auth.decorators import EDITOR_ROLES, login_required, role_required
from app.utils.responses import success
from tests.conftest import ApiClient

# Every admin endpoint that exists so far: (method, url, json body).
ADMIN_ENDPOINTS = [
    ("GET", "/api/admin/users", None),
    ("POST", "/api/admin/users", {}),
    ("PATCH", "/api/admin/users/1", {}),
]


@pytest.mark.parametrize(("method", "url", "body"), ADMIN_ENDPOINTS)
def test_admin_endpoints_require_login(api: ApiClient, method: str, url: str, body) -> None:
    response = api.request(method, url, json=body)

    assert response.status_code == 401


@pytest.mark.parametrize("role", ["planner", "viewer"])
@pytest.mark.parametrize(("method", "url", "body"), ADMIN_ENDPOINTS)
def test_admin_endpoints_forbid_non_admins(
    login_as, role: str, method: str, url: str, body
) -> None:
    client = login_as(role)

    response = client.request(method, url, json=body)

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "FORBIDDEN"


def test_admin_can_reach_admin_endpoints(login_as) -> None:
    client = login_as("admin")

    assert client.get("/api/admin/users").status_code == 200


@pytest.fixture
def guarded_app(app: Flask) -> Flask:
    """Test-only routes exercising the decorators with each role combination."""

    @app.post("/api/_test/editors-only")
    @role_required(*EDITOR_ROLES)
    def editors_only():
        return success({"ok": True})

    @app.get("/api/_test/any-user")
    @login_required
    def any_user():
        return success({"ok": True})

    return app


@pytest.mark.parametrize(("role", "expected"), [("admin", 200), ("planner", 200), ("viewer", 403)])
def test_viewer_cannot_use_write_routes(guarded_app, login_as, role: str, expected: int) -> None:
    client = login_as(role)

    assert client.post("/api/_test/editors-only", json={}).status_code == expected


@pytest.mark.parametrize("role", ["admin", "planner", "viewer"])
def test_every_role_can_use_read_routes(guarded_app, login_as, role: str) -> None:
    assert login_as(role).get("/api/_test/any-user").status_code == 200


def test_login_required_rejects_anonymous(guarded_app, api: ApiClient) -> None:
    assert api.get("/api/_test/any-user").status_code == 401


def test_role_required_needs_at_least_one_role() -> None:
    with pytest.raises(ValueError):
        role_required()
