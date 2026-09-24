"""Flask extension instances, created unbound and initialised in the app factory."""

from __future__ import annotations

from flask import Flask, current_app
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from redis import Redis
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Deterministic constraint names, so Alembic migrations are stable and readable.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


db = SQLAlchemy(model_class=Base)
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()


def init_redis(app: Flask) -> None:
    """Create the Redis client for this app and store it on ``app.extensions``."""
    app.extensions["redis"] = Redis.from_url(
        app.config["REDIS_URL"], socket_connect_timeout=2, socket_timeout=5
    )


def get_redis() -> Redis:
    """Return the Redis client of the current app."""
    return current_app.extensions["redis"]
