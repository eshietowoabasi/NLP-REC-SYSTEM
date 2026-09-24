"""Tests for /api/auth: login, logout, current user, CSRF and password changes."""

from __future__ import annotations

from sqlalchemy import select

from app.extensions import db
from app.models import AuditLog, User
from tests.conftest import TEST_PASSWORD, ApiClient


def audit_actions() -> list[str]:
    return list(db.session.scalars(select(AuditLog.action_type).order_by(AuditLog.id)))


# --------------------------------------------------------------------------- CSRF


def test_csrf_endpoint_returns_a_token(api: ApiClient) -> None:
    response = api.get("/api/auth/csrf")

    assert response.status_code == 200
    assert len(response.get_json()["data"]["csrf_token"]) > 20


def test_state_changing_request_without_csrf_token_is_rejected(api: ApiClient, make_user) -> None:
    user = make_user("planner")

    response = api.post(
        "/api/auth/login",
        json={"identifier": user.username, "password": TEST_PASSWORD},
        csrf=False,
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "CSRF_FAILED"


def test_request_with_forged_csrf_token_is_rejected(api: ApiClient, make_user) -> None:
    user = make_user("planner")

    response = api.post(
        "/api/auth/login",
        json={"identifier": user.username, "password": TEST_PASSWORD},
        csrf=False,
        headers={"X-CSRFToken": "forged-token"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "CSRF_FAILED"


# -------------------------------------------------------------------------- login


def test_login_with_username_returns_user_and_new_csrf_token(api: ApiClient, make_user) -> None:
    user = make_user("planner", username="ada")
    old_token = api.refresh_csrf()

    response = api.login("ada")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["user"]["username"] == "ada"
    assert data["user"]["role"] == "planner"
    assert "password_hash" not in data["user"]
    assert "session_token" not in data["user"]
    assert data["csrf_token"] and data["csrf_token"] != old_token
    db.session.refresh(user)
    assert user.last_login_at is not None
    assert audit_actions() == ["auth.login"]


def test_login_with_email_is_case_insensitive(api: ApiClient, make_user) -> None:
    make_user("viewer", username="grace", email="grace@example.com")

    response = api.login("  GRACE@Example.COM ")

    assert response.status_code == 200


def test_session_cookie_is_httponly_and_samesite_lax(api: ApiClient, make_user) -> None:
    user = make_user("viewer")

    response = api.login(user.username)

    cookie = next(c for c in response.headers.getlist("Set-Cookie") if "nlprs_session=" in c)
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_wrong_password_and_unknown_user_get_the_same_answer(api: ApiClient, make_user) -> None:
    user = make_user("planner")

    wrong_password = api.login(user.username, "Wrong-password-1")
    unknown_user = api.login("nobody", "Wrong-password-1")

    for response in (wrong_password, unknown_user):
        assert response.status_code == 401
        assert response.get_json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert (
        wrong_password.get_json()["error"]["message"] == unknown_user.get_json()["error"]["message"]
    )
    assert audit_actions() == ["auth.login_failed", "auth.login_failed"]


def test_failed_login_audit_records_identifier_but_not_password(api: ApiClient) -> None:
    api.login("someone", "Secret-guess-99")

    entry = db.session.scalars(select(AuditLog)).one()
    assert entry.detail["identifier"] == "someone"
    assert "Secret-guess-99" not in str(entry.detail)


def test_deactivated_user_cannot_log_in(api: ApiClient, make_user) -> None:
    user = make_user("planner", is_active=False)

    response = api.login(user.username)

    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "ACCOUNT_DEACTIVATED"


def test_login_validation_error_lists_fields(api: ApiClient) -> None:
    response = api.post("/api/auth/login", json={"identifier": ""})

    assert response.status_code == 422
    fields = response.get_json()["error"]["details"]["fields"]
    assert set(fields) == {"identifier", "password"}


def test_login_rejects_non_json_body(api: ApiClient) -> None:
    response = api.post("/api/auth/login", data="not json", content_type="text/plain")

    assert response.status_code == 400


# ---------------------------------------------------------------------- me/logout


def test_me_requires_login(api: ApiClient) -> None:
    response = api.get("/api/auth/me")

    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "UNAUTHORIZED"


def test_me_returns_the_logged_in_user(login_as) -> None:
    client = login_as("viewer", username="viv")

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.get_json()["data"]["username"] == "viv"


def test_logout_ends_the_session(login_as) -> None:
    client = login_as("planner")

    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert response.get_json()["data"]["csrf_token"]
    assert client.get("/api/auth/me").status_code == 401
    assert audit_actions()[-1] == "auth.logout"


def test_deactivating_a_user_ends_their_existing_session(login_as) -> None:
    client = login_as("planner")
    user = db.session.get(User, client.user.id)
    user.is_active = False
    db.session.commit()

    assert client.get("/api/auth/me").status_code == 401


# ------------------------------------------------------------------ change password


def test_change_password_success(app, login_as) -> None:
    client = login_as("planner", username="pat")
    other_device = ApiClient(app.test_client())
    assert other_device.login("pat").status_code == 200

    response = client.post(
        "/api/auth/change-password",
        json={"current_password": TEST_PASSWORD, "new_password": "Brand-new-pass-1"},
    )

    assert response.status_code == 200
    # This session continues; the other device is logged out.
    assert client.get("/api/auth/me").status_code == 200
    assert other_device.get("/api/auth/me").status_code == 401
    # Old password no longer works, the new one does.
    fresh = ApiClient(app.test_client())
    assert fresh.login("pat", TEST_PASSWORD).status_code == 401
    assert fresh.login("pat", "Brand-new-pass-1").status_code == 200
    assert "auth.password_changed" in audit_actions()


def test_change_password_rejects_wrong_current_password(login_as) -> None:
    client = login_as("planner")

    response = client.post(
        "/api/auth/change-password",
        json={"current_password": "Not-my-password", "new_password": "Brand-new-pass-1"},
    )

    assert response.status_code == 422
    assert "current_password" in response.get_json()["error"]["details"]["fields"]


def test_change_password_enforces_minimum_length(login_as) -> None:
    client = login_as("planner")

    response = client.post(
        "/api/auth/change-password",
        json={"current_password": TEST_PASSWORD, "new_password": "short"},
    )

    assert response.status_code == 422
    messages = response.get_json()["error"]["details"]["fields"]["new_password"]
    assert "at least 8 characters" in messages[0]


def test_change_password_rejects_reusing_the_current_password(login_as) -> None:
    client = login_as("planner")

    response = client.post(
        "/api/auth/change-password",
        json={"current_password": TEST_PASSWORD, "new_password": TEST_PASSWORD},
    )

    assert response.status_code == 422


def test_change_password_requires_login(api: ApiClient) -> None:
    response = api.post(
        "/api/auth/change-password",
        json={"current_password": "whatever1", "new_password": "Brand-new-pass-1"},
    )

    assert response.status_code == 401
