"""Tests for the RQ worker entry point and job enqueueing."""

from __future__ import annotations

import os

import pytest
from flask import Flask
from rq.timeouts import TimerDeathPenalty, UnixSignalDeathPenalty

from app import worker
from app.tasks import queue


class FakeWorker:
    """Records how the worker was built instead of connecting to Redis."""

    instances: list[FakeWorker] = []

    def __init__(self, queues, connection) -> None:
        self.queues = queues
        self.connection = connection
        self.work_kwargs: dict | None = None
        self.death_penalty_class = None
        FakeWorker.instances.append(self)

    def work(self, **kwargs) -> None:
        self.work_kwargs = kwargs


def test_worker_listens_on_configured_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setattr(worker, "Worker", FakeWorker)
    FakeWorker.instances.clear()

    worker.main()

    (started,) = FakeWorker.instances
    assert [q.name for q in started.queues] == ["default"]
    assert started.work_kwargs == {"with_scheduler": False}
    expected = TimerDeathPenalty if os.name == "nt" else UnixSignalDeathPenalty
    assert started.death_penalty_class is expected


def test_worker_runs_jobs_in_process() -> None:
    from rq import SimpleWorker

    # Jobs run in the worker process so cached NLP models survive between jobs.
    assert worker.Worker is SimpleWorker


def test_enqueue_uses_redis_when_not_eager(app: Flask, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    class FakeQueue:
        def __init__(self, name, connection) -> None:
            captured["name"] = name

        def enqueue(self, path, *args, job_timeout):
            captured.update(path=path, args=args, timeout=job_timeout)
            return type("Job", (), {"id": "job-123"})()

    monkeypatch.setattr(queue, "Queue", FakeQueue)
    app.config["TASKS_EAGER"] = False

    job_id = queue.enqueue("app.tasks.ingestion.ingest_document", 7)

    assert job_id == "job-123"
    assert captured == {
        "name": "default",
        "path": "app.tasks.ingestion.ingest_document",
        "args": (7,),
        "timeout": 900,
    }
