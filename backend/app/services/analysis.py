"""The analysis pipeline for one session, on in-memory data (no database).

    keywords → skills → embeddings → themes (topics) → overlap → scoring

The session job (``app.tasks.analysis``) loads passages from the database, calls
:func:`run_analysis` and stores the returned results. Keeping the pipeline free of database
access makes it testable on synthetic data and lets the benchmark time it directly.
"""

from __future__ import annotations

import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray
from spacy.language import Language

from app.models.enums import OverlapStatus
from app.services.embeddings.encoder import Encoder
from app.services.exceptions import AnalysisError
from app.services.ner.skills import (
    aggregate_skills,
    extract_mentions,
    ranked_skills,
    skills_in_passages,
)
from app.services.preprocessing.normalise import StopWords
from app.services.recommendations.scoring import (
    ScoreWeights,
    composite_score,
    document_weights,
    rank,
    scale_skill_demand,
    scale_theme_strength,
    skill_demand_raw,
    theme_strength_raw,
)
from app.services.similarity.overlap import compare_to_core
from app.services.tfidf.keywords import extract_keywords
from app.services.topics.modelling import centroid, fit_topics, representative_passages
from app.services.topics.naming import name_topics
from app.services.topics.surface import SurfaceForms
from app.services.topics.titles import excerpt, keyword_label, make_description, make_title

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
class CoreCourse:
    """A course of the active NUC core (e.g. "SEN 304"), embedded as a whole."""

    id: int
    code: str
    title: str
    embedding: NDArray[np.float32]


@dataclass(frozen=True)
class TopicNaming:
    """The catalogue of course-style names and what is needed to compare topics with it."""

    names: list[str]
    name_vectors: NDArray[np.float32]
    encoder: Encoder  # embeds each topic's keywords as a phrase


@dataclass(frozen=True)
class AnalysisParameters:
    weights: ScoreWeights
    similarity_threshold: float = 0.80
    max_recommendations: int = 20
    min_topic_size: int = 5
    evidence_per_recommendation: int = 8
    random_state: int = 42
    # Active domain stop words, removed from the stored normalised text before TF-IDF and
    # topic words, so stop words added after a document was parsed still apply.
    stop_words: frozenset[str] = frozenset()


def without_stop_words(text: str, stop_words: frozenset[str]) -> str:
    """Drop stop words from space-separated normalised text."""
    if not stop_words:
        return text
    return " ".join(token for token in text.split() if token not in stop_words)


@dataclass
class Candidate:
    """A candidate course topic (one BERTopic theme) with its scores."""

    topic_id: int
    auto_title: str  # course-style name, or the keyword title when no name is close enough
    keyword_title: str
    name_similarity: float | None
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
    closest_nuc_course_id: int | None = None
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


def unique_keywords(keywords: list[tuple[str, float]], labels: list[str]) -> list[dict[str, Any]]:
    """Keywords with their display labels, dropping repeated labels ("datum" and "data")."""
    seen: set[str] = set()
    result = []
    for (term, weight), label in zip(keywords, labels, strict=True):
        if label.lower() in seen:
            continue
        seen.add(label.lower())
        result.append({"term": term, "label": label, "weight": round(weight, 6)})
    return result


