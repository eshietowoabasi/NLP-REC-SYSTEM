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


def enqueue(path: str, *args: Any, timeout: int | None = None) -> str | None:
    """Queue the job at ``path`` with ``args``; returns the RQ job id (None when eager)."""
    app = current_app._get_current_object()  # type: ignore[attr-defined]
    if app.config["TASKS_EAGER"]:
        with app.app_context():  # separate DB session, as in the worker
            _resolve(path)(*args)
        return None
    queue = Queue(app.config["RQ_QUEUE_NAME"], connection=get_redis())
    job = queue.enqueue(path, *args, job_timeout=timeout or app.config["JOB_TIMEOUT_SECONDS"])
    logger.info("Queued %s%s as job %s", path, args, job.id)
    return job.id
