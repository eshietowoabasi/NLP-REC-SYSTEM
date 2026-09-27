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

    @app.cli.command("extract-courses")
    def extract_courses_command() -> None:
        """(Re)build the course list of every NUC core document (course-level overlap).

        New NUC core uploads get their courses at ingestion; this backfills documents ingested
        before course extraction existed. Passages are left untouched.
        """
        from sqlalchemy import select

        from app.extensions import db
        from app.models import Document, DocumentStatus, SourceCategory
        from app.services.embeddings.encoder import get_encoder
        from app.services.ingestion.cleaning import clean_pages
        from app.services.ingestion.parsers import parse_file
        from app.services.storage import get_storage
        from app.settings import get_setting
        from app.tasks.ingestion import store_courses

        encoder = get_encoder(get_setting("sbert_model"))
        documents = db.session.scalars(
            select(Document).where(
                Document.source_category == SourceCategory.NUC_CORE,
                Document.processing_status == DocumentStatus.READY,
            )
        ).all()
        for document in documents:
            parsed = parse_file(document.file_type, get_storage().read(document.stored_filename))
            count = store_courses(
                document, clean_pages(parsed.pages), parsed.page_count is not None, encoder
            )
            click.echo(f"{document.title}: {count} courses")
        db.session.commit()
