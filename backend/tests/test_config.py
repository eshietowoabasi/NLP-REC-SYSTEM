"""Tests for environment-based configuration selection."""

from __future__ import annotations

import pytest

from app.config import (
    BaseConfig,
    DevelopmentConfig,
    ProductionConfig,
    TestingConfig,
    get_config,
    resolve_test_database_url,
)
from tests.conftest import ensure_test_database


def test_test_database_is_dev_database_with_test_suffix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.setattr(
        BaseConfig, "SQLALCHEMY_DATABASE_URI", "postgresql+psycopg://u:p@db:5432/nlprs"
    )
    assert resolve_test_database_url() == "postgresql+psycopg://u:p@db:5432/nlprs_test"


def test_explicit_test_database_url_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+psycopg://u:p@other/custom_test")
    assert resolve_test_database_url() == "postgresql+psycopg://u:p@other/custom_test"


def test_active_test_config_never_points_at_a_non_test_database() -> None:
    assert (TestingConfig.SQLALCHEMY_DATABASE_URI or "").endswith("_test")
    assert TestingConfig.REDIS_URL.endswith("/15")


def test_suite_refuses_a_database_not_named_test() -> None:
    with pytest.raises(pytest.exit.Exception, match="must end in '_test'"):
        ensure_test_database("postgresql+psycopg://u:p@localhost:5432/nlprs")


def test_explicit_name_selects_config() -> None:
    assert get_config("testing") is TestingConfig
    assert get_config("development") is DevelopmentConfig


def test_app_env_variable_selects_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "testing")
    assert get_config() is TestingConfig


def test_unknown_env_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="Unknown APP_ENV"):
        get_config("staging")


def test_production_requires_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db/x")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        get_config("production")


def test_production_rejects_placeholder_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "change-me-to-a-long-random-string-xxxxxxxx")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db/x")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    with pytest.raises(RuntimeError, match="at least 32 characters"):
        get_config("production")


def test_production_accepts_strong_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "a" * 64)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db/x")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    assert get_config("production") is ProductionConfig
