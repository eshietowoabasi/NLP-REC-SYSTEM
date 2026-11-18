"""Background labour-market harvesting."""

from __future__ import annotations

import contextlib
import hashlib
import logging
import re
import time
from datetime import date

from sqlalchemy import or_, select

from app.extensions import db
from app.harvesting import HARVEST_JOB_TIMEOUT
from app.models import (
    Document,
    DocumentStatus,
    FileType,
    JobHarvestRun,
    NucDiscipline,
    Programme,
    SkillPattern,
    SourceCategory,
)
from app.seed.discipline_job_titles import DISCIPLINE_JOB_TITLES
from app.services.harvesting.myjobmag import (
    collect_batch,
    plan_sources,
)
from app.services.storage import get_storage
from app.tasks.queue import enqueue
from app.utils.time import utcnow


def _filename(title: str) -> str:
    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        title.lower(),
    ).strip(
        "-"
    )[:80]

    return f"myjobmag-{slug or 'job-advert'}.txt"


def _published_date(
    value: str,
) -> date | None:
    if not value:
        return None

    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


logger = logging.getLogger(__name__)


def ingest_harvested_document_with_retry(
    document_id: int,
    attempts: int = 3,
) -> None:
    """Ingest a harvested advert, retrying transient NLP/worker failures."""
    from app.tasks.ingestion import ingest_document

    for attempt in range(1, attempts + 1):
        ingest_document(document_id)

        document = db.session.get(
            Document,
            document_id,
        )

        if document is None:
            return

        if document.processing_status == DocumentStatus.READY:
            logger.info(
                "Harvested document %s ingested successfully on attempt %s.",
                document_id,
                attempt,
            )
            return

        if document.processing_status != DocumentStatus.FAILED:
            return

        if attempt < attempts:
            logger.warning(
                "Harvested document %s failed ingestion; retrying (%s/%s).",
                document_id,
                attempt + 1,
                attempts,
            )
            time.sleep(3)

    logger.error(
        "Harvested document %s remained failed after %s attempts.",
        document_id,
        attempts,
    )


def ingest_harvested_batch_with_retry(
    document_ids: list[int],
) -> None:
    """Batch-ingest harvested adverts, then retry only any failures."""
    from app.tasks.ingestion import ingest_documents_batch

    ids = list(dict.fromkeys(int(document_id) for document_id in document_ids))
    if not ids:
        return

    ingest_documents_batch(ids)

    failed_ids = list(
        db.session.scalars(
            select(Document.id).where(
                Document.id.in_(ids),
                Document.processing_status == DocumentStatus.FAILED,
            )
        )
    )

    for document_id in failed_ids:
        ingest_harvested_document_with_retry(
            document_id,
            attempts=2,
        )


#: MyJobMag job fields searched for a discipline when its programme names none.
DEFAULT_JOB_FIELDS: dict[NucDiscipline, list[str]] = {
    NucDiscipline.COMPUTING: ["information-technology"],
    NucDiscipline.ENGINEERING_AND_TECHNOLOGY: ["engineering"],
    NucDiscipline.ALLIED_HEALTH_SCIENCES: ["medical"],
    NucDiscipline.MEDICINE_AND_DENTISTRY: ["medical"],
    NucDiscipline.BASIC_MEDICAL_SCIENCES: ["medical"],
    NucDiscipline.PHARMACEUTICAL_SCIENCE: ["medical"],
}


def job_fields(programme: Programme) -> list[str]:
    """The programme's MyJobMag job fields, or its discipline's usual field."""
    if programme.job_field_slugs:
        return list(programme.job_field_slugs)
    return list(DEFAULT_JOB_FIELDS.get(programme.nuc_discipline, []))


#: Very common office tools on the computing list that do not make an advert a computing one.
NOT_FIELD_DEFINING = {"Microsoft Excel"}

#: Adverts kept per round of a collection, and how long a round may run (seconds).
ROUND_SIZE = 25
ROUND_SECONDS = 240


def job_titles(programme: Programme, extra_terms: list[str] | None = None) -> list[str]:
    """The programme's job titles, the discipline's usual ones and the planner's own."""
    titles = list(programme.job_search_terms or [])
    titles += DISCIPLINE_JOB_TITLES.get(programme.nuc_discipline, [])
    titles += list(extra_terms or [])
    return list(dict.fromkeys(t.strip().lower() for t in titles if t.strip()))


def field_skill_phrases(programme: Programme) -> dict[str, list[str]]:
    """The phrases of the programme's field skills (its discipline's list, without general
    workplace skills), by skill: how the collector recognises an advert of the field."""
    if programme.nuc_discipline is None:
        return {}
    phrases: dict[str, list[str]] = {}
    for name, pattern in db.session.execute(
        select(SkillPattern.canonical_name, SkillPattern.pattern).where(
            SkillPattern.is_active.is_(True),
            SkillPattern.discipline == programme.nuc_discipline,
        )
    ):
        if isinstance(pattern, str) and len(pattern) >= 2 and name not in NOT_FIELD_DEFINING:
            phrases.setdefault(name, []).append(pattern.lower())
    return phrases


