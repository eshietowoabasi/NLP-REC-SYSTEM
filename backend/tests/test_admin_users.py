"""Tests for the admin user-management API (/api/admin/users)."""

from __future__ import annotations

from sqlalchemy import select

from app.extensions import db
from app.models import AuditLog, User
from tests.conftest import TEST_PASSWORD, ApiClient

NEW_USER = {
    "username": "New.Planner",
    "email": "New.Planner@Example.com",
    "full_name": "  New Planner ",
    "role": "planner",
    "password": "Initial-pass-1",
}


def audit_entries(action: str) -> list[AuditLog]:
    return list(db.session.scalars(select(AuditLog).where(AuditLog.action_type == action)))


# ---------------------------------------------------------------------------- list


def test_list_users_is_paginated(login_as, make_user) -> None:
    admin = login_as("admin")
    for index in range(4):
        make_user("viewer", username=f"viewer{index}")

    response = admin.get("/api/admin/users?per_page=2&page=2")

    data = response.get_json()["data"]
    assert response.status_code == 200
    assert len(data["items"]) == 2
    assert data["pagination"] == {"page": 2, "per_page": 2, "total": 5, "pages": 3}


def test_list_users_filters_by_role_status_and_search(login_as, make_user) -> None:
    admin = login_as("admin", username="boss")
    make_user("planner", username="alice", full_name="Alice Planner")
    make_user("planner", username="bob", is_active=False)
    make_user("viewer", username="carol")

    def usernames(query: str) -> set[str]:
        items = admin.get(f"/api/admin/users?{query}").get_json()["data"]["items"]
        return {item["username"] for item in items}

    assert usernames("role=planner") == {"alice", "bob"}
    assert usernames("is_active=false") == {"bob"}
    assert usernames("search=ALICE") == {"alice"}
    assert usernames("role=planner&is_active=true") == {"alice"}


def test_list_users_rejects_invalid_query(login_as) -> None:
    admin = login_as("admin")

    response = admin.get("/api/admin/users?per_page=1000")

    assert response.status_code == 422


# -------------------------------------------------------------------------- create


def test_create_user_normalises_and_audits(login_as) -> None:
    admin = login_as("admin")

    response = admin.post("/api/admin/users", json=NEW_USER)

    assert response.status_code == 201
    data = response.get_json()["data"]
    assert data["username"] == "new.planner"
    assert data["email"] == "new.planner@example.com"
    assert data["full_name"] == "New Planner"
    assert data["is_active"] is True
    assert [e.detail for e in audit_entries("user.created")] == [
        {"username": "new.planner", "role": "planner"}
    ]
    # The new user can log in with the initial password.
    assert (
        ApiClient(admin.client.application.test_client())
        .login("new.planner", "Initial-pass-1")
        .status_code
        == 200
    )


def test_create_user_rejects_duplicates(login_as, make_user) -> None:
    admin = login_as("admin")
    make_user("viewer", username="new.planner", email="taken@example.com")

    response = admin.post("/api/admin/users", json={**NEW_USER, "email": "TAKEN@example.com"})

    assert response.status_code == 409
    assert set(response.get_json()["error"]["details"]["fields"]) == {"username", "email"}


def test_create_user_validates_fields(login_as) -> None:
    admin = login_as("admin")

    response = admin.post(
        "/api/admin/users",
        json={
            "username": "a b",
            "email": "not-an-email",
            "full_name": "",
            "role": "superuser",
            "password": "short",
            "unexpected": True,
        },
    )

    assert response.status_code == 422
    fields = response.get_json()["error"]["details"]["fields"]
    assert set(fields) == {"username", "email", "full_name", "role", "password", "unexpected"}


# -------------------------------------------------------------------------- update


def test_change_role_is_audited(login_as, make_user) -> None:
    admin = login_as("admin")
    user = make_user("viewer")

    response = admin.patch(f"/api/admin/users/{user.id}", json={"role": "planner"})

    assert response.status_code == 200
    assert response.get_json()["data"]["role"] == "planner"
    assert [e.detail for e in audit_entries("user.role_changed")] == [
        {"from": "viewer", "to": "planner"}
    ]


