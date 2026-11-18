"""Background job: load the NUC catalogue shipped with SkillBridge (see app/nuc_catalogue.py)."""

from __future__ import annotations

import logging

from app.extensions import db
from app.nuc_catalogue import BUNDLED_CATALOGUE, load_catalogue

logger = logging.getLogger(__name__)


def load_bundled_catalogue() -> None:
    """Create the catalogue's programmes and queue their NUC cores for processing."""
    try:
        summary = load_catalogue(BUNDLED_CATALOGUE, report=logger.info)
        logger.info(
            "NUC catalogue: %s programmes created, %s NUC cores queued, %s skipped, %s failed",
            len(summary.created),
            len(summary.queued),
            len(summary.skipped),
            len(summary.failed),
        )
    finally:
        db.session.remove()
