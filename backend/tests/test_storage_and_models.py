"""File storage safety, and the real SBERT encoder."""

from __future__ import annotations

import numpy as np
import pytest

from app.services.embeddings.encoder import get_encoder
from app.services.storage import FileStorage, VercelBlobStorage


def test_storage_round_trip(tmp_path) -> None:
    storage = FileStorage(tmp_path)

    name = storage.save(b"content", ".PDF")

    assert name.endswith(".pdf") and len(name) == 36
    assert storage.read(name) == b"content"
    assert storage.exists(name)
    assert storage.size(name) == len(b"content")
    storage.delete(name)
    assert not storage.exists(name)
    assert storage.size(name) is None
    storage.delete(name)  # deleting twice is harmless


@pytest.mark.parametrize(
    "name", ["../secret.pdf", "..\\secret.pdf", "report.pdf", "0" * 32 + ".exe", ""]
)
def test_storage_rejects_names_it_did_not_generate(tmp_path, name: str) -> None:
    with pytest.raises(ValueError):
        FileStorage(tmp_path).path(name)


class FakeBlob:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_blob(self, pathname, content, *, access):
        assert access == "private"
        self.objects[pathname] = bytes(content)

    def get_blob(self, pathname, *, access):
        assert access == "private"
        return type("Result", (), {"body": self.objects[pathname]})()

    def head_blob(self, pathname):
        if pathname not in self.objects:
            raise type("BlobNotFoundError", (Exception,), {})()
        return type("Head", (), {"size": len(self.objects[pathname])})()

    def delete_blob(self, pathname):
        self.objects.pop(pathname, None)


def test_vercel_blob_storage_contract(monkeypatch) -> None:
    fake = FakeBlob()
    storage = VercelBlobStorage()
    monkeypatch.setattr(storage, "_blob_module", lambda: fake)
    name = storage.save(b"content", ".PDF")
    assert name.endswith(".pdf") and len(name) == 36
    assert storage.read(name) == b"content"
    assert storage.exists(name)
    assert storage.size(name) == 7
    storage.delete(name)
    assert not storage.exists(name)
    assert storage.size(name) is None


def test_vercel_blob_uses_separate_report_prefix(monkeypatch) -> None:
    fake = FakeBlob()
    storage = VercelBlobStorage()
    monkeypatch.setattr(storage, "_blob_module", lambda: fake)
    name = storage.save(b"report", ".docx", area="reports")
    assert f"reports/{name}" in fake.objects


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
