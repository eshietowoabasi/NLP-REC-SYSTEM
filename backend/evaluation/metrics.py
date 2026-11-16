"""Evaluation metrics (pure functions, unit-tested with synthetic data in tests/test_evaluation.py).

* Skill extraction (NER): micro precision/recall/F1 over (passage, skill) pairs, per-label
  breakdown, and Cohen's kappa between two annotators.
* NUC overlap: AUC-ROC of the similarity score against human "already covered" labels,
  precision/recall/F1 at a threshold, and a threshold sweep for calibration.
* SUS: the standard System Usability Scale score (Brooke, 1996) with an adjective rating
  (Bangor, Kortum & Miller, 2009).
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass

from sklearn.metrics import cohen_kappa_score, roc_auc_score

# ------------------------------------------------------------------------ NER


@dataclass(frozen=True)
class PRF:
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1: float

    def as_dict(self) -> dict[str, float | int]:
        return asdict(self)


def prf(tp: int, fp: int, fn: int) -> PRF:
    """Precision, recall and F1 from counts (0 when undefined)."""
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return PRF(tp, fp, fn, precision, recall, f1)


def normalise_skill(name: str) -> str:
    return " ".join(name.strip().lower().split())


def parse_skills(cell: str | None) -> set[str]:
    """A cell such as "Python; AWS ; docker" → {"python", "aws", "docker"}."""
    if not cell:
        return set()
    return {normalise_skill(part) for part in cell.split(";") if part.strip()}


def micro_prf(predicted: Sequence[set[str]], gold: Sequence[set[str]]) -> PRF:
    """Micro-averaged P/R/F1 over (item, skill) pairs of parallel predicted/gold sets."""
    tp = fp = fn = 0
    for pred, true in zip(predicted, gold, strict=True):
        tp += len(pred & true)
        fp += len(pred - true)
        fn += len(true - pred)
    return prf(tp, fp, fn)


def annotator_kappa(a: Sequence[set[str]], b: Sequence[set[str]]) -> float | None:
    """Cohen's kappa between two annotators over binary (item, skill) decisions.

    The decisions are the skills that at least one annotator marked in an item (present or
    absent for each annotator); skills that neither marked are not counted, as there is no
    closed list of candidates. Returns None when undefined (fewer than two decisions, or no
    variation).
    """
    labels_a: list[int] = []
    labels_b: list[int] = []
    for skills_a, skills_b in zip(a, b, strict=True):
        for skill in skills_a | skills_b:
            labels_a.append(int(skill in skills_a))
            labels_b.append(int(skill in skills_b))
    if len(labels_a) < 2 or len(set(labels_a) | set(labels_b)) < 2:
        return None
    value = float(cohen_kappa_score(labels_a, labels_b))
    return None if math.isnan(value) else value


def kappa_interpretation(kappa: float | None) -> str:
    """Landis & Koch (1977) bands."""
    if kappa is None:
        return "undefined"
    bands = [
        (0.0, "poor"),
        (0.20, "slight"),
        (0.40, "fair"),
        (0.60, "moderate"),
        (0.80, "substantial"),
        (1.01, "almost perfect"),
    ]
    for upper, label in bands:
        if kappa <= upper:
            return label
    return "almost perfect"


# --------------------------------------------------------------------- overlap


@dataclass(frozen=True)
class ThresholdResult:
    threshold: float
    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    youden_j: float


def at_threshold(
    scores: Sequence[float], labels: Sequence[int], threshold: float
) -> ThresholdResult:
    """Classification at ``score > threshold`` (strict, as the application does)."""
    tp = fp = fn = tn = 0
    for score, label in zip(scores, labels, strict=True):
        predicted = score > threshold
        if predicted and label:
            tp += 1
        elif predicted:
            fp += 1
        elif label:
            fn += 1
        else:
            tn += 1
    counts = prf(tp, fp, fn)
    specificity = tn / (tn + fp) if tn + fp else 0.0
    return ThresholdResult(
        threshold=round(threshold, 4),
        precision=counts.precision,
        recall=counts.recall,
        f1=counts.f1,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        true_negatives=tn,
        youden_j=counts.recall + specificity - 1,
    )


def auc_roc(scores: Sequence[float], labels: Sequence[int]) -> float | None:
    """Area under the ROC curve, or None when only one class is labelled."""
    if len(set(labels)) < 2:
        return None
    return float(roc_auc_score(labels, scores))


def threshold_sweep(
    scores: Sequence[float],
    labels: Sequence[int],
    start: float = 0.40,
    stop: float = 0.95,
    step: float = 0.01,
) -> list[ThresholdResult]:
    count = int(round((stop - start) / step)) + 1
    return [at_threshold(scores, labels, start + i * step) for i in range(count)]


def best_threshold(results: Iterable[ThresholdResult]) -> ThresholdResult | None:
    """Highest F1; ties go to the higher threshold (fewer false duplicate flags)."""
    ranked = sorted(results, key=lambda r: (r.f1, r.threshold), reverse=True)
    return ranked[0] if ranked and ranked[0].f1 > 0 else None


# ------------------------------------------------------------------------- SUS


def sus_score(responses: Sequence[int]) -> float:
    """SUS score (0–100) from the ten 1–5 answers, in questionnaire order.

    Odd items are positive (answer − 1), even items negative (5 − answer); the sum × 2.5.
    """
    if len(responses) != 10 or any(not 1 <= r <= 5 for r in responses):
        raise ValueError("SUS needs ten answers from 1 to 5.")
    total = sum((r - 1) if i % 2 == 0 else (5 - r) for i, r in enumerate(responses))
    return total * 2.5


def sus_adjective(score: float) -> str:
    """Adjective rating of a mean SUS score (Bangor, Kortum & Miller, 2009)."""
    for limit, label in [
        (25.0, "Worst imaginable"),
        (39.0, "Poor"),
        (52.0, "OK"),
        (73.0, "Good"),
        (85.0, "Excellent"),
    ]:
        if score < limit:
            return label
    return "Best imaginable"


def summarise(values: Sequence[float]) -> dict[str, float | int | None]:
    """Mean, SD and a 95% confidence interval (t distribution) of a sample."""
    n = len(values)
    if n == 0:
        return {"n": 0, "mean": None, "sd": None, "ci95_low": None, "ci95_high": None}
    mean = statistics.fmean(values)
    if n == 1:
        return {"n": 1, "mean": mean, "sd": None, "ci95_low": None, "ci95_high": None}
    sd = statistics.stdev(values)
    from scipy.stats import t

    half = float(t.ppf(0.975, n - 1)) * sd / math.sqrt(n)
    return {"n": n, "mean": mean, "sd": sd, "ci95_low": mean - half, "ci95_high": mean + half}
