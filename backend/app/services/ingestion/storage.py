"""Local file storage for uploads (docs/DECISIONS.md, D7).

Files are stored under a random UUID name; the user-supplied filename is kept only as metadata.
"""
import hashlib
import os
import uuid
from pathlib import Path


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_bytes(data: bytes, upload_folder: str, extension: str) -> str:
    folder = Path(upload_folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{uuid.uuid4().hex}.{extension}"
    with open(path, "xb") as fh:
        fh.write(data)
    return str(path)


def delete_file(path: str) -> None:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
