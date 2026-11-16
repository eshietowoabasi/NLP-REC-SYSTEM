"""Skill extraction (EntityRuler) evaluation: precision, recall, F1 and inter-annotator kappa.

    python -m evaluation.ner_eval template --session 10 [--sample 60] [--seed 42]
    python -m evaluation.ner_eval score results/ner_gold_<stamp>.csv

``template`` samples passages of the session (stratified by document category), runs the skill
extractor on them and writes a CSV with the predicted skills and empty columns for two
annotators (see evaluation/README.md for the annotation guidelines), plus the list of skills
the extractor knows. ``score`` compares the predictions with the annotations: micro P/R/F1 over
(passage, skill) pairs, a breakdown by skill type, the skills most often missed or wrongly
found, and Cohen's kappa between the two annotators.
"""

from __future__ import annotations

import argparse
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from evaluation import metrics
from evaluation.common import (
    app_context,
    completed_session,
    read_csv,
    results_path,
    stamp,
    write_csv,
    write_json,
)

NONE_MARKER = "-"
COLUMNS = [
    "item",
    "passage_id",
    "document",
    "category",
    "text",
    "predicted_skills",
    "annotator_a",
    "annotator_b",
    "adjudicated",
    "notes",
]


def make_template(session_id: int, sample: int, seed: int) -> None:
    from app.services.ner.skills import build_skill_pipeline, extract_mentions
    from app.tasks.analysis import load_corpus, load_skill_patterns

    with app_context():
        session = completed_session(session_id)
        corpus = load_corpus(session)
        titles = {link.document.id: link.document.title for link in session.document_links}
        specs = load_skill_patterns()
        model = (session.parameter_config or {}).get("spacy_model", "en_core_web_sm")
        nlp = build_skill_pipeline(model, specs)

    # Stratified sample: every category gets a share proportional to its passages (at least 5).
    rng = random.Random(seed)
    by_category: dict[str, list[Any]] = defaultdict(list)
    for passage in corpus:
        by_category[passage.category].append(passage)
    chosen = []
    for _category, passages in sorted(by_category.items()):
        share = max(5, round(sample * len(passages) / len(corpus)))
        chosen += rng.sample(passages, min(share, len(passages)))
    rng.shuffle(chosen)
    mentions = extract_mentions(nlp, [p.text for p in chosen])

    stem = f"ner_gold_session{session_id}_{stamp()}"
    rows = [
        [
            index,
            passage.id,
            titles.get(passage.document_id, passage.document_id),
            passage.category,
            passage.text,
            "; ".join(sorted({m.name for m in found})) or NONE_MARKER,
            "",
            "",
            "",
            "",
        ]
        for index, (passage, found) in enumerate(zip(chosen, mentions, strict=True), start=1)
    ]
    template = write_csv(results_path(f"{stem}.csv"), COLUMNS, rows)
    vocabulary = write_csv(
        results_path(f"{stem}_skills.csv"),
        ["canonical_name", "type"],
        sorted({(s.canonical_name, s.label) for s in specs}),
    )
    print(f"{len(rows)} passages → {template}")
    print(f"Skills known to the extractor → {vocabulary}")
    print(
        "Annotate annotator_a and annotator_b independently (skills separated by ';', "
        f"'{NONE_MARKER}' for none), then run: python -m evaluation.ner_eval score {template}"
    )


def score(path: Path) -> None:
    rows = read_csv(path)
    vocabulary_path = path.with_name(path.stem + "_skills.csv")
    label_of: dict[str, str] = {}
    if vocabulary_path.exists():
        label_of = {
            metrics.normalise_skill(r["canonical_name"]): r["type"]
            for r in read_csv(vocabulary_path)
        }

    def cell(row: dict[str, str], column: str) -> set[str] | None:
        value = (row.get(column) or "").strip()
        if not value:
            return None  # not annotated
        return set() if value == NONE_MARKER else metrics.parse_skills(value)

    predicted, gold, both_a, both_b = [], [], [], []
    for row in rows:
        a, b, final = cell(row, "annotator_a"), cell(row, "annotator_b"), cell(row, "adjudicated")
        reference = final if final is not None else a
        if reference is None:
            continue
        predicted.append(cell(row, "predicted_skills") or set())
        gold.append(reference)
        if a is not None and b is not None:
            both_a.append(a)
            both_b.append(b)
    if not gold:
        raise SystemExit("No annotated rows yet (fill annotator_a or adjudicated).")

    overall = metrics.micro_prf(predicted, gold)
    by_label: dict[str, Counter[str]] = defaultdict(Counter)
    missed: Counter[str] = Counter()
    spurious: Counter[str] = Counter()
    for pred, true in zip(predicted, gold, strict=True):
        for skill in pred & true:
            by_label[label_of.get(skill, "OTHER")]["tp"] += 1
        for skill in pred - true:
            by_label[label_of.get(skill, "OTHER")]["fp"] += 1
            spurious[skill] += 1
        for skill in true - pred:
            by_label[label_of.get(skill, "OTHER")]["fn"] += 1
            missed[skill] += 1
    kappa = metrics.annotator_kappa(both_a, both_b)
    result = {
        "file": str(path),
        "annotated_passages": len(gold),
        "double_annotated_passages": len(both_a),
        "micro": overall.as_dict(),
        "by_type": {
            label: metrics.prf(c["tp"], c["fp"], c["fn"]).as_dict()
            for label, c in sorted(by_label.items())
        },
        "cohen_kappa": kappa,
        "kappa_interpretation": metrics.kappa_interpretation(kappa),
        "most_missed": missed.most_common(15),
        "most_spurious": spurious.most_common(15),
        "note": "Gold skills not in the extractor's list are counted under OTHER (coverage gaps).",
    }
    out = write_json(results_path(f"ner_scores_{stamp()}.json"), result)
    print(
        f"Passages: {len(gold)} (double-annotated: {len(both_a)})\n"
        f"Micro P={overall.precision:.3f} R={overall.recall:.3f} F1={overall.f1:.3f} "
        f"(TP {overall.true_positives}, FP {overall.false_positives}, "
        f"FN {overall.false_negatives})\n"
        f"Cohen's kappa: {kappa if kappa is None else round(kappa, 3)} "
        f"({metrics.kappa_interpretation(kappa)})\nSaved → {out}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    template = commands.add_parser("template", help="Write the annotation template")
    template.add_argument("--session", type=int, required=True)
    template.add_argument("--sample", type=int, default=60)
    template.add_argument("--seed", type=int, default=42)
    scoring = commands.add_parser("score", help="Score an annotated template")
    scoring.add_argument("file", type=Path)
    args = parser.parse_args()
    if args.command == "template":
        make_template(args.session, args.sample, args.seed)
    else:
        score(args.file)


if __name__ == "__main__":
    main()
