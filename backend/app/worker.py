"""RQ worker entry point: ``python -m app.worker``.

Jobs run inside a Flask application context so they can use the database session and
configuration exactly like request handlers.

A ``SimpleWorker`` runs every job in this same process instead of forking a child per job.
That keeps the NLP models (spaCy, SBERT), which the services cache at module level, loaded
between jobs, and avoids forking after PyTorch has started its threads. Docker restarts the
worker if it ever crashes.
"""

from __future__ import annotations

import os

from rq import Queue, SimpleWorker
from rq.timeouts import TimerDeathPenalty, UnixSignalDeathPenalty

from app import create_app
from app.extensions import db, get_redis
from app.models import Document, SourceCategory
from app.settings import upgrade_raised_defaults
from app.tasks.queue import background_queue_name

INGEST = "app.tasks.ingestion.ingest_document"

Worker = SimpleWorker


def move_nuc_core_loading(queue: Queue, background: Queue) -> int:
    """Move queued NUC core ingestion jobs to the background queue, so planners' jobs queued
    after them run first. Returns how many were moved."""
    moved = 0
    for job in queue.get_jobs():
        if job.func_name != INGEST or not job.args:
            continue
        document = db.session.get(Document, job.args[0])
        if document is None or document.source_category != SourceCategory.NUC_CORE:
            continue
        queue.remove(job)
        background.enqueue_job(job)
        moved += 1
    db.session.remove()
    return moved


def main() -> None:
    """Start a worker on the planner queue first, then the background queue."""
    app = create_app()
    with app.app_context():
        connection = get_redis()
        name = app.config["RQ_QUEUE_NAME"]
        queue = Queue(name, connection=connection)
        background = Queue(background_queue_name(name), connection=connection)
        for key in upgrade_raised_defaults():
            app.logger.info("Setting %s moved to its new default", key)
        moved = move_nuc_core_loading(queue, background)
        if moved:
            app.logger.info("Moved %d NUC core loading jobs to the background queue", moved)
        worker = Worker([queue, background], connection=connection)
        # Job timeouts use SIGALRM, which Windows lacks; fall back to a timer thread there.
        worker.death_penalty_class = (
            TimerDeathPenalty if os.name == "nt" else UnixSignalDeathPenalty
        )
        worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
