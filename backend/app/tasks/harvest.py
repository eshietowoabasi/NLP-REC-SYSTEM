"""Background labour-market harvesting."""

from __future__ import annotations

import hashlib
import re
from datetime import date

from sqlalchemy import or_, select

from app.extensions import db
from app.models import (
    Document,
    DocumentStatus,
    FileType,
    JobHarvestRun,
    Programme,
    SourceCategory,
)
from app.services.harvesting.myjobmag import (
    collect_jobs,
)
from app.services.storage import get_storage
from app.tasks.queue import enqueue
from app.utils.time import utcnow


def _filename(title: str) -> str:
    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        title.lower(),
    ).strip("-")[:80]

    return (
        f"myjobmag-{slug or 'job-advert'}.txt"
    )


def _published_date(
    value: str,
) -> date | None:
    if not value:
        return None

    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def harvest_programme_jobs(
    run_id: int,
) -> None:
    run = db.session.get(
        JobHarvestRun,
        run_id,
    )

    if run is None:
        return

    programme = db.session.get(
        Programme,
        run.programme_id,
    )

    if programme is None:
        run.status = "failed"
        run.error_message = (
            "The programme no longer exists."
        )
        run.completed_at = utcnow()
        db.session.commit()
        return

    run.status = "running"
    run.started_at = utcnow()
    run.error_message = None
    db.session.commit()

    stored_files = []

    try:
        collection = collect_jobs(
            list(
                programme.job_search_terms
                or []
            ),
            list(
                programme.job_field_slugs
                or []
            ),
            run.target_count,
            run.pages_per_field,
        )

        run.examined_count = (
            collection.examined
        )

        run.found_count = len(
            collection.adverts
        )

        run.skipped_count = (
            collection.skipped
        )

        imported_ids = []

        for advert in collection.adverts:
            content = advert.text.encode(
                "utf-8"
            )

            content_hash = hashlib.sha256(
                content
            ).hexdigest()

            duplicate = db.session.scalar(
                select(Document.id)
                .where(
                    or_(
                        Document.content_hash
                        == content_hash,
                        Document.source_url
                        == advert.url,
                    )
                )
                .limit(1)
            )

            if duplicate is not None:
                run.skipped_count += 1
                continue

            stored_filename = (
                get_storage().save(
                    content,
                    ".txt",
                )
            )

            stored_files.append(
                stored_filename
            )

            document = Document(
                uploaded_by_id=
                    run.requested_by_id,
                programme_id=
                    programme.id,
                title=advert.title[:255],
                original_filename=
                    _filename(
                        advert.title
                    )[:255],
                stored_filename=
                    stored_filename,
                file_type=FileType.TXT,
                file_size=len(content),
                content_hash=
                    content_hash,
                source_category=
                    SourceCategory.JOB_MARKET,
                processing_status=
                    DocumentStatus.UPLOADED,
                source="MyJobMag",
                source_url=advert.url,
                published_on=
                    _published_date(
                        advert.date_posted
                    ),
            )

            db.session.add(document)
            db.session.flush()

            imported_ids.append(
                document.id
            )

        run.imported_count = len(
            imported_ids
        )

        run.status = "completed"
        run.completed_at = utcnow()

        db.session.commit()

        for document_id in imported_ids:
            enqueue(
                "app.tasks.ingestion.ingest_document",
                document_id,
            )

    except Exception as exc:
        db.session.rollback()

        for stored_filename in stored_files:
            try:
                get_storage().delete(
                    stored_filename
                )
            except Exception:
                pass

        run = db.session.get(
            JobHarvestRun,
            run_id,
        )

        if run is not None:
            run.status = "failed"
            run.error_message = str(exc)[:1000]
            run.completed_at = utcnow()
            db.session.commit()

        raise
