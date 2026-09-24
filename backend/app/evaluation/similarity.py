"""Semantic-overlap evaluation (spec §17.3): expert-labelled topic pairs, AUC-ROC.

CSV columns: pair_id, candidate_topic, core_topic, expert_overlap (1 = overlaps the
NUC core, 0 = does not). The spec plans 30 pairs.
"""
import csv

import numpy as np

from .metrics import roc_summary


def load_pairs_csv(path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        needed = {"candidate_topic", "core_topic", "expert_overlap"}
        if not needed <= set(reader.fieldnames or []):
            raise ValueError(f"CSV needs columns: pair_id, {', '.join(sorted(needed))}")
        rows = list(reader)
    for i, row in enumerate(rows, start=2):
        if row["expert_overlap"].strip() not in ("0", "1"):
            raise ValueError(f"line {i}: expert_overlap must be 0 or 1")
        if not row["candidate_topic"].strip() or not row["core_topic"].strip():
            raise ValueError(f"line {i}: both topics are required")
    return rows


def evaluate_similarity(rows: list[dict], embedder, threshold: float) -> dict:
    candidates = embedder.encode([r["candidate_topic"].strip() for r in rows])
    cores = embedder.encode([r["core_topic"].strip() for r in rows])
    similarities = np.clip((candidates * cores).sum(axis=1), -1, 1)  # vectors are L2-normalised
    labels = [int(r["expert_overlap"]) for r in rows]
    summary = roc_summary(labels, [float(s) for s in similarities], threshold)
    warnings = []
    if embedder.backend != "sbert":
        warnings.append(f"Embedding backend '{embedder.backend}' is not SBERT; results do not evaluate the real system.")
    if len(rows) < 30:
        warnings.append(f"The evaluation plan calls for 30 topic pairs; this file has {len(rows)}.")
    return {
        "pairs": len(rows),
        "embedding_backend": embedder.backend,
        "embedding_model": embedder.model_name,
        **summary,
        "per_pair": [
            {"pair_id": r.get("pair_id") or str(i), "similarity": round(float(s), 4), "expert_overlap": l,
             "predicted_overlap": bool(s > threshold)}
            for i, (r, s, l) in enumerate(zip(rows, similarities, labels), start=1)
        ],
        "warnings": warnings,
    }
