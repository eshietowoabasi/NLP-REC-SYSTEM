import json
from pathlib import Path

import pytest

from app.evaluation.metrics import (
    cohen_kappa,
    describe,
    match_mentions,
    match_spans,
    prf,
    roc_summary,
    sus_score,
    topic_diversity,
)
from app.evaluation.ner import evaluate_ner
from app.evaluation.similarity import evaluate_similarity, load_pairs_csv
from app.evaluation.sus import evaluate_sus, load_sus_csv
from app.services.embeddings import HashingEmbedder

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "evaluation"


# --- metrics ------------------------------------------------------------------

def test_prf():
    assert prf(8, 2, 2) == {"precision": 0.8, "recall": 0.8, "f1": 0.8, "tp": 8, "fp": 2, "fn": 2}
    assert prf(0, 0, 0)["f1"] == 0.0


def test_span_matching_modes():
    gold = [{"start": 0, "end": 10, "label": "SKILL"}, {"start": 20, "end": 25, "label": "TOOL"}]
    pred = [{"start": 0, "end": 5, "label": "SKILL"}, {"start": 20, "end": 25, "label": "TOOL"}, {"start": 30, "end": 32, "label": "TOOL"}]
    assert match_spans(gold, pred, "strict") == (1, 2, 1)
    assert match_spans(gold, pred, "lenient") == (2, 1, 0)
    # A gold span is matched at most once; label must agree.
    assert match_spans([{"start": 0, "end": 5, "label": "TOOL"}], [{"start": 0, "end": 5, "label": "TOOL"}] * 2) == (1, 1, 0)
    assert match_spans([{"start": 0, "end": 5, "label": "TOOL"}], [{"start": 0, "end": 5, "label": "SKILL"}]) == (0, 1, 1)
    with pytest.raises(ValueError):
        match_spans(gold, pred, "fuzzy")


def test_mentions_and_kappa():
    assert match_mentions({("python", "TOOL"), ("sql", "TOOL")}, {("python", "TOOL"), ("aws", "TOOL")}) == (1, 1, 1)
    assert cohen_kappa(["A", "B", "A", "O"], ["A", "B", "A", "O"]) == 1.0
    assert cohen_kappa(["A", "A", "O", "O"], ["A", "O", "A", "O"]) == 0.0
    with pytest.raises(ValueError):
        cohen_kappa(["A"], [])


@pytest.mark.parametrize("answers, expected", [([5, 1] * 5, 100.0), ([1, 5] * 5, 0.0), ([3] * 10, 50.0), ([4, 2, 4, 1, 4, 2, 5, 2, 4, 2], 80.0)])
def test_sus_score(answers, expected):
    assert sus_score(answers) == expected


@pytest.mark.parametrize("answers", [[3] * 9, [0] + [3] * 9, [6] + [3] * 9, ["3"] * 10])
def test_sus_score_rejects_bad_input(answers):
    with pytest.raises(ValueError):
        sus_score(answers)


def test_describe_and_diversity():
    assert describe([70, 80, 90]) == {"n": 3, "mean": 80.0, "sd": 10.0, "min": 70, "max": 90}
    assert describe([]) == {"n": 0}
    assert topic_diversity([["a", "b"], ["b", "c"]]) == 0.75


def test_roc_summary():
    labels = [1, 1, 1, 0, 0, 0]
    scores = [0.9, 0.85, 0.6, 0.5, 0.3, 0.2]
    result = roc_summary(labels, scores, threshold=0.8)
    assert result["auc_roc"] == 1.0
    assert result["at_configured_threshold"]["recall"] == pytest.approx(2 / 3, abs=1e-3)
    best = result["youden_optimal"]
    assert best["youden_j"] == 1.0 and best["recall"] == 1.0 and best["precision"] == 1.0
    assert 0.5 <= best["threshold"] <= 0.6
    with pytest.raises(ValueError):
        roc_summary([1, 1], [0.2, 0.3], 0.8)


# --- evaluators -------------------------------------------------------------

def _sample_ner():
    return [json.loads(line) for line in (SAMPLES / "ner_annotations.sample.jsonl").read_text().splitlines() if line.strip()]


