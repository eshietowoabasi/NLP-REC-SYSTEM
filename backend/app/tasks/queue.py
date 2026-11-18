"""Enqueueing background jobs.

Jobs are referenced by dotted path (e.g. ``"app.tasks.ingestion.ingest_document"``) so the web
process does not import heavy NLP code. With ``TASKS_EAGER`` (used by the test suite) the job
runs immediately in a fresh application context instead of going through Redis.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any

from flask import current_app
from rq import Queue

from app.extensions import get_redis

logger = logging.getLogger(__name__)


def _resolve(path: str) -> Any:
    module_name, _, attribute = path.rpartition(".")
    return getattr(importlib.import_module(module_name), attribute)


def background_queue_name(name: str) -> str:
    """The low-priority queue the worker only takes from when ``name`` is empty."""
    return f"{name}-background"


def enqueue(
    path: str, *args: Any, timeout: int | None = None, background: bool = False
) -> str | None:
    """Queue the job at ``path`` with ``args``; returns the RQ job id (None when eager).

    ``background`` jobs (bulk loading of the NUC catalogue) wait until no planner job (an
    analysis, job collection, report or document upload) is queued.
    """
    app = current_app._get_current_object()  # type: ignore[attr-defined]
    if app.config["TASKS_EAGER"]:
        with app.app_context():  # separate DB session, as in the worker
            _resolve(path)(*args)
        return None
    name = app.config["RQ_QUEUE_NAME"]
    queue = Queue(background_queue_name(name) if background else name, connection=get_redis())
    job = queue.enqueue(path, *args, job_timeout=timeout or app.config["JOB_TIMEOUT_SECONDS"])
    logger.info("Queued %s%s as job %s", path, args, job.id)
    return job.id
