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
    """Documents live in ``<root>/documents/<uuid>.<ext>``, generated reports in
    ``<root>/reports/<uuid>.<ext>``. Methods take ``area="reports"`` for report files."""

    def __init__(self, root: str | Path) -> None:
        self.documents_dir = Path(root) / "documents"
        self.reports_dir = Path(root) / "reports"

    def _dir(self, area: str) -> Path:
        if area == "documents":
            return self.documents_dir
        if area == "reports":
            return self.reports_dir
        raise ValueError(f"Unknown storage area: {area!r}")

    def path(self, stored_filename: str, area: str = "documents") -> Path:
        """Absolute path of a stored file; rejects anything that is not a generated name."""
        if not _STORED_NAME.match(stored_filename):
            raise ValueError(f"Invalid stored filename: {stored_filename!r}")
        return self._dir(area) / stored_filename

    def save(self, content: bytes, extension: str, area: str = "documents") -> str:
        """Write ``content`` under a new UUID name and return that name."""
        self._dir(area).mkdir(parents=True, exist_ok=True)
        stored_filename = f"{uuid.uuid4().hex}{extension.lower()}"
        target = self.path(stored_filename, area)
        temporary = target.with_suffix(target.suffix + ".part")
        temporary.write_bytes(content)
        os.replace(temporary, target)  # atomic: readers never see a half-written file
        return stored_filename

    def read(self, stored_filename: str, area: str = "documents") -> bytes:
        return self.path(stored_filename, area).read_bytes()

    def delete(self, stored_filename: str, area: str = "documents") -> None:
        self.path(stored_filename, area).unlink(missing_ok=True)


def get_storage() -> FileStorage:
    """Storage rooted at the app's ``STORAGE_DIR``."""
    return FileStorage(current_app.config["STORAGE_DIR"])
