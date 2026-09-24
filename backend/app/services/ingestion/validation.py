"""Upload validation (spec §7.2): reject unsupported or oversized files before processing.

The extension must be allowed *and* the leading bytes must match that format, so a
renamed executable or image cannot slip through as ".pdf".
"""
import io
import zipfile

from ...models import FileType
from ...utils.errors import ApiError, ValidationError

_SNIFF_BYTES = 8192


class UnsupportedFileError(ApiError):
    status_code = 415
    code = "UNSUPPORTED_FILE_TYPE"


class FileTooLargeError(ApiError):
    status_code = 413
    code = "PAYLOAD_TOO_LARGE"


def file_extension(filename):
    return filename.rsplit(".", 1)[-1].lower() if filename and "." in filename else ""


def _looks_like_pdf(head: bytes) -> bool:
    # The header may be preceded by a little junk; readers accept it within the first 1 KB.
    return b"%PDF-" in head[:1024]


def _looks_like_docx(data: bytes) -> bool:
    if not data.startswith(b"PK\x03\x04"):
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            return "word/document.xml" in zf.namelist()
    except zipfile.BadZipFile:
        return False


def _looks_like_text(head: bytes) -> bool:
    if b"\x00" in head:  # binary content (UTF-16 text is out of scope, see decode_text)
        return False
    try:
        head.decode("utf-8")
        return True
    except UnicodeDecodeError as exc:
        # A multi-byte char may be split at the sniff boundary; anything earlier is real.
        if exc.start >= len(head) - 3:
            return True
    # Legacy Windows encodings: accept if it is mostly printable.
    printable = sum(32 <= b < 127 or b in (9, 10, 13) or b >= 128 for b in head)
    return printable / max(len(head), 1) > 0.95


def validate_upload(filename, data: bytes, max_bytes: int) -> FileType:
    """Return the FileType for a valid upload or raise an ApiError."""
    ext = file_extension(filename)
    try:
        file_type = FileType(ext)
    except ValueError:
        raise UnsupportedFileError(
            "Unsupported file type. Upload PDF, DOCX or TXT files.",
            details={"file": f"'.{ext}' is not supported" if ext else "File has no extension"},
        )

    if len(data) == 0:
        raise ValidationError("The uploaded file is empty", details={"file": "Empty file"})
    if len(data) > max_bytes:
        raise FileTooLargeError(
            f"File exceeds the {max_bytes // (1024 * 1024)} MB limit",
            details={"file": f"{len(data)} bytes"},
        )

    head = data[:_SNIFF_BYTES]
    checks = {
        FileType.PDF: lambda: _looks_like_pdf(head),
        FileType.DOCX: lambda: _looks_like_docx(data),
        FileType.TXT: lambda: _looks_like_text(head),
    }
    if not checks[file_type]():
        raise UnsupportedFileError(
            f"File content does not match the .{ext} extension",
            details={"file": "Content/extension mismatch"},
        )
    return file_type
