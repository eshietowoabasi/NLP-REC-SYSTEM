"""Labour-market collection rules shared by the API and the collection job.

A collection (``JobHarvestRun``) goes queued → running → completed or failed. Two things are
checked here:

* **Stopped collections.** If the background job dies (worker crash, timeout, restart), nothing
  marks the run as failed, and the programme would refuse new collections for ever. Before a
  programme's runs are read or a new one is started, :func:`expire_stopped_runs` marks such runs
  as failed: their RQ job has ended or disappeared, or they have been going for longer than any
  collection can take.
* **Readiness.** A completed collection has only *imported* its adverts; each advert is then
  processed (parsed, split into passages, embedded) by a separate ingestion job. The
  :func:`run_progress` counts tell users when the adverts can actually be analysed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from flask import current_app
from redis.exceptions import RedisError
from rq.exceptions import NoSuchJobError
from rq.job import Job
from sqlalchemy import func, select

from app.extensions import db, get_redis
from app.models import Document, DocumentStatus, JobHarvestRun
from app.utils.time import utcnow

logger = logging.getLogger(__name__)

# The RQ timeout of one collection round. Collecting is slow on purpose (2–3.5 s between
# requests); a large collection is many rounds, each queued by the previous one.
HARVEST_JOB_TIMEOUT = 900
# A run still active this long after it was created or started cannot still be working.
STOPPED_AFTER = timedelta(seconds=HARVEST_JOB_TIMEOUT + 300)
ACTIVE_STATUSES = ("queued", "running")
STOPPED_MESSAGE = "The collection stopped unexpectedly before it finished. Start it again."
# RQ job states in which the job will never update the run any more.
ENDED_JOB_STATES = {"finished", "failed", "stopped", "canceled"}


def _job_has_ended(job_id: str) -> bool | None:
    """True if the RQ job has ended or no longer exists; None if Redis cannot be asked."""
    try:
        job = Job.fetch(job_id, connection=get_redis())
        return str(job.get_status(refresh=True)) in ENDED_JOB_STATES
    except NoSuchJobError:
        return True
    except RedisError:
        logger.warning("Could not check collection job %s in Redis.", job_id)
        return None


def _has_stopped(run: JobHarvestRun) -> bool:
    if run.rq_job_id:
        ended = _job_has_ended(run.rq_job_id)
        if ended is not None:
            # Redis knows: a large collection runs for a long time in rounds, each with its own
            # job, so only the current round's job decides.
            return ended
    # Fallback for a worker that died without RQ noticing, and for runs without a job id.
    began = run.started_at or run.created_at
    return utcnow() - began > STOPPED_AFTER


def expire_stopped_runs(programme_id: int) -> None:
    """Mark the programme's queued/running collections whose job has stopped as failed.

    Commits only if something changed. With ``TASKS_EAGER`` (tests) jobs run synchronously,
    so only the time limit applies.
    """
    runs = db.session.scalars(
        select(JobHarvestRun).where(
            JobHarvestRun.programme_id == programme_id,
            JobHarvestRun.status.in_(ACTIVE_STATUSES),
        )
    ).all()
    eager = current_app.config["TASKS_EAGER"]
    changed = False
    for run in runs:
        stopped = (
            utcnow() - (run.started_at or run.created_at) > STOPPED_AFTER
            if eager
            else _has_stopped(run)
        )
        if stopped:
            logger.warning("Collection %s stopped unexpectedly; marking it failed.", run.id)
            run.status = "failed"
            run.error_message = STOPPED_MESSAGE
            run.completed_at = utcnow()
            changed = True
    if changed:
        db.session.commit()


@dataclass(frozen=True)
class RunProgress:
    """How far a collection has got, for users rather than for the job."""

    phase: str  # queued | collecting | preparing | ready | failed
    documents_ready: int
    documents_processing: int
    documents_failed: int
    # Ready adverts, oldest first, so New analysis can select them for the planner.
    ready_document_ids: list[int]


def run_progress(run: JobHarvestRun) -> RunProgress:
    """The run's phase and how many of its imported adverts are ready to analyse."""
    counts = dict(
        db.session.execute(
            select(Document.processing_status, func.count())
            .where(Document.harvest_run_id == run.id)
            .group_by(Document.processing_status)
        ).all()
    )
    ready = counts.get(DocumentStatus.READY, 0)
    failed = counts.get(DocumentStatus.FAILED, 0)
    processing = sum(counts.values()) - ready - failed - counts.get(DocumentStatus.ARCHIVED, 0)

    if run.status == "queued":
        phase = "queued"
    elif run.status == "running":
        phase = "collecting"
    elif run.status == "failed":
        phase = "failed"
    else:
        phase = "preparing" if processing > 0 else "ready"
    ready_ids = list(
        db.session.scalars(
            select(Document.id)
            .where(
                Document.harvest_run_id == run.id,
                Document.processing_status == DocumentStatus.READY,
            )
            .order_by(Document.id)
        )
    )
    return RunProgress(phase, ready, processing, failed, ready_ids)
