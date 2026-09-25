"""Analysis session rules shared by the API and the session job.

A session is created with a name, a set of ready library documents and parameters. Parameters
are a snapshot of the default settings (plus any overrides) taken at creation, so re-reading a
session later always shows exactly how it was configured.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select

from app.extensions import db
from app.models import (
    AnalysisSession,
    Document,
    DocumentSession,
    DocumentStatus,
    NLPResult,
    NucCoreVersion,
    Recommendation,
    SourceCategory,
)
from app.schemas.sessions import SessionParameters
from app.settings import get_setting
from app.utils.errors import ApiError

# Settings copied into every session's parameter_config.
SNAPSHOT_KEYS = (
    "score_weights",
    "similarity_threshold",
    "max_recommendations",
    "min_topic_size",
    "evidence_per_recommendation",
    "sbert_model",
    "spacy_model",
)
PARAMETER_ALIASES = {"score_weights": "weights"}


def default_parameters() -> dict[str, Any]:
    """The current default settings, as stored in a session's ``parameter_config``."""
    return {PARAMETER_ALIASES.get(key, key): get_setting(key) for key in SNAPSHOT_KEYS}


def build_parameters(overrides: SessionParameters) -> dict[str, Any]:
    config = default_parameters()
    if overrides.weights is not None:
        config["weights"] = overrides.weights.model_dump()
    if overrides.similarity_threshold is not None:
        config["similarity_threshold"] = overrides.similarity_threshold
    if overrides.max_recommendations is not None:
        config["max_recommendations"] = overrides.max_recommendations
    return config


def active_nuc_core() -> NucCoreVersion | None:
    return db.session.scalar(select(NucCoreVersion).where(NucCoreVersion.is_active.is_(True)))


def check_documents(document_ids: list[int]) -> list[Document]:
    """The documents, in the given order, if all can be analysed; otherwise a 422 ApiError."""
    limit = int(get_setting("max_documents_per_session"))
    if len(document_ids) > limit:
        raise ApiError(
            "VALIDATION_ERROR",
            f"A session can include at most {limit} documents.",
            422,
            {"fields": {"document_ids": [f"Select at most {limit} documents."]}},
        )
    found = {
        d.id: d for d in db.session.scalars(select(Document).where(Document.id.in_(document_ids)))
    }
    problems: list[str] = []
    for document_id in document_ids:
        document = found.get(document_id)
        if document is None:
            problems.append(f"Document {document_id} does not exist.")
        elif document.source_category == SourceCategory.NUC_CORE:
            problems.append(f"“{document.title}” is a NUC core document and cannot be analysed.")
        elif document.processing_status != DocumentStatus.READY:
            problems.append(f"“{document.title}” is not ready ({document.processing_status}).")
    if problems:
        raise ApiError(
            "VALIDATION_ERROR",
            "Some selected documents cannot be analysed.",
            422,
            {"fields": {"document_ids": problems}},
        )
    return [found[document_id] for document_id in document_ids]


def link_documents(session: AnalysisSession, documents: list[Document]) -> None:
    session.document_links = [
        DocumentSession(document_id=document.id, processing_order=order)
        for order, document in enumerate(documents, start=1)
    ]


def clear_results(session: AnalysisSession) -> None:
    """Remove the outputs of a previous run (before a retry)."""
    db.session.execute(delete(Recommendation).where(Recommendation.session_id == session.id))
    db.session.execute(delete(NLPResult).where(NLPResult.session_id == session.id))