def programme_skill_names(programme: Programme) -> list[str]:
    """Names of the active skills on the programme's skills list (general + its discipline)."""
    disciplines = [SkillPattern.discipline.is_(None)]
    if programme.nuc_discipline is not None:
        disciplines.append(SkillPattern.discipline == programme.nuc_discipline)
    names = db.session.scalars(
        select(SkillPattern.canonical_name)
        .where(SkillPattern.is_active.is_(True), or_(*disciplines))
        .distinct()
    )
    return [name for name in names if name]


def _known_url(url: str) -> bool:
    return (
        db.session.scalar(select(Document.id).where(Document.source_url == url).limit(1))
        is not None
    )


def _import(
    run: JobHarvestRun, programme: Programme, adverts, stored_files: list[str]
) -> list[int]:
    """Store collected adverts as job-advert documents (duplicates skipped); returns new ids."""
    imported_ids = []
    for advert in adverts:
        content = advert.text.encode("utf-8")
        content_hash = hashlib.sha256(content).hexdigest()
        duplicate = db.session.scalar(
            select(Document.id)
            .where(or_(Document.content_hash == content_hash, Document.source_url == advert.url))
            .limit(1)
        )
        if duplicate is not None:
            run.skipped_count += 1
            continue
        stored_filename = get_storage().save(content, ".txt")
        stored_files.append(stored_filename)
        document = Document(
            uploaded_by_id=run.requested_by_id,
            programme_id=programme.id,
            title=advert.title[:255],
            original_filename=_filename(advert.title)[:255],
            stored_filename=stored_filename,
            file_type=FileType.TXT,
            file_size=len(content),
            content_hash=content_hash,
            source_category=SourceCategory.JOB_MARKET,
            processing_status=DocumentStatus.UPLOADED,
            source="MyJobMag",
            source_url=advert.url,
            published_on=_published_date(advert.date_posted),
            harvest_run_id=run.id,
        )
        db.session.add(document)
        db.session.flush()
        imported_ids.append(document.id)
    return imported_ids


def harvest_programme_jobs(
    run_id: int,
    extra_terms: list[str] | None = None,
    cursor: dict | None = None,
) -> None:
    """Collect current adverts for a run, one round (about ``ROUND_SIZE`` adverts) at a time.

    The system decides what belongs to the programme: it reads every advert in the programme's
    MyJobMag job field and the listings of its job titles (the programme's, its discipline's
    and ``extra_terms``, the planner's own), keeping adverts whose title matches or that ask for
    the field's skills. Each round imports its adverts (processing starts at once, so they are
    ready while collection goes on), then queues the next round from ``cursor`` until the run's
    target is reached or every source is read. Other jobs queued meanwhile run between rounds.
    """
    run = db.session.get(JobHarvestRun, run_id)
    if run is None:
        return
    programme = db.session.get(Programme, run.programme_id)
    if programme is None:
        run.status = "failed"
        run.error_message = "The programme no longer exists."
        run.completed_at = utcnow()
        db.session.commit()
        return
    if cursor is None:
        if run.status != "queued":
            # Already handled, e.g. marked as stopped while it waited in the queue.
            return
        run.status = "running"
        run.started_at = utcnow()
        run.error_message = None
        db.session.commit()
    elif run.status != "running":
        return  # stopped or failed meanwhile

    stored_files: list[str] = []
    try:
        titles = job_titles(programme, extra_terms)
        sources = plan_sources(titles, job_fields(programme))
        if not sources:
            raise ValueError("Job collection is not set up for this programme yet.")
        remaining = max(run.target_count - run.imported_count, 0)
        batch = collect_batch(
            sources,
            cursor,
            titles,
            field_skill_phrases(programme),
            batch_size=min(ROUND_SIZE, remaining),
            deadline=time.monotonic() + ROUND_SECONDS,
            is_known=_known_url,
        )
        run.examined_count += batch.examined
        run.found_count += len(batch.adverts)
        run.skipped_count += batch.skipped + batch.known
        imported_ids = _import(run, programme, batch.adverts, stored_files)
        run.imported_count += len(imported_ids)
        finished = batch.cursor is None or run.imported_count >= run.target_count
        if finished:
            run.status = "completed"
            run.completed_at = utcnow()
        db.session.commit()

        if imported_ids:
            enqueue(
                "app.tasks.harvest.ingest_harvested_batch_with_retry",
                imported_ids,
                timeout=1800,
            )
        if not finished:
            job_id = enqueue(
                "app.tasks.harvest.harvest_programme_jobs",
                run.id,
                list(extra_terms or []),
                batch.cursor,
                timeout=HARVEST_JOB_TIMEOUT,
            )
            if job_id is not None:
                run = db.session.get(JobHarvestRun, run_id)
                run.rq_job_id = job_id
                db.session.commit()
    except Exception as exc:
        db.session.rollback()
        # Best-effort clean-up of files stored in this round.
        for stored_filename in stored_files:
            with contextlib.suppress(Exception):
                get_storage().delete(stored_filename)
        run = db.session.get(JobHarvestRun, run_id)
        if run is not None:
            run.error_message = str(exc)[:1000]
            run.completed_at = utcnow()
            # Adverts from earlier rounds are kept: the run ends as completed if it has some.
            run.status = "completed" if run.imported_count else "failed"
            db.session.commit()
        raise
