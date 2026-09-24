"""Unit tests for passwords, audit logging, settings and request validation helpers."""

from __future__ import annotations

import pytest
from flask import Flask
from pydantic import BaseModel
from sqlalchemy import select

from app.audit import AuditAction, record_audit
from app.auth.passwords import hash_password, password_problem, verify_password
from app.extensions import db
from app.models import AuditLog, Setting, User
from app.settings import DEFAULT_SETTINGS, get_setting
from app.utils.errors import ApiError
from app.utils.validation import paginate
from tests.conftest import ApiClient

# ------------------------------------------------------------------------ passwords


def test_password_rules() -> None:
    assert password_problem("1234567") is not None
    assert password_problem("12345678") is None
    assert password_problem("é" * 37) is not None  # 74 bytes > bcrypt's 72-byte limit


def test_hash_and_verify(app: Flask) -> None:
    hashed = hash_password("Correct-horse-1")

    assert hashed.startswith("$2")
    assert "$04$" in hashed  # testing config uses cost 4
    assert verify_password("Correct-horse-1", hashed)
    assert not verify_password("Wrong-horse-1", hashed)
    assert not verify_password("x" * 100, hashed)


def test_verify_against_unknown_user_is_false() -> None:
    assert verify_password("anything-at-all", None) is False


# ---------------------------------------------------------------------------- audit


def test_audit_records_client_ip_behind_the_proxy(api: ApiClient, make_user) -> None:
    user = make_user("viewer")

    api.post(
        "/api/auth/login",
        json={"identifier": user.username, "password": "Test-password-123"},
        headers={"X-Forwarded-For": "41.58.1.2"},
    )

    entry = db.session.scalars(select(AuditLog)).one()
    assert entry.ip_address == "41.58.1.2"
    assert entry.user_id == user.id


def test_record_audit_outside_a_request(app: Flask, make_user) -> None:
    user = make_user("admin")

    entry = record_audit(
        AuditAction.SETTINGS_UPDATED, "setting", "max_recommendations", user_id=user.id
    )
    db.session.commit()

    assert entry.ip_address is None
    assert entry.entity_id == "max_recommendations"
    assert entry.detail == {}


# ------------------------------------------------------------------------- settings


def test_get_setting_falls_back_to_default(app: Flask) -> None:
    assert get_setting("similarity_threshold") == DEFAULT_SETTINGS["similarity_threshold"]
    assert get_setting("credit_unit_allowance") is None


def test_get_setting_reads_stored_value(app: Flask) -> None:
    db.session.add(Setting(key="max_recommendations", value=15))
    db.session.commit()

    assert get_setting("max_recommendations") == 15


def test_get_unknown_setting_raises(app: Flask) -> None:
    with pytest.raises(KeyError):
        get_setting("no_such_setting")


def test_default_weights_sum_to_one() -> None:
    assert sum(DEFAULT_SETTINGS["score_weights"].values()) == pytest.approx(1.0)


# ----------------------------------------------------------------------- validation


def test_paginate_handles_an_empty_result(app: Flask) -> None:
    items, meta = paginate(select(User), page=1, per_page=10)

    assert items == []
    assert meta == {"page": 1, "per_page": 10, "total": 0, "pages": 0}


def test_parse_query_errors_become_422(app: Flask) -> None:
    from app.utils.validation import parse_query

    class Query(BaseModel):
        page: int

    with app.test_request_context("/?page=abc"), pytest.raises(ApiError) as caught:
        parse_query(Query)
    assert caught.value.status == 422
    assert "page" in caught.value.details["fields"]
