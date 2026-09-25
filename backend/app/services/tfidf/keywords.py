"""TF-IDF keyword extraction over the normalised passage text.

Runs on the heavily normalised branch of preprocessing (lowercase lemmas without stop words),
so "Developers must build APIs" and "API development" contribute to the same terms. Unigrams
and bigrams are scored; a term's score is its mean TF-IDF weight across the passages, overall
and within each source category.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# Normalised text is already tokenised: tokens are separated by single spaces.
TOKEN_PATTERN = r"(?u)[^\s]+"
# With fewer passages than this, rare/common term filtering would remove too much.
MIN_PASSAGES_FOR_FILTERING = 10


@dataclass(frozen=True)
class Keyword:
    term: str
    score: float
    passage_count: int

    def as_dict(self) -> dict[str, float | int | str]:
        return {
            "term": self.term,
            "score": round(self.score, 6),
            "passage_count": self.passage_count,
        }


def _vectorizer(passage_count: int, filtered: bool) -> TfidfVectorizer:
    use_filters = filtered and passage_count >= MIN_PASSAGES_FOR_FILTERING
    return TfidfVectorizer(
        ngram_range=(1, 2),
        token_pattern=TOKEN_PATTERN,
        lowercase=False,
        sublinear_tf=True,
        min_df=2 if use_filters else 1,  # a term must appear in at least two passages
        max_df=0.85 if use_filters else 1.0,  # and in no more than 85% of them
    )


def _top(
    scores: np.ndarray, counts: np.ndarray, vocabulary: np.ndarray, top_n: int
) -> list[Keyword]:
    order = np.argsort(-scores, kind="stable")[:top_n]
    return [
        Keyword(str(vocabulary[i]), float(scores[i]), int(counts[i]))
        for i in order
        if scores[i] > 0
    ]


def extract_keywords(
    normalised_texts: list[str], categories: list[str], top_n: int = 30
) -> dict[str, object]:
    """Top TF-IDF terms overall and per source category.

    Returns ``{"overall": [...], "by_category": {category: [...]}, "passage_count": n}`` where
    each keyword is ``{"term", "score", "passage_count"}``.
    """
    if len(normalised_texts) != len(categories):
        raise ValueError("Each passage needs exactly one category.")
    result: dict[str, object] = {
        "overall": [],
        "by_category": {},
        "passage_count": len(normalised_texts),
    }
    if not any(text.strip() for text in normalised_texts):
        return result

    try:
        vectorizer = _vectorizer(len(normalised_texts), filtered=True)
        matrix = vectorizer.fit_transform(normalised_texts)
    except ValueError:  # filtering left no terms (tiny or very uniform corpus)
        vectorizer = _vectorizer(len(normalised_texts), filtered=False)
        matrix = vectorizer.fit_transform(normalised_texts)

    vocabulary = vectorizer.get_feature_names_out()
    presence = (matrix > 0).astype(np.int32)
    result["overall"] = [
        k.as_dict()
        for k in _top(
            np.asarray(matrix.mean(axis=0)).ravel(),
            np.asarray(presence.sum(axis=0)).ravel(),
            vocabulary,
            top_n,
        )
    ]
    labels = np.asarray(categories)
    by_category: dict[str, list[dict[str, float | int | str]]] = {}
    for category in sorted(set(categories)):
        rows = np.flatnonzero(labels == category)
        subset = matrix[rows]
        by_category[category] = [
            k.as_dict()
            for k in _top(
                np.asarray(subset.mean(axis=0)).ravel(),
                np.asarray(presence[rows].sum(axis=0)).ravel(),
                vocabulary,
                top_n,
            )
        ]
    result["by_category"] = by_category
    return result
