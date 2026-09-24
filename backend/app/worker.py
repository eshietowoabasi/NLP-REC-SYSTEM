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
from app.extensions import get_redis

Worker = SimpleWorker


def main() -> None:
    """Start a worker listening on the configured queue until it is stopped."""
    app = create_app()
    with app.app_context():
        connection = get_redis()
        queue = Queue(app.config["RQ_QUEUE_NAME"], connection=connection)
        worker = Worker([queue], connection=connection)
        # Job timeouts use SIGALRM, which Windows lacks; fall back to a timer thread there.
        worker.death_penalty_class = (
            TimerDeathPenalty if os.name == "nt" else UnixSignalDeathPenalty
        )
        worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
