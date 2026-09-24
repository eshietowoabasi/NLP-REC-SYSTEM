"""Flask extension instances, created unbound and initialised in the app factory."""

from __future__ import annotations

from flask import Flask, current_app
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from redis import Redis
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


db = SQLAlchemy(model_class=Base)
migrate = Migrate()


def init_redis(app: Flask) -> None:
    """Create the Redis client for this app and store it on ``app.extensions``."""
    app.extensions["redis"] = Redis.from_url(
        app.config["REDIS_URL"], socket_connect_timeout=2, socket_timeout=5
    )


def get_redis() -> Redis:
    """Return the Redis client of the current app."""
    return current_app.extensions["redis"]
