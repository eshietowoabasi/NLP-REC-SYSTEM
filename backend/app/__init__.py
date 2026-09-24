import os

from flask import Flask

from .config import CONFIGS, ProductionConfig
from .extensions import db, login_manager, migrate


def create_app(config_name=None):
    config_name = config_name or os.environ.get("APP_CONFIG", "development")
    config_class = CONFIGS[config_name]
    if config_class is ProductionConfig:
        ProductionConfig.validate()

    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    login_manager.init_app(app)

    from .tasks import init_celery

    init_celery(app)

    from . import models  # noqa: F401  (register models with SQLAlchemy)
    from .routes import register_blueprints
    from .utils.errors import register_error_handlers
    from .cli import register_cli

    register_blueprints(app)
    register_error_handlers(app)
    register_cli(app)

    return app
