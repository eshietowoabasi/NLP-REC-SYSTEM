"""Accepting uploaded files: validate, reject duplicates, store, create the Document row.

Used by the document library upload and the admin NUC core upload.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import PurePath

from sqlalchemy import select
from werkzeug.datastructures import FileStorage as UploadedFile

from app.extensions import db
from app.models import Document, DocumentStatus, SourceCategory, User
from app.services.ingestion.validation import MAX_FILE_BYTES, UploadRejectedError, validate_upload
from app.services.storage import get_storage

MAX_TITLE_LENGTH = 255


def title_from_filename(filename: str) -> str:
    """ "nigeria_ict-policy_2024.pdf" → "nigeria ict policy 2024"."""
    stem = PurePath(filename).stem
    title = " ".join(re.sub(r"[_\-]+", " ", stem).split())
    return (title or "Untitled document")[:MAX_TITLE_LENGTH]


def read_upload(upload: UploadedFile) -> bytes:
    """Read an uploaded file, stopping just past the size limit."""
    return upload.stream.read(MAX_FILE_BYTES + 1)


def find_duplicate(content_hash: str) -> Document | None:
    """An existing, non-archived document with exactly the same content."""
    return db.session.scalar(
        select(Document).where(
            Document.content_hash == content_hash,
            Document.processing_status != DocumentStatus.ARCHIVED,
        )
    )


def store_upload(upload: UploadedFile, category: SourceCategory, uploader: User) -> Document:
    """Validate and save one uploaded file and add its Document row (the caller commits).

    Raises UploadRejectedError with a message for the uploader. The file is written to storage
    before the row is committed; on a failed commit the caller removes it (see ``discard``).
    """
    filename = PurePath(upload.filename or "").name
    if not filename:
        raise UploadRejectedError("The file has no name.")
    content = read_upload(upload)
    checked = validate_upload(filename, content)

    content_hash = hashlib.sha256(content).hexdigest()
    duplicate = find_duplicate(content_hash)
    if duplicate is not None:
        raise UploadRejectedError(f"This file has already been uploaded as “{duplicate.title}”.")

    stored_filename = get_storage().save(content, checked.extension)
    document = Document(
        uploaded_by_id=uploader.id,
        title=title_from_filename(filename),
        original_filename=filename[:MAX_TITLE_LENGTH],
        stored_filename=stored_filename,
        file_type=checked.file_type,
        file_size=checked.size,
        content_hash=content_hash,
        source_category=category,
        processing_status=DocumentStatus.UPLOADED,
    )
    db.session.add(document)
    db.session.flush()
    return document


def discard(documents: list[Document]) -> None:
    """Remove stored files of documents whose rows were not committed."""
    storage = get_storage()
    for document in documents:
        storage.delete(document.stored_filename)