def run_analysis(
    corpus: list[CorpusPassage],
    core: list[CorePassage],
    parameters: AnalysisParameters,
    skill_nlp: Language,
    canonical_names: dict[str, str],
    on_stage: StageCallback | None = None,
    courses: list[CoreCourse] | None = None,
    *,
    text_nlp: Language | None = None,
    naming: TopicNaming | None = None,
    document_titles: dict[int, str] | None = None,
) -> AnalysisOutput:
    """Run the keyword, skill, theme, overlap and scoring stages.

    ``on_stage(name)`` is called as each stage starts (for progress reporting).
    ``canonical_names`` maps lowercase terms to canonical skill names, for titles.
    ``courses`` are the NUC core's courses: when given, each theme is compared with whole
    courses (similarity, novelty and duplicate status come from the closest course); without
    them, it is compared with individual NUC core passages. The closest passage is always
    recorded, for side-by-side evidence.
    ``text_nlp`` (a spaCy pipeline with the lemmatiser) turns keyword lemmas back into the words
    as written; ``naming`` gives topics course-style names; ``document_titles`` are used in the
    plain-language descriptions. All three are optional (tests run without them).
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
    normalised = [without_stop_words(p.normalised_text, parameters.stop_words) for p in corpus]
    categories = [p.category for p in corpus]
    document_ids = [p.document_id for p in corpus]

    stage("keywords")
    keywords = extract_keywords(normalised, categories)

    stage("skills")
    mentions = extract_mentions(skill_nlp, texts)
    skill_stats = aggregate_skills(mentions, document_ids, categories)
    document_frequency = {name: s.document_frequency for name, s in skill_stats.items()}
    corpus_mentions = {name: s.mentions for name, s in skill_stats.items()}
    entities = {
        "skills": [s.as_dict() for s in ranked_skills(skill_stats)],
        "passages_with_skills": sum(1 for m in mentions if m),
        "passage_count": len(corpus),
        "document_count": len(set(document_ids)),
    }

    stage("embeddings")
    embeddings = np.vstack([p.embedding for p in corpus]).astype(np.float32)
    core_embeddings = np.vstack([p.embedding for p in core]).astype(np.float32)
    courses = courses or []
    course_embeddings = (
        np.vstack([c.embedding for c in courses]).astype(np.float32) if courses else None
    )
    if embeddings.shape[1] != core_embeddings.shape[1] or (
        course_embeddings is not None and course_embeddings.shape[1] != embeddings.shape[1]
    ):
        raise AnalysisError(
            "The documents and the NUC core were embedded with different models. "
            "Re-upload the NUC core so both use the current embedding model."
        )

    stage("themes")
    model = fit_topics(normalised, embeddings, parameters.min_topic_size, parameters.random_state)
    # Theme strength counts documents equally: each passage weighs 1 / passages in its document.
    weights = np.asarray(document_weights(document_ids))
    total = float(weights[model.assignments != -1].sum())

    member_indices = sorted({i for topic in model.topics for i in topic.members})
    surfaces = (
        SurfaceForms(StopWords.build(parameters.stop_words)).learn(
            text_nlp, [texts[i] for i in member_indices]
        )
        if text_nlp is not None
        else None
    )
    titles = document_titles or {}
    category_of = dict(zip(document_ids, categories, strict=True))
    total_documents = len(set(document_ids))

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
        passages_per_document = Counter(document_ids[i] for i in members)
        document_count = len(passages_per_document)
        mean_probability = float(np.mean(model.probabilities[members]))
        top_keywords = topic.keywords[:TOP_KEYWORDS_PER_CANDIDATE]
        keyword_labels = [keyword_label(w, canonical_names, surfaces) for w, _ in top_keywords]
        keyword_title = make_title(words, canonical_names, surfaces)
        candidates.append(
            Candidate(
                topic_id=topic.topic_id,
                auto_title=keyword_title,
                keyword_title=keyword_title,
                name_similarity=None,
                description=make_description(
                    document_count=document_count,
                    total_documents=total_documents,
                    documents_by_category=dict(
                        Counter(category_of[d] for d in passages_per_document)
                    ),
                    advert_titles=[
                        titles.get(d, "")
                        for d, _ in passages_per_document.most_common()
                        if category_of[d] == "job_market"
                    ],
                    skills=[name for name, _, _ in top_skills],
                    keywords=keyword_labels,
                ),
                keywords=unique_keywords(top_keywords, keyword_labels),
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
                ner_raw=skill_demand_raw(
                    [(name, count) for name, _, count in top_skills],
                    document_frequency,
                    corpus_mentions,
                ),
                topic_raw=theme_strength_raw(
                    float(weights[members].sum()), total, mean_probability
                ),
            )
        )

    if naming is not None and naming.names and candidates:
        phrases = [", ".join(k["label"] for k in c.keywords[:8]) for c in candidates]
        chosen = name_topics(
            np.vstack(centres),
            naming.encoder.encode(phrases),
            naming.names,
            naming.name_vectors,
        )
        for candidate, topic_name in zip(candidates, chosen, strict=True):
            candidate.name_similarity = round(topic_name.similarity, 4)
            if topic_name.name:
                candidate.auto_title = topic_name.name

    stage("overlap")
    centre_matrix = np.vstack(centres)
    threshold = parameters.similarity_threshold
    passage_overlaps = compare_to_core(centre_matrix, core_embeddings, threshold)
    course_overlaps = (
        compare_to_core(centre_matrix, course_embeddings, threshold)
        if course_embeddings is not None
        else [None] * len(candidates)
    )
    for candidate, by_passage, by_course in zip(
        candidates, passage_overlaps, course_overlaps, strict=True
    ):
        overlap = by_course or by_passage
        candidate.max_similarity = overlap.max_similarity
        candidate.novelty_score = overlap.novelty
        candidate.overlap_status = overlap.status
        candidate.closest_nuc_passage_id = core[by_passage.closest_index].id
        if by_course is not None:
            candidate.closest_nuc_course_id = courses[by_course.closest_index].id

    stage("scoring")
    for candidate, ner, topic_score in zip(
        candidates,
        scale_skill_demand([c.ner_raw for c in candidates]),
        scale_theme_strength([c.topic_raw for c in candidates]),
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
    course_by_id = {c.id: c for c in courses}
    passage_by_id = {p.id: p for p in corpus}
    return AnalysisOutput(
        keywords=keywords,
        entities=entities,
        topics={
            "topic_count": len(candidates),
            "outlier_passages": int(np.sum(model.assignments == -1)),
            "modelled_passages": len(corpus),
            # Near-duplicate topics merged after clustering (groups of original topic ids).
            "merged_topics": model.merged,
            "topics": [
                {
                    "topic_id": c.topic_id,
                    "title": c.auto_title,
                    "keyword_title": c.keyword_title,
                    "name_similarity": c.name_similarity,
                    "keywords": c.keywords,
                    "size": c.size,
                    "document_count": c.document_count,
                    "mean_probability": round(c.mean_probability, 6),
                    "strength_raw": round(c.topic_raw, 6),
                    "strength": round(c.topic_score, 6),
                    "skill_demand_raw": round(c.ner_raw, 6),
                    "skill_demand": round(c.ner_score, 6),
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
            # "course": themes compared with whole NUC courses; "passage": with passages.
            "basis": "course" if courses else "passage",
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
                    "closest_nuc_course": (
                        {
                            "id": course.id,
                            "code": course.code,
                            "title": course.title,
                        }
                        if (course := course_by_id.get(c.closest_nuc_course_id or -1))
                        else None
                    ),
                }
                for c in ranked
            ],
        },
        candidates=ranked,
        recommendations=ranked[: parameters.max_recommendations],
        stage_timings=timings,
    )
