"""Celery integration (docs/DECISIONS.md, D3).

Worker: ``celery -A celery_worker.celery worker --loglevel=info``
"""
from celery import Celery, Task, shared_task


def init_celery(app):
    class FlaskTask(Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery = Celery(app.name, task_cls=FlaskTask)
    celery.config_from_object(app.config["CELERY"])
    celery.set_default()
    app.extensions["celery"] = celery
    return celery


@shared_task(name="analysis.fail_stale_runs", ignore_result=True)
def fail_stale_runs_task() -> None:
    from flask import current_app

    from ..services.analysis import fail_stale_runs

    failed = fail_stale_runs(current_app.config["STALE_RUN_MINUTES"])
    if failed:
        current_app.logger.warning("Marked stale analysis sessions as failed: %s", failed)


@shared_task(name="analysis.run", ignore_result=True)
def run_analysis_task(session_id: int) -> None:
    from ..services.analysis import run_analysis

    run_analysis(session_id)


def warm_up(app):
    """Load models and trigger UMAP's JIT compilation once per worker process.

    Without this the first analysis in each worker pays ~20 s of numba compilation.
    """
    import numpy as np

    from ..services.embeddings import get_embedder
    from ..services.ner import load_ner_nlp
    from ..services.preprocessing import load_nlp
    from ..services.topics import Passage, model_topics

    with app.app_context():
        load_nlp(app.config["SPACY_MODEL"])
        load_ner_nlp(app.config["SPACY_MODEL"])
        embedder = get_embedder(app.config["EMBEDDING_BACKEND"], app.config["SBERT_MODEL"])
        embedder.encode(["warm up"])
        rng = np.random.default_rng(0)
        vectors = rng.normal(size=(60, 16)).astype(np.float32)
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
        model_topics([Passage(f"warm up passage number {i} text", 0, "") for i in range(60)], vectors)
