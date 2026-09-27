"""Evaluation metrics (SYNTHETIC numbers; the real results come from evaluation/ scripts)."""

from __future__ import annotations

import pytest

from evaluation import metrics


def test_prf_and_micro_average_over_passage_skill_pairs() -> None:
    predicted = [{"python", "aws"}, {"docker"}, set()]
    gold = [{"python"}, {"docker", "kubernetes"}, {"sql"}]

    result = metrics.micro_prf(predicted, gold)

    # TP: python, docker; FP: aws; FN: kubernetes, sql.
    assert (result.true_positives, result.false_positives, result.false_negatives) == (2, 1, 2)
    assert result.precision == pytest.approx(2 / 3)
    assert result.recall == pytest.approx(0.5)
    assert result.f1 == pytest.approx(2 * (2 / 3) * 0.5 / (2 / 3 + 0.5))
    assert metrics.prf(0, 0, 0).f1 == 0.0


def test_skill_cells_are_normalised() -> None:
    assert metrics.parse_skills(" Python ;AWS;  machine   learning ;") == {
        "python",
        "aws",
        "machine learning",
    }
    assert metrics.parse_skills("") == set()


def test_annotator_kappa() -> None:
    a = [{"python", "aws"}, {"docker"}, {"sql"}, {"linux"}]
    b = [{"python"}, {"docker"}, {"sql", "excel"}, {"linux"}]
    # Decisions: python 1/1, aws 1/0, docker 1/1, sql 1/1, excel 0/1, linux 1/1.
    kappa = metrics.annotator_kappa(a, b)
    assert kappa is not None and -1 <= kappa < 1
    assert metrics.annotator_kappa([{"x"}], [{"x"}]) is None  # no variation
    assert metrics.kappa_interpretation(0.85) == "almost perfect"
    assert metrics.kappa_interpretation(0.5) == "moderate"
    assert metrics.kappa_interpretation(None) == "undefined"


def test_overlap_threshold_is_strict_and_calibration_prefers_best_f1() -> None:
    scores = [0.90, 0.80, 0.70, 0.60, 0.50]
    labels = [1, 1, 1, 0, 0]

    at_080 = metrics.at_threshold(scores, labels, 0.80)
    assert (at_080.true_positives, at_080.false_negatives) == (1, 2)  # 0.80 is not > 0.80
    assert metrics.auc_roc(scores, labels) == pytest.approx(1.0)
    best = metrics.best_threshold(metrics.threshold_sweep(scores, labels))
    assert best is not None and best.f1 == pytest.approx(1.0)
    assert 0.60 <= best.threshold < 0.70
    assert metrics.auc_roc([0.5, 0.6], [1, 1]) is None


def test_sus_scoring_and_adjectives() -> None:
    assert metrics.sus_score([5, 1, 5, 1, 5, 1, 5, 1, 5, 1]) == 100.0
    assert metrics.sus_score([1, 5, 1, 5, 1, 5, 1, 5, 1, 5]) == 0.0
    assert metrics.sus_score([3] * 10) == 50.0
    with pytest.raises(ValueError):
        metrics.sus_score([3] * 9)
    assert metrics.sus_adjective(50.0) == "OK"
    assert metrics.sus_adjective(80.0) == "Excellent"
    summary = metrics.summarise([70.0, 80.0, 90.0])
    assert summary["mean"] == pytest.approx(80.0)
    assert summary["ci95_low"] < 80.0 < summary["ci95_high"]
