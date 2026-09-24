"""Metric functions for the evaluation plan (spec §17). Pure functions, no I/O."""
import math
from collections import Counter


def prf(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4), "tp": tp, "fp": fp, "fn": fn}


def _overlaps(a, b) -> bool:
    return a["start"] < b["end"] and b["start"] < a["end"]


def match_spans(gold: list[dict], predicted: list[dict], mode: str = "strict") -> tuple[int, int, int]:
    """Count TP/FP/FN between span annotations ({start, end, label}).

    strict: same start, end and label. lenient: overlapping spans with the same label.
    Each gold span can be matched at most once.
    """
    if mode not in ("strict", "lenient"):
        raise ValueError("mode must be 'strict' or 'lenient'")
    unmatched = list(gold)
    tp = 0
    for p in predicted:
        for g in unmatched:
            same = (g["start"], g["end"]) == (p["start"], p["end"]) if mode == "strict" else _overlaps(g, p)
            if same and g["label"] == p["label"]:
                unmatched.remove(g)
                tp += 1
                break
    return tp, len(predicted) - tp, len(unmatched)


def match_mentions(gold: set, predicted: set) -> tuple[int, int, int]:
    """Document-level comparison of (normalised name, label) sets."""
    tp = len(gold & predicted)
    return tp, len(predicted - gold), len(gold - predicted)


def cohen_kappa(labels_a: list, labels_b: list) -> float:
    """Cohen's kappa for two annotators labelling the same items."""
    if len(labels_a) != len(labels_b):
        raise ValueError("annotators must label the same items")
    n = len(labels_a)
    if n == 0:
        return 0.0
    observed = sum(a == b for a, b in zip(labels_a, labels_b)) / n
    ca, cb = Counter(labels_a), Counter(labels_b)
    expected = sum(ca[k] * cb[k] for k in ca) / (n * n)
    if expected == 1:
        return 1.0
    return round((observed - expected) / (1 - expected), 4)


def sus_score(responses: list[int]) -> float:
    """System Usability Scale: 10 items on a 1-5 scale -> 0-100 (Brooke, 1996)."""
    if len(responses) != 10 or any(not isinstance(r, int) or not 1 <= r <= 5 for r in responses):
        raise ValueError("SUS needs 10 integer responses between 1 and 5")
    odd = sum(r - 1 for r in responses[0::2])      # items 1, 3, 5, 7, 9 (positive)
    even = sum(5 - r for r in responses[1::2])     # items 2, 4, 6, 8, 10 (negative)
    return (odd + even) * 2.5


def describe(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    n = len(values)
    mean = sum(values) / n
    sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1)) if n > 1 else 0.0
    return {"n": n, "mean": round(mean, 2), "sd": round(sd, 2), "min": min(values), "max": max(values)}


def roc_summary(labels: list[int], scores: list[float], threshold: float) -> dict:
    """AUC-ROC, the Youden-optimal threshold, and classification quality at ``threshold``
    (positive = score > threshold, matching the overlap rule in spec §9)."""
    from sklearn.metrics import roc_auc_score, roc_curve

    if len(set(labels)) < 2:
        raise ValueError("ground truth needs both overlapping (1) and non-overlapping (0) pairs")
    auc = roc_auc_score(labels, scores)
    fpr, tpr, thresholds = roc_curve(labels, scores)
    best = max(range(len(thresholds)), key=lambda i: (tpr[i] - fpr[i], -abs(thresholds[i] - threshold)))

    def at(t):
        predicted = [s > t for s in scores]
        tp = sum(p and l == 1 for p, l in zip(predicted, labels))
        fp = sum(p and l == 0 for p, l in zip(predicted, labels))
        fn = sum((not p) and l == 1 for p, l in zip(predicted, labels))
        tn = len(labels) - tp - fp - fn
        return {**prf(tp, fp, fn), "tn": tn, "accuracy": round((tp + tn) / len(labels), 4), "threshold": round(float(t), 4)}

    # roc_curve thresholds are ">=" cut points; nudge below so our ">" rule includes that score.
    youden_t = float(thresholds[best]) - 1e-9 if math.isfinite(thresholds[best]) else 1.0
    return {
        "auc_roc": round(float(auc), 4),
        "at_configured_threshold": at(threshold),
        "youden_optimal": {**at(youden_t), "threshold": round(float(thresholds[best]), 4),
                           "youden_j": round(float(tpr[best] - fpr[best]), 4)},
        "curve": [{"fpr": round(float(f), 4), "tpr": round(float(t), 4)} for f, t in zip(fpr, tpr)],
    }


def topic_diversity(topics: list[list[str]], top_n: int = 10) -> float:
    """Share of unique words among all topics' top-n words (Dieng et al., 2020)."""
    words = [w for t in topics for w in t[:top_n]]
    return round(len(set(words)) / len(words), 4) if words else 0.0
