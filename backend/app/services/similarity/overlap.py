"""Overlap of candidate topics with the NUC core (the fixed 70%), by meaning.

For each candidate, ``max_sim`` is the highest cosine similarity between the candidate
embedding and any NUC core passage embedding; ``novelty = 1 - max_sim`` (clipped to [0, 1]).
A candidate is a *Potential Duplicate* when ``max_sim`` is strictly greater than the threshold
(default 0.80); exactly 0.80 is still "No Significant Overlap". The closest NUC passage is
reported so planners can compare the two side by side.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from app.models.enums import OverlapStatus


@dataclass(frozen=True)
class Overlap:
    max_similarity: float
    closest_index: int  # index into the NUC core passages
    novelty: float
    status: OverlapStatus


def _normalise(matrix: NDArray[np.float32]) -> NDArray[np.float32]:
    matrix = np.atleast_2d(np.asarray(matrix, dtype=np.float32))
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.where(norms == 0, 1, norms)


def overlap_status(max_similarity: float, threshold: float) -> OverlapStatus:
    return (
        OverlapStatus.POTENTIAL_DUPLICATE
        if max_similarity > threshold
        else OverlapStatus.NO_SIGNIFICANT_OVERLAP
    )


def compare_to_core(
    candidates: NDArray[np.float32], core: NDArray[np.float32], threshold: float
) -> list[Overlap]:
    """Overlap of each candidate embedding (rows) with the NUC core passage embeddings."""
    if len(core) == 0:
        raise ValueError("The NUC core has no passages to compare against.")
    similarities = _normalise(candidates) @ _normalise(core).T
    results = []
    for row in similarities:
        index = int(np.argmax(row))
        max_similarity = float(np.clip(row[index], -1.0, 1.0))
        results.append(
            Overlap(
                max_similarity=max_similarity,
                closest_index=index,
                novelty=float(np.clip(1.0 - max_similarity, 0.0, 1.0)),
                status=overlap_status(max_similarity, threshold),
            )
        )
    return results
