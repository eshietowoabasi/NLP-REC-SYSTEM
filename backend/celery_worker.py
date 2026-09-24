from celery.signals import worker_process_init
from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402
from app.tasks import warm_up  # noqa: E402

app = create_app()
celery = app.extensions["celery"]


@worker_process_init.connect
def _warm_up_worker(**_):
    warm_up(app)
