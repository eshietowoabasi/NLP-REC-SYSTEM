"""Storage of uploaded files on the local storage volume.

Files are saved under random UUID names (the original filename is only kept in the database),
so user-supplied names never reach the filesystem. Files are never served from a public path;
downloads go through an authorised API endpoint.
"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

from flask import current_app

_STORED_NAME = re.compile(r"^[0-9a-f]{32}\.(pdf|docx|txt)$")


class FileStorage:
    """Documents live in ``<root>/documents/<uuid>.<ext>``."""

    def __init__(self, root: str | Path) -> None:
        self.documents_dir = Path(root) / "documents"

    def path(self, stored_filename: str) -> Path:
        """Absolute path of a stored file; rejects anything that is not a generated name."""
        if not _STORED_NAME.match(stored_filename):
            raise ValueError(f"Invalid stored filename: {stored_filename!r}")
        return self.documents_dir / stored_filename

    def save(self, content: bytes, extension: str) -> str:
        """Write ``content`` under a new UUID name and return that name."""
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        stored_filename = f"{uuid.uuid4().hex}{extension.lower()}"
        target = self.path(stored_filename)
        temporary = target.with_suffix(target.suffix + ".part")
        temporary.write_bytes(content)
        os.replace(temporary, target)  # atomic: readers never see a half-written file
        return stored_filename

    def read(self, stored_filename: str) -> bytes:
        return self.path(stored_filename).read_bytes()

    def delete(self, stored_filename: str) -> None:
        self.path(stored_filename).unlink(missing_ok=True)


def get_storage() -> FileStorage:
    """Storage rooted at the app's ``STORAGE_DIR``."""
    return FileStorage(current_app.config["STORAGE_DIR"])
