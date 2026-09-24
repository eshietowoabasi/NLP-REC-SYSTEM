"""Flask CLI commands (``flask --app wsgi <command>``)."""

from __future__ import annotations

import os

import click
from flask import Flask

from app.seed import AdminSeed, SeedError, run_seed


def admin_from_env() -> AdminSeed | None:
    """Read the first admin's details from ADMIN_* environment variables, if all are set."""
    username = os.environ.get("ADMIN_USERNAME", "").strip()
    email = os.environ.get("ADMIN_EMAIL", "").strip()
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not (username and email and password):
        return None
    full_name = os.environ.get("ADMIN_FULL_NAME", "").strip() or "System Administrator"
    return AdminSeed(username=username, email=email, password=password, full_name=full_name)


def register_cli(app: Flask) -> None:
    """Attach the project's CLI commands to ``app``."""

    @app.cli.command("seed")
    def seed_command() -> None:
        """Create the first admin, default settings, skill patterns and stop words."""
        try:
            summary = run_seed(admin_from_env())
        except SeedError as exc:
            raise click.ClickException(str(exc)) from exc
        admin = "created" if summary["admin_created"] else "already exists (unchanged)"
        click.echo(f"Admin user: {admin}")
        click.echo(f"Settings added: {summary['settings']}")
        click.echo(f"Skill patterns added: {summary['skill_patterns']}")
        click.echo(f"Stop words added: {summary['stop_words']}")
