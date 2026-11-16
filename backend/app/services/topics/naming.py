"""Course-style names for topics, chosen from a curated catalogue by SBERT similarity.

Each topic is compared with every catalogue name ("Software Testing and Quality Assurance")
twice: through its centre (the mean embedding of its extracts) and through the embedding of its
keywords written as a phrase. The average of the two similarities ranks the names; the centre
captures what the extracts are about, the keywords what distinguishes the topic.

A topic gets its best name only if the similarity is at least ``NAME_THRESHOLD`` (0.50: on the
real corpus, names at 0.50 and above were right, below it they were wrong or too vague, e.g.
"Broadband Penetration" → "IT Infrastructure Management" at 0.47). Names are unique: the more
similar topic wins a name, the other takes its next name above the threshold, or keeps its
keyword title when no other name is close enough (as do topics whose best name is below the
threshold).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

NAME_THRESHOLD = 0.50


@dataclass(frozen=True)
class TopicName:
    name: str | None  # None: no catalogue name is close enough
    similarity: float  # of the best catalogue name, even when below the threshold


def _normalise(matrix: NDArray[np.float32]) -> NDArray[np.float32]:
    matrix = np.atleast_2d(np.asarray(matrix, dtype=np.float32))
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.where(norms == 0, 1, norms)


def name_topics(
    centres: NDArray[np.float32],
    keyword_vectors: NDArray[np.float32],
    names: Sequence[str],
    name_vectors: NDArray[np.float32],
    threshold: float = NAME_THRESHOLD,
) -> list[TopicName]:
    """A catalogue name (or None) per topic; rows of ``centres`` and ``keyword_vectors`` align."""
    if len(centres) == 0:
        return []
    if not names:
        return [TopicName(None, 0.0) for _ in range(len(centres))]
    similarity = (
        _normalise(centres) @ _normalise(name_vectors).T
        + _normalise(keyword_vectors) @ _normalise(name_vectors).T
    ) / 2
    best = similarity.max(axis=1)
    result: list[TopicName | None] = [None] * len(centres)
    taken: set[int] = set()
    # Topics with the clearest match choose first.
    for row in np.argsort(-best, kind="stable"):
        row = int(row)
        order = np.argsort(-similarity[row], kind="stable")
        if best[row] < threshold:
            result[row] = TopicName(None, float(best[row]))
            continue
        free = next(
            (int(i) for i in order if int(i) not in taken and similarity[row, i] >= threshold),
            None,
        )
        if free is not None:
            taken.add(free)
            result[row] = TopicName(names[free], float(similarity[row, free]))
        else:
            result[row] = TopicName(None, float(best[row]))
    return [r if r is not None else TopicName(None, 0.0) for r in result]
