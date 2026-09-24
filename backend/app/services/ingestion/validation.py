"""Upload validation: extension, real content type (magic bytes) and size.

Runs on the uploaded bytes before anything is saved. The file type is decided by the content,
not the name: a renamed image or executable is rejected even with a ``.pdf`` extension.
"""

from __future__ import annotations

import io
import logging
import zipfile
from dataclasses import dataclass
from functools import cache
from pathlib import PurePath
from typing import Any

from app.models.enums import FileType

logger = logging.getLogger(__name__)

MAX_FILE_BYTES = 25 * 1024 * 1024
ALLOWED_EXTENSIONS: dict[str, FileType] = {
    ".pdf": FileType.PDF,
    ".docx": FileType.DOCX,
    ".txt": FileType.TXT,
}
# libmagic reports DOCX as a Word document on recent versions, and as a plain ZIP on older ones.
_DOCX_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/zip",
    "application/octet-stream",
}


class UploadRejectedError(ValueError):
    """The file cannot be accepted; ``str(exc)`` is a message suitable for the uploader."""


@dataclass(frozen=True)
class ValidatedUpload:
    file_type: FileType
    extension: str
    size: int


@cache
def _libmagic() -> Any | None:
    """The ``magic`` module, or None when the libmagic system library is not installed.

    Docker images install libmagic; a native Windows setup usually lacks it, in which case
    the signature checks in :func:`validate_upload` are used on their own.
    """
    try:
        import magic

        magic.from_buffer(b"%PDF-1.7", mime=True)
        return magic
    except (ImportError, OSError):
        logger.warning("libmagic is not available; using built-in file signature checks only.")
        return None


def detect_mime(content: bytes) -> str | None:
    """MIME type from the file's content (libmagic), or None if libmagic is unavailable."""
    magic = _libmagic()
    if magic is None:
        return None
    return str(magic.from_buffer(content[:8192], mime=True))


def _is_docx(content: bytes) -> bool:
    """A DOCX is a ZIP archive containing ``word/document.xml``."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            return "word/document.xml" in archive.namelist()
    except zipfile.BadZipFile:
        return False


def _looks_like_text(content: bytes) -> bool:
    """Plain text has no NUL bytes (binary formats almost always do)."""
    return b"\x00" not in content[:65536]


def validate_upload(filename: str, content: bytes) -> ValidatedUpload:
    """Check an uploaded file and return its type, or raise :class:`UploadRejectedError`."""
    extension = PurePath(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise UploadRejectedError("Unsupported file type. Upload PDF, DOCX or TXT files.")
    size = len(content)
    if size == 0:
        raise UploadRejectedError("The file is empty.")
    if size > MAX_FILE_BYTES:
        raise UploadRejectedError("The file is larger than the 25 MB limit.")

    file_type = ALLOWED_EXTENSIONS[extension]
    mime = detect_mime(content)
    # Both the libmagic verdict (when available) and the format's own signature must agree.
    if file_type is FileType.PDF:
        valid = mime in (None, "application/pdf") and content.startswith(b"%PDF-")
    elif file_type is FileType.DOCX:
        valid = (mime is None or mime in _DOCX_MIME_TYPES) and _is_docx(content)
    else:
        valid = (mime is None or mime.startswith("text/")) and _looks_like_text(content)
    if not valid:
        detected = f" (detected {mime})" if mime else ""
        raise UploadRejectedError(
            f"The file content does not match its .{file_type.value} extension{detected}."
        )
    return ValidatedUpload(file_type=file_type, extension=extension, size=size)
