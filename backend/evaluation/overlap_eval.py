"""NUC overlap evaluation: AUC-ROC, precision/recall at 0.80, and threshold calibration.

    python -m evaluation.overlap_eval template --session 10 [--closest 3] [--random 2]
    python -m evaluation.overlap_eval score results/overlap_pairs_<stamp>.csv [--threshold 0.80]

``template`` re-analyses the session in memory and, for every theme, lists its ``--closest``
most similar NUC courses (the courses compared by the session, i.e. after the exclusions) and
``--random`` other courses, with the cosine similarity, the theme's keywords and a representative
passage, and an empty ``covered`` column. Annotators mark ``1`` when the NUC course already
teaches the theme's content (the theme would duplicate it) and ``0`` when it does not.

``score`` computes the AUC-ROC of the similarity against these labels, precision, recall and F1
at the current threshold (strictly greater, as in the application), and sweeps thresholds from
0.40 to 0.95 to suggest a calibrated one (highest F1; Youden's J is reported too).
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import numpy as np

from evaluation import metrics
from evaluation.common import read_csv, reanalyse, results_path, stamp, write_csv, write_json

COLUMNS = [
    "pair",
    "topic_id",
    "theme",
    "theme_keywords",
    "theme_passage",
    "course_code",
    "course_title",
    "similarity",
    "similarity_rank",
    "covered",
    "annotator_b",
    "notes",
]


def make_template(session_id: int, closest: int, others: int, seed: int) -> None:
    from evaluation.common import app_context

    with app_context():
        data = reanalyse(session_id)
    courses = data.courses
    if not courses:
        raise SystemExit("The session's NUC core has no courses; nothing to pair.")
    matrix = np.vstack([c.embedding for c in courses]).astype(np.float32)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    texts = {p.id: p.text for p in data.corpus}
    rng = random.Random(seed)
    rows = []
    for candidate in data.output.candidates:
        similarities = matrix @ data.centres[candidate.topic_id]
        order = list(np.argsort(-similarities))
        picked = order[:closest]
        rest = order[closest:]
        picked += rng.sample(rest, min(others, len(rest)))
        keywords = ", ".join(k["term"] for k in candidate.keywords[:8])
        passage = texts[candidate.evidence[0][0]] if candidate.evidence else ""
        for index in picked:
            course = courses[index]
            rows.append(
                [
                    len(rows) + 1,
                    candidate.topic_id,
                    candidate.auto_title,
                    keywords,
                    " ".join(passage.split())[:600],
                    course.code,
                    course.title,
                    f"{float(similarities[index]):.4f}",
                    order.index(index) + 1,
                    "",
                    "",
                    "",
                ]
            )
    # Shuffle so annotators are not anchored by the similarity order.
    rng.shuffle(rows)
    for number, row in enumerate(rows, start=1):
        row[0] = number
    path = write_csv(
        results_path(f"overlap_pairs_session{session_id}_{stamp()}.csv"), COLUMNS, rows
    )
    print(
        f"{len(rows)} theme–course pairs ({len(data.output.candidates)} themes × "
        f"{closest} closest + {others} random) → {path}\n"
        "Fill 'covered' with 1 (the course already teaches this theme) or 0, optionally "
        f"'annotator_b' for agreement, then run: python -m evaluation.overlap_eval score {path}"
    )


def score(path: Path, threshold: float) -> None:
    rows = read_csv(path)
    labelled = [r for r in rows if (r.get("covered") or "").strip() in {"0", "1"}]
    if not labelled:
        raise SystemExit("No labelled pairs yet: fill the 'covered' column with 0 or 1.")
    scores = [float(r["similarity"]) for r in labelled]
    labels = [int(r["covered"]) for r in labelled]
    current = metrics.at_threshold(scores, labels, threshold)
    sweep = metrics.threshold_sweep(scores, labels)
    best = metrics.best_threshold(sweep)
    youden = max(sweep, key=lambda r: (r.youden_j, r.threshold))
    double = [r for r in labelled if (r.get("annotator_b") or "").strip() in {"0", "1"}]
    kappa = None
    if len(double) >= 2:
        from sklearn.metrics import cohen_kappa_score

        a = [int(r["covered"]) for r in double]
        b = [int(r["annotator_b"]) for r in double]
        if len(set(a) | set(b)) > 1:
            kappa = float(cohen_kappa_score(a, b))
    result = {
        "file": str(path),
        "pairs": len(labelled),
        "covered": sum(labels),
        "not_covered": len(labels) - sum(labels),
        "auc_roc": metrics.auc_roc(scores, labels),
        "at_threshold": current.__dict__,
        "best_f1_threshold": best.__dict__ if best else None,
        "best_youden_threshold": youden.__dict__,
        "sweep": [r.__dict__ for r in sweep],
        "annotator_kappa": kappa,
        "kappa_interpretation": metrics.kappa_interpretation(kappa),
    }
    out = write_json(results_path(f"overlap_scores_{stamp()}.json"), result)
    auc = result["auc_roc"]
    print(
        f"Pairs: {len(labelled)} ({sum(labels)} covered)\n"
        f"AUC-ROC: {'undefined (one class only)' if auc is None else f'{auc:.3f}'}\n"
        f"At {threshold:.2f}: P={current.precision:.3f} R={current.recall:.3f} "
        f"F1={current.f1:.3f}\n"
        + (
            f"Best F1 at {best.threshold:.2f}: P={best.precision:.3f} R={best.recall:.3f} "
            f"F1={best.f1:.3f}\n"
            if best
            else "No threshold gives F1 > 0.\n"
        )
        + f"Youden's J best at {youden.threshold:.2f}\nSaved → {out}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    template = commands.add_parser("template", help="Write the theme–course pairs to label")
    template.add_argument("--session", type=int, required=True)
    template.add_argument("--closest", type=int, default=3)
    template.add_argument("--random", type=int, default=2)
    template.add_argument("--seed", type=int, default=42)
    scoring = commands.add_parser("score", help="Score labelled pairs")
    scoring.add_argument("file", type=Path)
    scoring.add_argument("--threshold", type=float, default=0.80)
    args = parser.parse_args()
    if args.command == "template":
        make_template(args.session, args.closest, args.random, args.seed)
    else:
        score(args.file, args.threshold)


if __name__ == "__main__":
    main()
