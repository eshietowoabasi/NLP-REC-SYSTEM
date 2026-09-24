"""Tests for the seed data and the ``flask seed`` command."""

from __future__ import annotations

import pytest
from flask import Flask
from sqlalchemy import select

from app.extensions import db
from app.models import Setting, SkillPattern, StopWord, User
from app.seed import AdminSeed, SeedError, run_seed
from app.seed.skill_patterns import iter_skill_patterns
from app.seed.stop_words import DOMAIN_STOP_WORDS
from app.settings import DEFAULT_SETTINGS

pytestmark = pytest.mark.usefixtures("app")

ADMIN = AdminSeed(
    username="Admin", email="Admin@Example.com", password="Seed-admin-pass-1", full_name="Admin"
)


def test_seed_creates_everything_once() -> None:
    first = run_seed(ADMIN)
    second = run_seed(ADMIN)

    assert first == {
        "admin_created": True,
        "settings": len(DEFAULT_SETTINGS),
        "skill_patterns": len(iter_skill_patterns()),
        "stop_words": len(set(DOMAIN_STOP_WORDS)),
    }
    assert second == {"admin_created": False, "settings": 0, "skill_patterns": 0, "stop_words": 0}
    admin = db.session.scalars(select(User)).one()
    assert (admin.username, admin.email, admin.role) == ("admin", "admin@example.com", "admin")


def test_seed_has_a_substantial_skill_vocabulary() -> None:
    rows = iter_skill_patterns()
    labels = {label for label, _, _ in rows}

    assert len({canonical for _, canonical, _ in rows}) >= 150
    assert labels == {"SKILL", "TOOL", "CERT", "LANGUAGE"}


def test_token_patterns_survive_a_second_seed_despite_jsonb_key_order() -> None:
    run_seed(ADMIN)
    token_rows = db.session.scalars(
        select(SkillPattern).where(SkillPattern.canonical_name == "Go")
    ).all()

    assert any(isinstance(row.pattern, list) for row in token_rows)
    assert run_seed(ADMIN)["skill_patterns"] == 0


def test_seed_keeps_admin_edited_settings() -> None:
    db.session.add(Setting(key="similarity_threshold", value=0.9))
    db.session.commit()

    run_seed(ADMIN)

    assert db.session.get(Setting, "similarity_threshold").value == 0.9


def test_seed_requires_admin_details_when_no_admin_exists() -> None:
    with pytest.raises(SeedError, match="ADMIN_USERNAME"):
        run_seed(None)
    assert db.session.query(Setting).count() == 0  # nothing half-seeded


def test_seed_rejects_a_weak_admin_password() -> None:
    with pytest.raises(SeedError, match="at least 8"):
        run_seed(AdminSeed("admin", "admin@example.com", "short", "Admin"))


def test_seed_without_admin_env_is_fine_once_an_admin_exists(make_user) -> None:
    make_user("admin")

    assert run_seed(None)["admin_created"] is False


def test_stop_words_are_lowercase_and_unique() -> None:
    run_seed(ADMIN)
    words = list(db.session.scalars(select(StopWord.word)))

    assert all(word == word.lower() for word in words)
    assert len(words) == len(set(words))
    assert {"candidate", "salary", "lagos", "abuja"} <= set(words)


def test_cli_seed_command(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in {
        "ADMIN_USERNAME": "cliadmin",
        "ADMIN_EMAIL": "cli@example.com",
        "ADMIN_PASSWORD": "Cli-admin-pass-1",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("ADMIN_FULL_NAME", raising=False)

    result = app.test_cli_runner().invoke(args=["seed"])

    assert result.exit_code == 0, result.output
    assert "Admin user: created" in result.output
    admin = db.session.scalars(select(User)).one()
    assert admin.full_name == "System Administrator"


def test_cli_seed_command_reports_missing_admin(app: Flask, monkeypatch) -> None:
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)

    result = app.test_cli_runner().invoke(args=["seed"])

    assert result.exit_code != 0
    assert "ADMIN_USERNAME" in result.output
