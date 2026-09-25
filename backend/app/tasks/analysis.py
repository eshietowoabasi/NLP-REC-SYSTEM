"""Background job: run the analysis pipeline for one session.

Stages (``current_stage`` / ``progress_percent`` are saved as each one starts, so the UI can
poll them): validating → loading → keywords → skills → embeddings → themes → overlap →
scoring → completed. On failure the session keeps the failing stage and gets an error message.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import numpy as np
from sqlalchemy import select

from app.extensions import db
from app.models import (
    AnalysisSession,
    Document,
    DocumentSession,
    NLPResult,
    NLPResultType,
    Passage,
    Recommendation,
    RecommendationEvidence,
    SessionStatus,
    SkillPattern,
)
from app.services.analysis import (
    STAGE_PROGRESS,
    AnalysisOutput,
    AnalysisParameters,
    CorePassage,
    CorpusPassage,
    run_analysis,
)
from app.services.exceptions import AnalysisError
from app.services.ner.skills import SkillPatternSpec, build_skill_pipeline, canonical_lookup
from app.services.preprocessing.spacy_model import get_nlp
from app.services.recommendations.scoring import ScoreWeights, WeightsError
from app.sessions import active_nuc_core
from app.utils.time import utcnow

logger = logging.getLogger(__name__)


def unexpected_failure(stage: str | None) -> str:
    return (
        f"The analysis failed unexpectedly during the {stage or 'first'} stage. "
        "Try again; if it keeps failing, contact an administrator."
    )


class Progress:
    """Saves the current stage and progress of a session, and times each stage."""

    def __init__(self, session: AnalysisSession) -> None:
        self.session = session
        self.timings: dict[str, float] = {}
        self._started: tuple[str, float] | None = None

    def stage(self, name: str) -> None:
        now = time.perf_counter()
        if self._started:
            previous, started = self._started
            self.timings.setdefault(previous, round(now - started, 3))
        self._started = (name, now)
        self.session.current_stage = name
        self.session.progress_percent = STAGE_PROGRESS.get(name, self.session.progress_percent)
        db.session.commit()
        logger.info("Session %s: %s", self.session.id, name)


def load_parameters(config: dict[str, Any]) -> AnalysisParameters:
    try:
        weights = ScoreWeights.from_dict(config["weights"])
    except (KeyError, TypeError, WeightsError) as exc:
        raise AnalysisError(f"The session's score weights are invalid: {exc}") from exc
    return AnalysisParameters(
        weights=weights,
        similarity_threshold=float(config["similarity_threshold"]),
        max_recommendations=int(config["max_recommendations"]),
        min_topic_size=int(config["min_topic_size"]),
        evidence_per_recommendation=int(config["evidence_per_recommendation"]),
    )


def _vector(value: Any) -> np.ndarray:
    return np.asarray(value, dtype=np.float32)


def load_corpus(session: AnalysisSession) -> list[CorpusPassage]:
    rows = db.session.execute(
        select(Passage, Document.source_category)
        .join(Document, Document.id == Passage.document_id)
        .join(DocumentSession, DocumentSession.document_id == Document.id)
        .where(DocumentSession.session_id == session.id)
        .order_by(DocumentSession.processing_order, Passage.position)
    ).all()
    corpus = []
    for passage, category in rows:
        if passage.embedding is None:
            raise AnalysisError(
                f"A passage of document {passage.document_id} has no embedding; "
                "re-upload that document."
            )
        corpus.append(
            CorpusPassage(
                id=passage.id,
                document_id=passage.document_id,
                category=str(getattr(category, "value", category)),
                text=passage.text,
                normalised_text=passage.normalised_text,
                embedding=_vector(passage.embedding),
            )
        )
    return corpus


def load_core(document_id: int) -> list[CorePassage]:
    passages = db.session.scalars(
        select(Passage).where(Passage.document_id == document_id).order_by(Passage.position)
    )
    return [
        CorePassage(id=p.id, text=p.text, embedding=_vector(p.embedding))
        for p in passages
        if p.embedding is not None
    ]


def load_skill_patterns() -> list[SkillPatternSpec]:
    """The active skill patterns."""
    patterns = db.session.scalars(select(SkillPattern).where(SkillPattern.is_active.is_(True)))
    return [
        SkillPatternSpec(str(getattr(p.label, "value", p.label)), p.pattern, p.canonical_name)
        for p in patterns
    ]


def validate(session: AnalysisSession) -> tuple[AnalysisParameters, int]:
    """Check the session can run; returns its parameters and the NUC core document id."""
    parameters = load_parameters(session.parameter_config or {})
    if not session.document_links:
        raise AnalysisError("The session has no documents.")
    not_ready = [
        link.document.title
        for link in session.document_links
        if link.document.processing_status != "ready"
    ]
    if not_ready:
        raise AnalysisError(f"These documents are not ready: {', '.join(not_ready)}.")
    version = active_nuc_core()
    if version is None:
        raise AnalysisError(
            "There is no active NUC core reference. An administrator must upload one first."
        )
    session.nuc_core_version_id = version.id
    return parameters, version.document_id


def save_results(session: AnalysisSession, output: AnalysisOutput) -> None:
    for result_type, payload in (
        (NLPResultType.TFIDF, output.keywords),
        (NLPResultType.ENTITIES, output.entities),
        (NLPResultType.TOPICS, output.topics),
        (NLPResultType.SIMILARITY, output.similarity),
    ):
        db.session.add(NLPResult(session_id=session.id, result_type=result_type, payload=payload))
    for candidate in output.recommendations:
        recommendation = Recommendation(
            session_id=session.id,
            rank=candidate.rank,
            topic_id=candidate.topic_id,
            auto_title=candidate.auto_title,
            topic_title=candidate.auto_title,
            topic_description=candidate.description,
            keywords=candidate.keywords,
            skills=candidate.skills,
            ner_score=candidate.ner_score,
            topic_score=candidate.topic_score,
            novelty_score=candidate.novelty_score,
            composite_score=candidate.composite_score,
            max_similarity=candidate.max_similarity,
            closest_nuc_passage_id=candidate.closest_nuc_passage_id,
            overlap_status=candidate.overlap_status,
        )
        recommendation.evidence = [
            RecommendationEvidence(passage_id=passage_id, relevance_score=relevance)
            for passage_id, relevance in candidate.evidence
        ]
        db.session.add(recommendation)


def _fail(session_id: int, message: str) -> None:
    db.session.rollback()
    session = db.session.get(AnalysisSession, session_id)
    if session is not None:
        session.status = SessionStatus.FAILED
        session.error_message = message
        session.completed_at = utcnow()
        db.session.commit()


def run_session(session_id: int) -> None:
    """Run the full analysis for the session with id ``session_id``."""
    session = db.session.get(AnalysisSession, session_id)
    if session is None or session.status != SessionStatus.PROCESSING:
        logger.info("Skipping session %s (missing or not queued)", session_id)
        return
    session.started_at = utcnow()
    session.completed_at = None
    session.error_message = None
    progress = Progress(session)
    started = time.perf_counter()
    try:
        progress.stage("validating")
        parameters, core_document_id = validate(session)
        config = session.parameter_config

        progress.stage("loading")
        corpus = load_corpus(session)
        core = load_core(core_document_id)
        specs = load_skill_patterns()
        model_name = config.get("spacy_model", "en_core_web_sm")
        skill_nlp = build_skill_pipeline(model_name, specs)
        canonical = canonical_lookup(specs, get_nlp(model_name))

        output = run_analysis(
            corpus, core, parameters, skill_nlp, canonical, on_stage=progress.stage
        )

        save_results(session, output)
        progress.timings.update(output.stage_timings)
        session.stage_timings = progress.timings
        session.status = SessionStatus.COMPLETED
        session.current_stage = "completed"
        session.progress_percent = 100
        session.completed_at = utcnow()
        db.session.commit()
        logger.info(
            "Session %s completed in %.1fs: %s recommendations (%s)",
            session_id,
            time.perf_counter() - started,
            len(output.recommendations),
            output.stage_timings,
        )
    except AnalysisError as exc:
        logger.info("Session %s failed at %s: %s", session_id, session.current_stage, exc)
        _fail(session_id, str(exc))
    except Exception:
        stage = session.current_stage
        logger.exception("Session %s failed unexpectedly at %s", session_id, stage)
        _fail(session_id, unexpected_failure(stage))
    finally:
        db.session.remove()
