"""Score normalisation, composite scoring and ranking of candidate topics.

    composite = w_ner × skill_demand + w_topic × theme_strength + w_novelty × novelty

* skill demand (NER): for each of the candidate's top skills, count the distinct documents in
  the session that mention it; sum, apply log1p, then min-max normalise across candidates.
* theme strength (topic): (topic passages / all non-outlier passages) × mean topic probability,
  then min-max normalise across candidates.
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


def skill_demand_raw(top_skills: Sequence[str], document_frequency: dict[str, int]) -> float:
    """log1p of the summed document frequencies of the candidate's top skills."""
    return math.log1p(sum(document_frequency.get(skill, 0) for skill in top_skills))


def theme_strength_raw(topic_size: int, total_non_outlier: int, mean_probability: float) -> float:
    """Share of the modelled passages in this topic, weighted by how confidently they belong."""
    if total_non_outlier <= 0:
        return 0.0
    return (topic_size / total_non_outlier) * mean_probability


def composite_score(ner: float, topic: float, novelty: float, weights: ScoreWeights) -> float:
    value = weights.ner * ner + weights.topic * topic + weights.novelty * novelty
    return float(min(max(value, 0.0), 1.0))


def rank(composites: Sequence[float], tie_breakers: Sequence[float]) -> list[int]:
    """Indices by composite (highest first); ties go to the higher ``tie_breakers`` value."""
    return sorted(range(len(composites)), key=lambda i: (-composites[i], -tie_breakers[i], i))
