"""Storage backends for uploaded documents and generated reports.

The database stores only generated UUID filenames. A backend maps those names to either
local filesystem paths or private Vercel Blob pathnames. Downloads continue to pass through
authorised API endpoints.
"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import Protocol

from flask import current_app

_STORED_NAME = re.compile(r"^[0-9a-f]{32}\.(pdf|docx|txt)$")
_AREAS = {"documents", "reports"}


class StorageBackend(Protocol):
    def save(self, content: bytes, extension: str, area: str = "documents") -> str: ...
    def read(self, stored_filename: str, area: str = "documents") -> bytes: ...
    def delete(self, stored_filename: str, area: str = "documents") -> None: ...
    def exists(self, stored_filename: str, area: str = "documents") -> bool: ...
    def size(self, stored_filename: str, area: str = "documents") -> int | None: ...


def _validate_area(area: str) -> str:
    if area not in _AREAS:
        raise ValueError(f"Unknown storage area: {area!r}")
    return area


def _validate_stored_filename(stored_filename: str) -> str:
    if not _STORED_NAME.match(stored_filename):
        raise ValueError(f"Invalid stored filename: {stored_filename!r}")
    return stored_filename


def _new_stored_filename(extension: str) -> str:
    extension = extension.lower()
    if extension not in {".pdf", ".docx", ".txt"}:
        raise ValueError(f"Unsupported storage extension: {extension!r}")
    return f"{uuid.uuid4().hex}{extension}"


class FileStorage:
    """Local filesystem storage rooted at STORAGE_DIR."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.documents_dir = self.root / "documents"
        self.reports_dir = self.root / "reports"

    def _dir(self, area: str) -> Path:
        _validate_area(area)
        return self.documents_dir if area == "documents" else self.reports_dir

    def path(self, stored_filename: str, area: str = "documents") -> Path:
        _validate_stored_filename(stored_filename)
        return self._dir(area) / stored_filename

    def save(self, content: bytes, extension: str, area: str = "documents") -> str:
        self._dir(area).mkdir(parents=True, exist_ok=True)
        stored_filename = _new_stored_filename(extension)
        target = self.path(stored_filename, area)
        temporary = target.with_suffix(target.suffix + ".part")
        temporary.write_bytes(content)
        os.replace(temporary, target)
        return stored_filename

    def read(self, stored_filename: str, area: str = "documents") -> bytes:
        return self.path(stored_filename, area).read_bytes()

    def delete(self, stored_filename: str, area: str = "documents") -> None:
        self.path(stored_filename, area).unlink(missing_ok=True)

    def exists(self, stored_filename: str, area: str = "documents") -> bool:
        return self.path(stored_filename, area).exists()

    def size(self, stored_filename: str, area: str = "documents") -> int | None:
        path = self.path(stored_filename, area)
        return path.stat().st_size if path.exists() else None


class VercelBlobStorage:
    """Private Vercel Blob storage using the official synchronous Python SDK."""

    access = "private"

    @staticmethod
    def _pathname(stored_filename: str, area: str = "documents") -> str:
        _validate_area(area)
        _validate_stored_filename(stored_filename)
        return f"{area}/{stored_filename}"

    @staticmethod
    def _blob_module():
        try:
            from vercel.blob import sync as blob
        except ImportError as exc:
            raise RuntimeError("Vercel Blob storage requires the 'vercel-blob' package.") from exc
        return blob

    def save(self, content: bytes, extension: str, area: str = "documents") -> str:
        stored_filename = _new_stored_filename(extension)
        self._blob_module().put_blob(
            self._pathname(stored_filename, area), content, access=self.access
        )
        return stored_filename

    def read(self, stored_filename: str, area: str = "documents") -> bytes:
        result = self._blob_module().get_blob(
            self._pathname(stored_filename, area), access=self.access
        )
        return result.body

    def delete(self, stored_filename: str, area: str = "documents") -> None:
        self._blob_module().delete_blob(self._pathname(stored_filename, area))

    def exists(self, stored_filename: str, area: str = "documents") -> bool:
        try:
            self._blob_module().head_blob(self._pathname(stored_filename, area))
        except Exception as exc:
            if exc.__class__.__name__ == "BlobNotFoundError":
                return False
            raise
        return True

    def size(self, stored_filename: str, area: str = "documents") -> int | None:
        try:
            return self._blob_module().head_blob(self._pathname(stored_filename, area)).size
        except Exception as exc:
            if exc.__class__.__name__ == "BlobNotFoundError":
                return None
            raise


def get_storage() -> StorageBackend:
    backend = current_app.config.get("STORAGE_BACKEND", "local")
    if backend == "local":
        return FileStorage(current_app.config["STORAGE_DIR"])
    if backend == "vercel_blob":
        return VercelBlobStorage()
    raise RuntimeError(f"Unknown STORAGE_BACKEND: {backend!r}")
