"""Sentence embedding backends (spec §8.4; docs/DECISIONS.md, D1).

- ``sbert``: Sentence-Transformers model (default ``all-MiniLM-L6-v2``). Production.
- ``hashing``: deterministic hashed bag of words/bigrams. No downloads; used by the
  test suite and for offline development. It captures lexical, not semantic,
  similarity, so it must not be used for evaluation or real recommendations.

All backends return L2-normalised float32 arrays, so cosine similarity is a dot product.
"""
from functools import lru_cache

import numpy as np

DEFAULT_SBERT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class EmbeddingUnavailableError(RuntimeError):
    pass


def _normalise(vectors: np.ndarray) -> np.ndarray:
    vectors = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


class SentenceTransformerEmbedder:
    backend = "sbert"

    def __init__(self, model_name: str = DEFAULT_SBERT_MODEL, batch_size: int = 64):
        self.model_name = model_name
        self.batch_size = batch_size
        self._model = None

    @property
    def model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise EmbeddingUnavailableError(
                    "sentence-transformers is not installed; install it or set EMBEDDING_BACKEND=hashing for offline development"
                ) from exc
            try:
                self._model = SentenceTransformer(self.model_name, device="cpu")
            except Exception as exc:
                raise EmbeddingUnavailableError(f"Could not load SBERT model '{self.model_name}': {exc}") from exc
        return self._model

    @property
    def dimension(self) -> int:
        # get_embedding_dimension() in sentence-transformers >= 6; the old name is a deprecated alias.
        getter = getattr(self.model, "get_embedding_dimension", None) or self.model.get_sentence_embedding_dimension
        return int(getter())

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        vectors = self.model.encode(
            texts, batch_size=self.batch_size, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True
        )
        return _normalise(vectors)


class HashingEmbedder:
    backend = "hashing"

    def __init__(self, dimension: int = 512):
        from sklearn.feature_extraction.text import HashingVectorizer

        self.model_name = f"hashing-{dimension}"
        self.dimension = dimension
        self._vectorizer = HashingVectorizer(
            n_features=dimension, ngram_range=(1, 2), stop_words="english", alternate_sign=False, norm=None
        )

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        return _normalise(self._vectorizer.transform(texts).toarray())


@lru_cache(maxsize=4)
def get_embedder(backend: str = "sbert", model_name: str = DEFAULT_SBERT_MODEL):
    """Cached so the SBERT model is loaded once per worker process."""
    if backend == "sbert":
        return SentenceTransformerEmbedder(model_name)
    if backend == "hashing":
        return HashingEmbedder()
    raise ValueError(f"Unknown embedding backend '{backend}'")


def mean_embedding(vectors: np.ndarray) -> np.ndarray | None:
    if len(vectors) == 0:
        return None
    return _normalise(vectors.mean(axis=0, keepdims=True))[0]