def test_ner_evaluation_on_sample():
    result = evaluate_ner(_sample_ner())
    overall = result["scores"]["overall"]
    assert overall["tp"] + overall["fn"] == sum(len(r["gold"]) for r in _sample_ner())
    assert overall["precision"] > 0.8 and overall["recall"] > 0.75
    assert set(result["scores"]) == {"overall", "SKILL", "TOOL", "CERT"}
    assert 0.8 < result["inter_annotator"]["pairwise_f1"] <= 1 and result["inter_annotator"]["cohen_kappa_tokens"] > 0.8
    assert any("50 job adverts" in w for w in result["warnings"])


def test_ner_document_mode_uses_names():
    records = [{"id": "x", "text": "Kubernetes and K8s clusters with Python.",
                "gold": [{"text": "Kubernetes", "label": "TOOL"}, {"text": "Python", "label": "TOOL"}]}]
    result = evaluate_ner(records, mode="document")
    assert result["scores"]["overall"]["recall"] == 1.0 and result["scores"]["overall"]["fp"] == 0


def test_ner_validation_errors():
    with pytest.raises(ValueError, match="outside the text"):
        evaluate_ner([{"text": "short", "gold": [{"start": 0, "end": 99, "label": "TOOL"}]}])
    with pytest.raises(ValueError, match="missing text"):
        evaluate_ner([{"gold": []}])


def test_sus_evaluation_on_sample():
    result = evaluate_sus(load_sus_csv(SAMPLES / "sus_responses.sample.csv"))
    assert result["n"] == 6 and result["meets_target"] and result["grade"] in ("Good", "Excellent")
    assert len(result["respondents"]) == 6


def test_sus_csv_errors(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("respondent_id,q1\nR1,3\n")
    with pytest.raises(ValueError, match="q1..q10"):
        load_sus_csv(bad)
    bad.write_text("respondent_id," + ",".join(f"q{i}" for i in range(1, 11)) + "\nR1," + ",".join(["9"] * 10) + "\n")
    with pytest.raises(ValueError, match="line 2"):
        evaluate_sus(load_sus_csv(bad))


def test_similarity_evaluation_on_sample():
    result = evaluate_similarity(load_pairs_csv(SAMPLES / "similarity_pairs.sample.csv"), HashingEmbedder(), 0.8)
    assert result["pairs"] == 10 and 0 <= result["auc_roc"] <= 1
    assert len(result["per_pair"]) == 10 and all(-1 <= p["similarity"] <= 1 for p in result["per_pair"])
    assert any("not SBERT" in w for w in result["warnings"])


def test_similarity_csv_validation(tmp_path):
    bad = tmp_path / "pairs.csv"
    bad.write_text("pair_id,candidate_topic,core_topic,expert_overlap\np1,a,b,yes\n")
    with pytest.raises(ValueError, match="0 or 1"):
        load_pairs_csv(bad)


def test_topics_and_performance_evaluations():
    from app.evaluation.performance import benchmark, synthetic_corpus
    from app.evaluation.topics import evaluate_topics

    corpus = synthetic_corpus(documents=4, words=600, seed=1)
    topics = evaluate_topics(corpus, HashingEmbedder())
    assert topics["num_topics"] >= 2
    for model in ("bertopic", "lda"):
        assert 0 <= topics[model]["c_v"] <= 1 and len(topics[model]["topics"]) == topics["num_topics"]

    result = benchmark(corpus, synthetic_corpus(1, 300, seed=9)[0], "hashing", "unused", warm=False)
    assert result["documents"] == 4 and result["recommendations"] >= 1
    assert result["meets_target"] and "topics" in result["stage_seconds"]


def test_eval_cli(app, tmp_path):
    runner = app.test_cli_runner()
    out = tmp_path / "ner.json"
    result = runner.invoke(args=["eval", "ner", str(SAMPLES / "ner_annotations.sample.jsonl"), "--output", str(out)])
    assert result.exit_code == 0, result.output
    assert "overall" in result.output and json.loads(out.read_text())["documents"] == 5
    result = runner.invoke(args=["eval", "sus", str(SAMPLES / "sus_responses.sample.csv"), "--output", str(tmp_path / "s.json")])
    assert result.exit_code == 0 and "SUS: n=6" in result.output
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"text": "x", "gold": [{"start": 0, "end": 5, "label": "TOOL"}]}) + "\n")
    result = runner.invoke(args=["eval", "ner", str(bad)])
    assert result.exit_code != 0 and "outside the text" in result.output
