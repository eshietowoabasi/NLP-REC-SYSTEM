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

    @app.cli.command("import-manifest")
    @click.argument("manifest", type=click.Path(exists=True, dir_okay=False))
    def import_manifest_command(manifest: str) -> None:
        """Set titles, source, link and date of library documents from a corpus manifest.

        MANIFEST is the collector's ``manifest.csv`` (columns file, source, url, title, company,
        date_posted, ...). Documents are matched by file name; job adverts get
        "Title – Company" as their title. Documents not in the manifest are left unchanged.
        """
        import csv
        from datetime import date
        from pathlib import PurePosixPath

        from sqlalchemy import select

        from app.extensions import db
        from app.models import Document, SourceCategory

        with open(manifest, encoding="utf-8-sig", newline="") as handle:
            rows = {
                PurePosixPath(r["file"]).name: r for r in csv.DictReader(handle) if r.get("file")
            }
        updated = 0
        for document in db.session.scalars(select(Document)):
            row = rows.get(document.original_filename)
            if row is None:
                continue
            title = (row.get("title") or "").strip() or document.title
            company = (row.get("company") or "").strip()
            if document.source_category == SourceCategory.JOB_MARKET and company:
                title = f"{title} – {company}"
            posted = (row.get("date_posted") or "").strip()
            document.title = title[:255]
            document.source = (row.get("source") or "").strip() or None
            document.source_url = (row.get("url") or "").strip() or None
            document.published_on = date.fromisoformat(posted) if posted else None
            updated += 1
        db.session.commit()
        click.echo(f"Updated {updated} of {len(rows)} manifest entries.")

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
