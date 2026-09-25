"""The analysis pipeline for one session, on in-memory data (no database).

    keywords → skills → embeddings → themes → overlap → scoring

The session job (``app.tasks.analysis``) loads passages from the database, calls
:func:`run_analysis` and stores the returned results. Keeping the pipeline free of database
access makes it testable on synthetic data and lets the benchmark time it directly.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray
from spacy.language import Language

from app.models.enums import OverlapStatus
from app.services.exceptions import AnalysisError
from app.services.ner.skills import (
    aggregate_skills,
    extract_mentions,
    ranked_skills,
    skills_in_passages,
)
from app.services.recommendations.scoring import (
    ScoreWeights,
    composite_score,
    min_max,
    rank,
    skill_demand_raw,
    theme_strength_raw,
)
from app.services.similarity.overlap import compare_to_core
from app.services.tfidf.keywords import extract_keywords
from app.services.topics.modelling import centroid, fit_topics, representative_passages
from app.services.topics.titles import excerpt, make_description, make_title

TOP_SKILLS_PER_CANDIDATE = 10
TOP_KEYWORDS_PER_CANDIDATE = 10
SAMPLE_PASSAGES_PER_TOPIC = 3

# Stages in order, with the progress (percent) reached when each one starts.
STAGES: tuple[tuple[str, int], ...] = (
    ("validating", 5),
    ("loading", 10),
    ("keywords", 20),
    ("skills", 35),
    ("embeddings", 50),
    ("themes", 55),
    ("overlap", 80),
    ("scoring", 90),
)
STAGE_PROGRESS = dict(STAGES)


@dataclass(frozen=True)
class CorpusPassage:
    """A passage of a (non-NUC) document selected for the session."""

    id: int
    document_id: int
    category: str
    text: str
    normalised_text: str
    embedding: NDArray[np.float32]


@dataclass(frozen=True)
class CorePassage:
    """A passage of the active NUC core document."""

    id: int
    text: str
    embedding: NDArray[np.float32]


@dataclass(frozen=True)
class AnalysisParameters:
    weights: ScoreWeights
    similarity_threshold: float = 0.80
    max_recommendations: int = 20
    min_topic_size: int = 5
    evidence_per_recommendation: int = 8
    random_state: int = 42


@dataclass
class Candidate:
    """A candidate course topic (one BERTopic theme) with its scores."""

    topic_id: int
    auto_title: str
    description: str
    keywords: list[dict[str, Any]]
    skills: list[dict[str, Any]]
    member_passage_ids: list[int]
    document_count: int
    size: int
    mean_probability: float
    evidence: list[tuple[int, float]]  # (passage id, relevance)
    ner_raw: float = 0.0
    topic_raw: float = 0.0
    ner_score: float = 0.0
    topic_score: float = 0.0
    novelty_score: float = 0.0
    composite_score: float = 0.0
    max_similarity: float = 0.0
    closest_nuc_passage_id: int | None = None
    overlap_status: OverlapStatus = OverlapStatus.NO_SIGNIFICANT_OVERLAP
    rank: int | None = None


@dataclass
class AnalysisOutput:
    keywords: dict[str, Any]
    entities: dict[str, Any]
    topics: dict[str, Any]
    similarity: dict[str, Any]
    candidates: list[Candidate]  # every candidate, ranked
    recommendations: list[Candidate]  # the top ``max_recommendations``
    stage_timings: dict[str, float] = field(default_factory=dict)


StageCallback = Callable[[str], None]


def run_analysis(
    corpus: list[CorpusPassage],
    core: list[CorePassage],
    parameters: AnalysisParameters,
    skill_nlp: Language,
    canonical_names: dict[str, str],
    on_stage: StageCallback | None = None,
) -> AnalysisOutput:
    """Run the keyword, skill, theme, overlap and scoring stages.

    ``on_stage(name)`` is called as each stage starts (for progress reporting).
    ``canonical_names`` maps lowercase terms to canonical skill names, for titles.
    Raises AnalysisError when the data cannot produce recommendations.
    """
    if not corpus:
        raise AnalysisError("The selected documents have no extracted passages.")
    if not core:
        raise AnalysisError("The active NUC core reference has no extracted passages.")

    timings: dict[str, float] = {}
    current: list[tuple[str, float]] = []

    def stage(name: str) -> None:
        now = time.perf_counter()
        if current:
            previous, started = current.pop()
            timings[previous] = round(now - started, 3)
        current.append((name, now))
        if on_stage:
            on_stage(name)

    texts = [p.text for p in corpus]
    normalised = [p.normalised_text for p in corpus]
    categories = [p.category for p in corpus]
    document_ids = [p.document_id for p in corpus]

    stage("keywords")
    keywords = extract_keywords(normalised, categories)

    stage("skills")
    mentions = extract_mentions(skill_nlp, texts)
    skill_stats = aggregate_skills(mentions, document_ids, categories)
    document_frequency = {name: s.document_frequency for name, s in skill_stats.items()}
    entities = {
        "skills": [s.as_dict() for s in ranked_skills(skill_stats)],
        "passages_with_skills": sum(1 for m in mentions if m),
        "passage_count": len(corpus),
        "document_count": len(set(document_ids)),
    }

    stage("embeddings")
    embeddings = np.vstack([p.embedding for p in corpus]).astype(np.float32)
    core_embeddings = np.vstack([p.embedding for p in core]).astype(np.float32)
    if embeddings.shape[1] != core_embeddings.shape[1]:
        raise AnalysisError(
            "The documents and the NUC core were embedded with different models. "
            "Re-upload the NUC core so both use the current embedding model."
        )

    stage("themes")
    model = fit_topics(normalised, embeddings, parameters.min_topic_size, parameters.random_state)
    total = model.non_outlier_count

    candidates: list[Candidate] = []
    centres: list[NDArray[np.float32]] = []  # one topic centre per candidate, for overlap
    for topic in model.topics:
        members = topic.members
        centre = centroid(embeddings[members])
        centres.append(centre)
        evidence_idx = representative_passages(
            members, embeddings, centre, parameters.evidence_per_recommendation
        )
        words = [word for word, _ in topic.keywords]
        top_skills = skills_in_passages(mentions, members, TOP_SKILLS_PER_CANDIDATE)
        document_count = len({document_ids[i] for i in members})
        mean_probability = float(np.mean(model.probabilities[members]))
        candidates.append(
            Candidate(
                topic_id=topic.topic_id,
                auto_title=make_title(words, canonical_names),
                description=make_description(
                    words, canonical_names, len(members), document_count, texts[evidence_idx[0][0]]
                ),
                keywords=[
                    {"term": w, "weight": round(weight, 6)}
                    for w, weight in topic.keywords[:TOP_KEYWORDS_PER_CANDIDATE]
                ],
                skills=[
                    {
                        "name": name,
                        "label": label,
                        "mentions": count,
                        "document_frequency": document_frequency.get(name, 0),
                    }
                    for name, label, count in top_skills
                ],
                member_passage_ids=[corpus[i].id for i in members],
                document_count=document_count,
                size=len(members),
                mean_probability=mean_probability,
                evidence=[(corpus[i].id, relevance) for i, relevance in evidence_idx],
                ner_raw=skill_demand_raw([name for name, _, _ in top_skills], document_frequency),
                topic_raw=theme_strength_raw(len(members), total, mean_probability),
            )
        )

    stage("overlap")
    for candidate, overlap in zip(
        candidates,
        compare_to_core(np.vstack(centres), core_embeddings, parameters.similarity_threshold),
        strict=True,
    ):
        candidate.max_similarity = overlap.max_similarity
        candidate.novelty_score = overlap.novelty
        candidate.closest_nuc_passage_id = core[overlap.closest_index].id
        candidate.overlap_status = overlap.status

    stage("scoring")
    for candidate, ner, topic_score in zip(
        candidates,
        min_max([c.ner_raw for c in candidates]),
        min_max([c.topic_raw for c in candidates]),
        strict=True,
    ):
        candidate.ner_score = ner
        candidate.topic_score = topic_score
        candidate.composite_score = composite_score(
            ner, topic_score, candidate.novelty_score, parameters.weights
        )
    order = rank([c.composite_score for c in candidates], [c.size for c in candidates])
    ranked = [candidates[i] for i in order]
    for position, candidate in enumerate(ranked, start=1):
        candidate.rank = position
    stage("done")
    timings.pop("done", None)

    core_by_id = {p.id: p for p in core}
    passage_by_id = {p.id: p for p in corpus}
    return AnalysisOutput(
        keywords=keywords,
        entities=entities,
        topics={
            "topic_count": len(candidates),
            "outlier_passages": int(np.sum(model.assignments == -1)),
            "modelled_passages": len(corpus),
            "topics": [
                {
                    "topic_id": c.topic_id,
                    "title": c.auto_title,
                    "keywords": c.keywords,
                    "size": c.size,
                    "document_count": c.document_count,
                    "mean_probability": round(c.mean_probability, 6),
                    "strength_raw": round(c.topic_raw, 6),
                    "strength": round(c.topic_score, 6),
                    "samples": [
                        {
                            "passage_id": pid,
                            "document_id": passage_by_id[pid].document_id,
                            "text": excerpt(passage_by_id[pid].text, 400),
                        }
                        for pid, _ in c.evidence[:SAMPLE_PASSAGES_PER_TOPIC]
                    ],
                }
                for c in sorted(candidates, key=lambda c: -c.size)
            ],
        },
        similarity={
            "threshold": parameters.similarity_threshold,
            "candidates": [
                {
                    "topic_id": c.topic_id,
                    "title": c.auto_title,
                    "max_similarity": round(c.max_similarity, 6),
                    "novelty": round(c.novelty_score, 6),
                    "overlap_status": c.overlap_status.value,
                    "closest_nuc_passage": {
                        "id": c.closest_nuc_passage_id,
                        "text": (
                            excerpt(core_by_id[c.closest_nuc_passage_id].text, 400)
                            if c.closest_nuc_passage_id in core_by_id
                            else ""
                        ),
                    },
                }
                for c in ranked
            ],
        },
        candidates=ranked,
        recommendations=ranked[: parameters.max_recommendations],
        stage_timings=timings,
    )
