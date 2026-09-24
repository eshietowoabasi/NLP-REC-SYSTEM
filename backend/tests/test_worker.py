"""Tests for the RQ worker entry point."""

from __future__ import annotations

import pytest

from app import worker


class FakeWorker:
    """Records how the worker was built instead of connecting to Redis."""

    instances: list[FakeWorker] = []

    def __init__(self, queues, connection) -> None:
        self.queues = queues
        self.connection = connection
        self.work_kwargs: dict | None = None
        FakeWorker.instances.append(self)

    def work(self, **kwargs) -> None:
        self.work_kwargs = kwargs


def test_worker_listens_on_configured_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setattr(worker, "Worker", FakeWorker)
    monkeypatch.setattr(worker, "load_dotenv", lambda: None)
    FakeWorker.instances.clear()

    worker.main()

    (started,) = FakeWorker.instances
    assert [queue.name for queue in started.queues] == ["default"]
    assert started.work_kwargs == {"with_scheduler": False}
