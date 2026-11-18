"""Self sign-up: anyone can create a planner account for the programmes they work on."""

from __future__ import annotations

from app.extensions import db
from app.sessions import default_programme

PASSWORD = "Synthetic-pass-2026"


def test_programmes_for_sign_up_are_public(api) -> None:
    programme = default_programme()
    db.session.commit()

    listed = api.get("/api/auth/register/programmes").get_json()["data"]

    assert {"id": programme.id, "name": programme.name} in [
        {"id": p["id"], "name": p["name"]} for p in listed
    ]


def test_signing_up_creates_a_signed_in_planner(api) -> None:
    programme = default_programme()
    db.session.commit()

    response = api.post(
        "/api/auth/register",
        json={
            "username": "new-planner",
            "email": "new.planner@example.com",
            "full_name": "Synthetic New Planner",
            "password": PASSWORD,
            "programme_ids": [programme.id],
        },
    )

    assert response.status_code == 201, response.get_json()
    user = response.get_json()["data"]["user"]
    assert user["role"] == "planner"
    assert [p["id"] for p in user["programmes"]] == [programme.id]
    me = api.get("/api/auth/me").get_json()["data"]
    assert me["username"] == "new-planner"


def test_sign_up_needs_a_programme_and_unique_details(api, make_user) -> None:
    make_user("planner", username="taken-name", email="taken@example.com")
    default_programme()
    db.session.commit()
    base = {
        "username": "taken-name",
        "email": "taken@example.com",
        "full_name": "Synthetic Person",
        "password": PASSWORD,
    }

    no_programme = api.post("/api/auth/register", json={**base, "programme_ids": []})
    taken = api.post("/api/auth/register", json={**base, "programme_ids": [default_programme().id]})
    unknown = api.post(
        "/api/auth/register",
        json={**base, "username": "fresh", "email": "fresh@example.com", "programme_ids": [999999]},
    )

    assert no_programme.status_code == 422
    assert taken.status_code == 409
    assert unknown.status_code == 422
