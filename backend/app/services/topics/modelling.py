"""Theme discovery with BERTopic (UMAP + HDBSCAN) over precomputed passage embeddings.

Only passages of non-NUC documents are modelled; the NUC core is the comparison baseline and
never becomes a topic. Clustering uses the SBERT embeddings of the original text; the topic
words (c-TF-IDF) are computed from the normalised text, so they are lowercase lemmas without
stop words. The outlier topic (-1) is discarded. A fixed ``random_state`` makes runs repeatable.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from app.services.exceptions import AnalysisError

OUTLIER_TOPIC = -1
TOP_WORDS = 10


@dataclass(frozen=True)
class Topic:
    """A discovered theme: its members are indices into the modelled passages."""

    topic_id: int
    keywords: list[tuple[str, float]]
    members: list[int]


@dataclass(frozen=True)
class TopicModelResult:
    assignments: NDArray[np.int64]  # topic id per passage (-1 = outlier)
    probabilities: NDArray[np.float64]  # membership strength of each passage in its topic
    topics: list[Topic]

    @property
    def non_outlier_count(self) -> int:
        return int(np.sum(self.assignments != OUTLIER_TOPIC))


def minimum_passages(min_topic_size: int) -> int:
    """Fewest passages for which topic modelling is attempted."""
    return max(2 * min_topic_size, 10)


def fit_topics(
    normalised_texts: list[str],
    embeddings: NDArray[np.float32],
    min_topic_size: int = 5,
    random_state: int = 42,
) -> TopicModelResult:
    """Cluster passages into themes. Raises AnalysisError if there is too little text."""
    from bertopic import BERTopic
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import CountVectorizer
    from umap import UMAP

    count = len(normalised_texts)
    if count != len(embeddings):
        raise ValueError("One embedding is needed per passage.")
    needed = minimum_passages(min_topic_size)
    if count < needed:
        raise AnalysisError(
            f"Too little text to discover themes: {count} passages were found but at least "
            f"{needed} are needed. Add more documents to the session."
        )

    # Empty normalised passages (all stop words) would break the topic-word vectoriser.
    docs = [text if text.strip() else "_" for text in normalised_texts]
    model = BERTopic(
        umap_model=UMAP(
            n_neighbors=min(15, count - 1),
            n_components=min(5, count - 2),
            min_dist=0.0,
            metric="cosine",
            random_state=random_state,
            n_jobs=1,  # a fixed seed makes UMAP single-threaded; stated to keep runs repeatable
        ),
        hdbscan_model=HDBSCAN(
            min_cluster_size=min_topic_size,
            metric="euclidean",
            cluster_selection_method="eom",
            prediction_data=True,
        ),
        vectorizer_model=CountVectorizer(
            ngram_range=(1, 2), token_pattern=r"(?u)[^\s]+", lowercase=False
        ),
        calculate_probabilities=False,
        top_n_words=TOP_WORDS,
        verbose=False,
    )
    assignments, probabilities = model.fit_transform(docs, embeddings=np.asarray(embeddings))
    labels = np.asarray(assignments, dtype=np.int64)
    probs = (
        np.asarray(probabilities, dtype=np.float64)
        if probabilities is not None
        else np.ones(count, dtype=np.float64)
    )

    topics = []
    for topic_id in sorted(set(labels.tolist()) - {OUTLIER_TOPIC}):
        words = [
            (word, float(weight))
            for word, weight in (model.get_topic(topic_id) or [])
            if word != "_"
        ]
        topics.append(
            Topic(
                topic_id=int(topic_id),
                keywords=words[:TOP_WORDS],
                members=np.flatnonzero(labels == topic_id).tolist(),
            )
        )
    if not topics:
        raise AnalysisError(
            "No recurring themes were found: every passage was classed as an outlier. "
            "Add more documents on related subjects and run the session again."
        )
    return TopicModelResult(assignments=labels, probabilities=probs, topics=topics)


def centroid(vectors: NDArray[np.float32]) -> NDArray[np.float32]:
    """L2-normalised mean of the given (normalised) embeddings."""
    mean = np.asarray(vectors, dtype=np.float32).mean(axis=0)
    norm = float(np.linalg.norm(mean))
    return mean / norm if norm > 0 else mean


def representative_passages(
    member_indices: list[int],
    embeddings: NDArray[np.float32],
    centre: NDArray[np.float32],
    top_n: int,
) -> list[tuple[int, float]]:
    """The ``top_n`` members closest to the topic centre: (passage index, cosine similarity)."""
    similarities = embeddings[member_indices] @ centre
    order = np.argsort(-similarities, kind="stable")[:top_n]
    return [(member_indices[i], float(similarities[i])) for i in order]
