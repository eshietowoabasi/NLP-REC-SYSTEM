"""RQ worker entry point: ``python -m app.worker``.

Jobs run inside a Flask application context so they can use the database session and
configuration exactly like request handlers. Because one worker process runs many jobs,
services that load NLP models cache them at module level so each model loads only once.
"""

from __future__ import annotations

from flask.cli import load_dotenv
from rq import Queue, Worker

from app import create_app
from app.extensions import get_redis


def main() -> None:
    """Start a worker listening on the configured queue until it is stopped."""
    # Same .env lookup as the ``flask`` CLI; variables already set (e.g. by Docker) win.
    load_dotenv()
    app = create_app()
    with app.app_context():
        connection = get_redis()
        queue = Queue(app.config["RQ_QUEUE_NAME"], connection=connection)
        Worker([queue], connection=connection).work(with_scheduler=False)


if __name__ == "__main__":
    main()
