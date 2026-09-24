"""Initial data: first admin user, default settings, skill patterns and domain stop words.

Every function is idempotent: existing rows are left untouched, so ``flask seed`` can be run
again safely (for example after adding new starter patterns).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import func, select

from app.auth.passwords import hash_password, password_problem
from app.extensions import db
from app.models.configuration import Setting, SkillPattern, StopWord
from app.models.enums import SkillLabel, UserRole
from app.models.user import User
from app.seed.skill_patterns import iter_skill_patterns
from app.seed.stop_words import DOMAIN_STOP_WORDS
from app.settings import DEFAULT_SETTINGS


@dataclass(frozen=True)
class AdminSeed:
    username: str
    email: str
    password: str
    full_name: str


class SeedError(Exception):
    """Seeding cannot continue (e.g. admin credentials are missing or weak)."""


def seed_admin(admin: AdminSeed | None) -> bool:
    """Create the first admin unless any admin already exists. Returns True if created."""
    if db.session.scalar(select(User.id).where(User.role == UserRole.ADMIN).limit(1)):
        return False
    if admin is None:
        raise SeedError(
            "No admin exists yet. Set ADMIN_USERNAME, ADMIN_EMAIL and ADMIN_PASSWORD "
            "(and optionally ADMIN_FULL_NAME) in the environment, then run `flask seed` again."
        )
    problem = password_problem(admin.password)
    if problem:
        raise SeedError(f"ADMIN_PASSWORD is not acceptable: {problem}")
    db.session.add(
        User(
            username=admin.username.strip().lower(),
            email=admin.email.strip().lower(),
            full_name=admin.full_name.strip(),
            role=UserRole.ADMIN,
            password_hash=hash_password(admin.password),
        )
    )
    return True


def seed_settings() -> int:
    """Insert every default setting that is not stored yet. Returns the number added."""
    existing = set(db.session.scalars(select(Setting.key)))
    added = 0
    for key, value in DEFAULT_SETTINGS.items():
        if key not in existing:
            db.session.add(Setting(key=key, value=value))
            added += 1
    return added


def seed_skill_patterns() -> int:
    """Insert the starter skill patterns that are not stored yet. Returns the number added."""
    existing = {
        (label, db_pattern_key(pattern))
        for label, pattern in db.session.execute(select(SkillPattern.label, SkillPattern.pattern))
    }
    added = 0
    for label, canonical, pattern in iter_skill_patterns():
        key = (SkillLabel(label), db_pattern_key(pattern))
        if key in existing:
            continue
        db.session.add(
            SkillPattern(label=SkillLabel(label), pattern=pattern, canonical_name=canonical)
        )
        existing.add(key)
        added += 1
    return added


def db_pattern_key(pattern: object) -> str:
    """Stable comparison key for a phrase or token pattern.

    JSONB does not preserve object key order, so patterns are compared as key-sorted JSON.
    """
    return json.dumps(pattern, sort_keys=True)


def seed_stop_words() -> int:
    """Insert the starter domain stop words that are not stored yet. Returns the number added."""
    existing = set(db.session.scalars(select(func.lower(StopWord.word))))
    added = 0
    for word in DOMAIN_STOP_WORDS:
        if word.lower() not in existing:
            db.session.add(StopWord(word=word.lower()))
            existing.add(word.lower())
            added += 1
    return added


def run_seed(admin: AdminSeed | None) -> dict[str, int | bool]:
    """Run every seeding step in one transaction and return what was added."""
    try:
        summary: dict[str, int | bool] = {
            "admin_created": seed_admin(admin),
            "settings": seed_settings(),
            "skill_patterns": seed_skill_patterns(),
            "stop_words": seed_stop_words(),
        }
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return summary
