"""Analysis session rules shared by the API and the session job.

A session is created with a name, a set of ready library documents and parameters. Parameters
are a snapshot of the default settings (plus any overrides) taken at creation, so re-reading a
session later always shows exactly how it was configured.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select

from app.access import can_see_programme, programme_scope
from app.extensions import db
from app.models import (
    AnalysisSession,
    Document,
    DocumentSession,
    DocumentStatus,
    NLPResult,
    NucCoreVersion,
    Programme,
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
    # Current default settings copied into each session.
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


def default_programme() -> Programme:
    # Return the default programme, recreating it for legacy/test workflows if needed.
    programme = db.session.scalar(
        select(Programme).where(Programme.is_active.is_(True)).order_by(Programme.id).limit(1)
    )
    if programme is not None:
        return programme

    programme = Programme(
        name="Computer Science",
        discipline_code="CSC",
        faculty="Faculty of Computing",
        description="Default programme for legacy SkillBridge workflows.",
        country="Nigeria",
        is_active=True,
    )
    db.session.add(programme)
    db.session.flush()
    return programme


def default_programme_for_user() -> Programme | None:
    """The programme a new session or upload uses when none is chosen.

    The default programme if the user may see it, else the first of their own programmes
    (by id); None for a planner or viewer with no programmes.
    """
    programme = default_programme()
    if can_see_programme(programme.id):
        return programme
    scope = programme_scope() or set()
    return db.session.scalar(
        select(Programme)
        .where(Programme.is_active.is_(True), Programme.id.in_(scope))
        .order_by(Programme.id)
        .limit(1)
    )


def active_programme(programme_id: int, field: str = "programme_id") -> Programme:
    """The active programme with this id that the user may work on, or a 422 on ``field``."""
    programme = db.session.get(Programme, programme_id)
    if programme is None or not programme.is_active or not can_see_programme(programme.id):
        raise ApiError(
            "VALIDATION_ERROR",
            "Some fields are invalid.",
            422,
            {"fields": {field: ["Choose an active programme."]}},
        )
    return programme


def active_nuc_core(programme_id: int | None = None) -> NucCoreVersion | None:
    # Return the active curriculum benchmark for a programme, with legacy fallback.
    if programme_id is None:
        legacy = db.session.scalar(
            select(NucCoreVersion)
            .where(NucCoreVersion.is_active.is_(True))
            .order_by(NucCoreVersion.id.desc())
            .limit(1)
        )
        if legacy is not None:
            return legacy
        programme_id = default_programme().id

    return db.session.scalar(
        select(NucCoreVersion).where(
            NucCoreVersion.programme_id == programme_id,
            NucCoreVersion.is_active.is_(True),
        )
    )


def check_documents(document_ids: list[int], programme: Programme) -> list[Document]:
    """The documents, in the given order, if all can be analysed; otherwise a 422 ApiError.

    A session may use the programme's own documents and general documents (no programme), never
    another programme's: a Nursing Science analysis must not pick up computing job adverts.
    """
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
        elif document.programme_id is not None and document.programme_id != programme.id:
            other = document.programme.name if document.programme else "another programme"
            problems.append(f"“{document.title}” belongs to {other}, not {programme.name}.")
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
