"""SBERT sentence embeddings.

The model is loaded once per process and reused (``get_encoder`` is cached). Embeddings are
L2-normalised, so the cosine similarity of two embeddings is simply their dot product.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

import numpy as np
from numpy.typing import NDArray


class Encoder(Protocol):
    """Anything that turns texts into L2-normalised vectors (the real model, or a test fake)."""

    model_name: str

    def encode(self, texts: list[str]) -> NDArray[np.float32]: ...


class SentenceTransformerEncoder:
    """Wraps a sentence-transformers model running on the CPU."""

    def __init__(self, model_name: str, batch_size: int = 32) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.batch_size = batch_size
        self._model = SentenceTransformer(model_name, device="cpu")

    def encode(self, texts: list[str]) -> NDArray[np.float32]:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        vectors = self._model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)

    @property
    def dimension(self) -> int:
        return int(self._model.get_embedding_dimension() or 0)


@lru_cache(maxsize=2)
def get_encoder(model_name: str) -> Encoder:
    """Load (once per process) the SBERT model called ``model_name``."""
    return SentenceTransformerEncoder(model_name)
