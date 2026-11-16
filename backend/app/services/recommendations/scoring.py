"""Score normalisation, composite scoring and ranking of candidate topics.

    composite = w_ner × skill_demand + w_topic × theme_strength + w_novelty × novelty

* skill demand (NER): for each of the candidate's top skills, the distinct documents in the
  session that mention it × the share of the skill's mentions that fall in this theme
  (specificity); sum, apply log1p, then min-max over the candidates that have skills
  (candidates without skills score 0).
* theme strength (topic): (document-weighted topic passages / all non-outlier passages) × mean
  topic probability, square root, then min-max normalise across candidates.
* novelty: 1 - max similarity to the NUC core (already in [0, 1]).

Min-max normalisation maps the lowest value to 0 and the highest to 1; if all candidates have
the same value they all get 1.0 (nobody is penalised for a tie).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

WEIGHT_TOLERANCE = 0.001
DEFAULT_WEIGHTS = {"ner": 0.40, "topic": 0.35, "novelty": 0.25}


class WeightsError(ValueError):
    """The three weights are out of range or do not sum to 1."""


@dataclass(frozen=True)
class ScoreWeights:
    ner: float
    topic: float
    novelty: float

    def __post_init__(self) -> None:
        for name in ("ner", "topic", "novelty"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise WeightsError(f"The {name} weight must be between 0 and 1.")
        total = self.ner + self.topic + self.novelty
        if abs(total - 1.0) > WEIGHT_TOLERANCE:
            raise WeightsError(f"The weights must sum to 1.0 (they sum to {total:.3f}).")

    @classmethod
    def from_dict(cls, values: dict[str, float]) -> ScoreWeights:
        return cls(
            ner=float(values["ner"]), topic=float(values["topic"]), novelty=float(values["novelty"])
        )

    def as_dict(self) -> dict[str, float]:
        return {"ner": self.ner, "topic": self.topic, "novelty": self.novelty}


def min_max(values: Sequence[float]) -> list[float]:
    """Scale to [0, 1]; all-equal (or single) values become 1.0."""
    if not values:
        return []
    low, high = min(values), max(values)
    if math.isclose(high, low, rel_tol=0.0, abs_tol=1e-12):
        return [1.0] * len(values)
    return [(value - low) / (high - low) for value in values]


def skill_demand_raw(
    top_skills: Sequence[tuple[str, int]],
    document_frequency: dict[str, int],
    corpus_mentions: dict[str, int],
) -> float:
    """Specificity-weighted skill demand of a candidate (before scaling).

    For each of the candidate's top skills ``(name, mentions in this theme)``: the number of
    documents mentioning the skill, weighted by the share of the skill's mentions that fall in
    this theme. Summed, then ``log1p``. A skill that appears everywhere (e.g. "Agile") adds
    little to any one theme; a skill concentrated in the theme adds its full demand.
    """
    total = 0.0
    for name, in_theme in top_skills:
        corpus = max(corpus_mentions.get(name, 0), in_theme, 1)
        total += document_frequency.get(name, 0) * (in_theme / corpus)
    return math.log1p(total)


def scale_skill_demand(raw: Sequence[float]) -> list[float]:
    """Min-max over the candidates that have skills; candidates without skills stay at 0.

    Themes with no recognised skills would otherwise set the minimum and push every other
    theme towards 1.
    """
    with_skills = [index for index, value in enumerate(raw) if value > 0]
    scaled = min_max([raw[index] for index in with_skills])
    result = [0.0] * len(raw)
    for index, value in zip(with_skills, scaled, strict=True):
        result[index] = value
    return result


def scale_theme_strength(raw: Sequence[float]) -> list[float]:
    """Square root, then min-max: shrinks the lead of the largest theme, keeps the order."""
    return min_max([math.sqrt(max(value, 0.0)) for value in raw])


def theme_strength_raw(
    topic_size: float, total_non_outlier: float, mean_probability: float
) -> float:
    """Share of the modelled passages in this topic, weighted by how confidently they belong.

    Sizes are document-weighted passage counts (see :func:`document_weights`), so a long
    document cannot dominate by its number of passages alone.
    """
    if total_non_outlier <= 0:
        return 0.0
    return (topic_size / total_non_outlier) * mean_probability


def document_weights(document_ids: Sequence[int]) -> list[float]:
    """Weight of each passage = 1 / (number of passages in its document).

    Every document then contributes a total weight of 1, however long it is: a 116-passage
    policy PDF counts as much as a 6-passage job advert.
    """
    counts: dict[int, int] = {}
    for document_id in document_ids:
        counts[document_id] = counts.get(document_id, 0) + 1
    return [1.0 / counts[document_id] for document_id in document_ids]


def composite_score(ner: float, topic: float, novelty: float, weights: ScoreWeights) -> float:
    value = weights.ner * ner + weights.topic * topic + weights.novelty * novelty
    return float(min(max(value, 0.0), 1.0))


def rank(composites: Sequence[float], tie_breakers: Sequence[float]) -> list[int]:
    """Indices by composite (highest first); ties go to the higher ``tie_breakers`` value."""
    return sorted(range(len(composites)), key=lambda i: (-composites[i], -tie_breakers[i], i))
