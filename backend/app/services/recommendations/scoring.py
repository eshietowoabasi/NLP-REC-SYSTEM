"""Candidate building and recommendation scoring (spec §10; docs/DECISIONS.md, D4).

    composite = w_ner * ner_score + w_topic * topic_score + w_novelty * novelty_score

All three components are normalised to [0, 1] across the session's candidates:
- ner_score:   log(1 + m) / log(1 + max m), where m is the number of SKILL/TOOL/CERT
               mentions in the candidate's passages. The log keeps one very large
               theme from flattening every other score.
- topic_score: mean of the candidate's passage share and document spread, each
               relative to the session maximum, so a theme found in many sources
               outranks one repeated at length in a single document.
- novelty:     1 - max cosine similarity to the NUC core (spec §9).
"""
import math
from collections import Counter
from dataclasses import dataclass, field

import numpy as np

from ...models import OverlapStatus

DOMINANT_SKILL_SHARE = 0.2   # a skill in >= 20% of a topic's passages can name it
EVIDENCE_SKILLS = 10


@dataclass
class Candidate:
    topic_id: int
    topic_label: str
    embedding: np.ndarray
    passage_count: int
    distinct_passages: int
    document_ids: list[int]
    source_category_counts: dict
    keywords: list[str]
    representative_passages: list[dict]
    entity_mentions: Counter          # (name, label) -> mentions in the topic's passages
    entity_passages: Counter          # (name, label) -> distinct passages mentioning it
    # Filled in by scoring:
    title: str = ""
    description: str = ""
    ner_score: float = 0.0
    topic_score: float = 0.0
    novelty_score: float = 0.0
    max_similarity: float = 0.0
    composite_score: float = 0.0
    overlap_status: OverlapStatus = OverlapStatus.NO_SIGNIFICANT_OVERLAP
    core_matches: list = field(default_factory=list)


def candidate_title(candidate: Candidate) -> str:
    """Prefer a dominant skill's canonical name ("Cloud Computing") over the raw topic label."""
    threshold = max(1, DOMINANT_SKILL_SHARE * candidate.distinct_passages)
    ranked = sorted(
        ((name, label, n) for (name, label), n in candidate.entity_passages.items() if n >= threshold),
        key=lambda x: (x[1] != "SKILL", -x[2], x[0]),  # skills before tools/certs
    )
    names = [name for name, _, _ in ranked[:2]]
    if not names:
        return candidate.topic_label
    return " and ".join(names)


def candidate_description(candidate: Candidate) -> str:
    sources = ", ".join(f"{cat} ({n})" for cat, n in sorted(candidate.source_category_counts.items(), key=lambda kv: -kv[1]))
    skills = [name for (name, _), _ in candidate.entity_mentions.most_common(5)]
    parts = [
        f"Theme found in {candidate.passage_count} passages across {len(candidate.document_ids)} "
        f"source document(s): {sources}.",
        f"Key terms: {', '.join(candidate.keywords[:6])}.",
    ]
    if skills:
        parts.append(f"Most demanded skills and tools: {', '.join(skills)}.")
    return " ".join(parts)


def ner_scores(mentions: list[int]) -> list[float]:
    top = max(mentions, default=0)
    if top <= 0:
        return [0.0 for _ in mentions]
    return [round(math.log1p(m) / math.log1p(top), 4) for m in mentions]


def topic_scores(passage_counts: list[int], document_counts: list[int]) -> list[float]:
    max_passages = max(passage_counts, default=0) or 1
    max_docs = max(document_counts, default=0) or 1
    return [
        round(0.5 * p / max_passages + 0.5 * d / max_docs, 4)
        for p, d in zip(passage_counts, document_counts)
    ]


def composite_score(ner: float, topic: float, novelty: float, config: dict) -> float:
    value = config["ner_weight"] * ner + config["topic_weight"] * topic + config["novelty_weight"] * novelty
    return round(min(max(value, 0.0), 1.0), 4)


def score_candidates(candidates: list[Candidate], overlaps: list, config: dict) -> None:
    """Fill in scores, titles and descriptions in place. ``overlaps`` aligns with candidates."""
    ner = ner_scores([sum(c.entity_mentions.values()) for c in candidates])
    topic = topic_scores([c.passage_count for c in candidates], [len(c.document_ids) for c in candidates])
    used_titles = set()
    for candidate, overlap, n, t in zip(candidates, overlaps, ner, topic):
        candidate.ner_score = n
        candidate.topic_score = t
        candidate.novelty_score = overlap.novelty
        candidate.max_similarity = overlap.max_similarity
        candidate.overlap_status = overlap.status
        candidate.core_matches = overlap.matches
        candidate.composite_score = composite_score(n, t, overlap.novelty, config)
        title = candidate_title(candidate)
        if title.lower() in used_titles:
            title = f"{title}: {candidate.topic_label}"  # two themes around the same skill
        used_titles.add(title.lower())
        candidate.title = title[:255]
        candidate.description = candidate_description(candidate)


def rank_candidates(candidates: list[Candidate], limit: int) -> list[Candidate]:
    """Novel candidates first by composite score, then potential duplicates (spec §9:
    they must not appear as normal high-priority recommendations), capped at ``limit``."""
    def key(c):
        return (c.overlap_status is OverlapStatus.POTENTIAL_DUPLICATE, -c.composite_score, c.topic_id)

    return sorted(candidates, key=key)[:limit]
