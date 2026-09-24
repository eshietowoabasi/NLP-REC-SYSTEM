"""Upload validation: extension, content type by magic bytes, size."""

from __future__ import annotations

import pytest

from app.models import FileType
from app.services.ingestion import validation
from app.services.ingestion.validation import MAX_FILE_BYTES, UploadRejectedError, validate_upload
from tests.documents import JOB_AD_TEXT, make_docx, make_pdf

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture(params=["libmagic", "signatures-only"])
def detection(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> str:
    """Run each test with libmagic (when installed) and with the signature-only fallback."""
    if request.param == "signatures-only":
        monkeypatch.setattr(validation, "detect_mime", lambda _content: None)
    elif validation.detect_mime(b"%PDF-1.7") is None:
        pytest.skip("libmagic is not installed on this machine")
    return request.param


@pytest.mark.usefixtures("detection")
class TestValidateUpload:
    def test_accepts_pdf_docx_and_txt(self) -> None:
        assert validate_upload("ad.pdf", make_pdf([JOB_AD_TEXT])).file_type is FileType.PDF
        assert validate_upload("ad.DOCX", make_docx([JOB_AD_TEXT])).file_type is FileType.DOCX
        assert validate_upload("ad.txt", JOB_AD_TEXT.encode()).file_type is FileType.TXT

    @pytest.mark.parametrize("name", ["report.doc", "slides.pptx", "image.png", "noextension"])
    def test_rejects_other_extensions(self, name: str) -> None:
        with pytest.raises(UploadRejectedError, match="Unsupported file type"):
            validate_upload(name, b"whatever")

    def test_rejects_empty_file(self) -> None:
        with pytest.raises(UploadRejectedError, match="empty"):
            validate_upload("empty.txt", b"")

    def test_rejects_oversized_file(self) -> None:
        with pytest.raises(UploadRejectedError, match="25 MB"):
            validate_upload("big.txt", b"a" * (MAX_FILE_BYTES + 1))

    @pytest.mark.parametrize(
        ("name", "content"),
        [
            ("fake.pdf", PNG_BYTES),  # an image renamed to .pdf
            ("fake.pdf", JOB_AD_TEXT.encode()),  # text renamed to .pdf
            ("fake.docx", make_pdf([JOB_AD_TEXT])),  # a PDF renamed to .docx
            ("fake.txt", PNG_BYTES),  # binary renamed to .txt
        ],
    )
    def test_rejects_content_that_does_not_match_the_extension(
        self, name: str, content: bytes
    ) -> None:
        with pytest.raises(UploadRejectedError, match="does not match"):
            validate_upload(name, content)

    def test_rejects_zip_that_is_not_a_word_document(self) -> None:
        import io
        import zipfile

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("readme.txt", "not a docx")
        with pytest.raises(UploadRejectedError):
            validate_upload("archive.docx", buffer.getvalue())
