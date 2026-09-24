"""File storage safety, and the real SBERT encoder."""

from __future__ import annotations

import numpy as np
import pytest

from app.services.embeddings.encoder import get_encoder
from app.services.storage import FileStorage


def test_storage_round_trip(tmp_path) -> None:
    storage = FileStorage(tmp_path)

    name = storage.save(b"content", ".PDF")

    assert name.endswith(".pdf") and len(name) == 36
    assert storage.read(name) == b"content"
    storage.delete(name)
    assert not storage.path(name).exists()
    storage.delete(name)  # deleting twice is harmless


@pytest.mark.parametrize(
    "name", ["../secret.pdf", "..\\secret.pdf", "report.pdf", "0" * 32 + ".exe", ""]
)
def test_storage_rejects_names_it_did_not_generate(tmp_path, name: str) -> None:
    with pytest.raises(ValueError):
        FileStorage(tmp_path).path(name)


@pytest.mark.real_models
@pytest.mark.usefixtures("app")  # as in the worker: the app (and its TLS setting) comes first
def test_real_sbert_embeddings_are_normalised_and_meaningful() -> None:
    encoder = get_encoder("all-MiniLM-L6-v2")

    vectors = encoder.encode(
        [
            "Build REST APIs with Python and Django.",
            "Develop backend web services using Python frameworks.",
            "Harvest cassava and yams on the family farm.",
        ]
    )

    assert vectors.shape == (3, 384)
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5)
    related, unrelated = vectors[0] @ vectors[1], vectors[0] @ vectors[2]
    assert related > unrelated + 0.2
    assert encoder.encode([]).shape == (0, 384)