def test_update_name_and_email(login_as, make_user) -> None:
    admin = login_as("admin")
    user = make_user("viewer", email="old@example.com")

    response = admin.patch(
        f"/api/admin/users/{user.id}",
        json={"full_name": "Renamed", "email": "NEW@example.com"},
    )

    data = response.get_json()["data"]
    assert (data["full_name"], data["email"]) == ("Renamed", "new@example.com")
    changes = audit_entries("user.updated")[0].detail["changes"]
    assert changes["email"] == {"from": "old@example.com", "to": "new@example.com"}


def test_unchanged_values_produce_no_audit_entries(login_as, make_user) -> None:
    admin = login_as("admin")
    user = make_user("viewer")

    admin.patch(
        f"/api/admin/users/{user.id}",
        json={"role": "viewer", "is_active": True, "full_name": user.full_name},
    )

    assert audit_entries("user.updated") == []
    assert audit_entries("user.role_changed") == []
    assert audit_entries("user.activated") == []


def test_email_change_cannot_take_another_users_email(login_as, make_user) -> None:
    admin = login_as("admin")
    make_user("viewer", email="taken@example.com")
    user = make_user("viewer")

    response = admin.patch(f"/api/admin/users/{user.id}", json={"email": "taken@example.com"})

    assert response.status_code == 409


def test_deactivate_logs_the_user_out_and_blocks_login(app, login_as) -> None:
    admin = login_as("admin")
    victim = login_as("planner", username="leaving")

    response = admin.patch(f"/api/admin/users/{victim.user.id}", json={"is_active": False})

    assert response.status_code == 200
    assert victim.get("/api/auth/me").status_code == 401
    assert ApiClient(app.test_client()).login("leaving").status_code == 403
    assert len(audit_entries("user.deactivated")) == 1


def test_reactivate_user(login_as, make_user) -> None:
    admin = login_as("admin")
    user = make_user("viewer", is_active=False)

    response = admin.patch(f"/api/admin/users/{user.id}", json={"is_active": True})

    assert response.get_json()["data"]["is_active"] is True
    assert len(audit_entries("user.activated")) == 1


def test_reset_password(app, login_as) -> None:
    admin = login_as("admin")
    target = login_as("viewer", username="forgetful")

    response = admin.patch(
        f"/api/admin/users/{target.user.id}", json={"new_password": "Reset-by-admin-1"}
    )

    assert response.status_code == 200
    assert target.get("/api/auth/me").status_code == 401  # existing session ended
    fresh = ApiClient(app.test_client())
    assert fresh.login("forgetful", TEST_PASSWORD).status_code == 401
    assert fresh.login("forgetful", "Reset-by-admin-1").status_code == 200
    assert len(audit_entries("user.password_reset")) == 1


def test_admin_cannot_demote_or_deactivate_themselves(login_as) -> None:
    admin = login_as("admin")
    own_url = f"/api/admin/users/{admin.user.id}"

    demote = admin.patch(own_url, json={"role": "viewer"})
    deactivate = admin.patch(own_url, json={"is_active": False})

    for response in (demote, deactivate):
        assert response.status_code == 422
        assert response.get_json()["error"]["code"] == "SELF_MODIFICATION"
    db.session.expire_all()
    me = db.session.get(User, admin.user.id)
    assert me.role == "admin" and me.is_active


def test_admin_can_edit_own_name(login_as) -> None:
    admin = login_as("admin")

    response = admin.patch(f"/api/admin/users/{admin.user.id}", json={"full_name": "Head Admin"})

    assert response.status_code == 200


def test_update_unknown_user_is_404(login_as) -> None:
    admin = login_as("admin")

    response = admin.patch("/api/admin/users/9999", json={"full_name": "Nobody"})

    assert response.status_code == 404
