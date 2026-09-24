"""Parsers (PDF per page, DOCX paragraphs + tables, TXT encodings) and light cleaning."""

from __future__ import annotations

import pymupdf
import pytest

from app.models import FileType
from app.services.ingestion.cleaning import clean_pages, count_words, remove_headers_footers
from app.services.ingestion.parsers import (
    SCANNED_PDF_MESSAGE,
    ParseError,
    decode_text,
    parse_file,
)
from tests.documents import (
    FINTECH_TEXT,
    JOB_AD_TEXT,
    SECURITY_TEXT,
    make_blank_pdf,
    make_docx,
    make_pdf,
)

# ------------------------------------------------------------------------------ PDF


def test_pdf_is_parsed_page_by_page() -> None:
    parsed = parse_file(FileType.PDF, make_pdf([JOB_AD_TEXT, SECURITY_TEXT]))

    assert parsed.page_count == 2
    assert "Django" in parsed.pages[0]
    assert "Splunk" in parsed.pages[1]


def test_scanned_pdf_without_text_is_rejected() -> None:
    with pytest.raises(ParseError, match="scanned PDF"):
        parse_file(FileType.PDF, make_blank_pdf())
    assert SCANNED_PDF_MESSAGE == "No extractable text (scanned PDF). OCR is not supported."


def test_password_protected_pdf_is_rejected() -> None:
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), JOB_AD_TEXT)
    encrypted = document.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="secret")

    with pytest.raises(ParseError, match="password-protected"):
        parse_file(FileType.PDF, encrypted)


def test_damaged_pdf_is_rejected() -> None:
    with pytest.raises(ParseError, match="damaged"):
        parse_file(FileType.PDF, b"%PDF-1.7 this is not really a pdf")


# ----------------------------------------------------------------------------- DOCX


def test_docx_includes_paragraphs_and_tables_in_order() -> None:
    content = make_docx(
        ["Required skills", "Strong Python knowledge"],
        table=[["Skill", "Level"], ["PostgreSQL", "Advanced"], ["Docker", "Intermediate"]],
    )

    parsed = parse_file(FileType.DOCX, content)

    assert parsed.page_count is None
    text = parsed.pages[0]
    assert text.index("Required skills") < text.index("PostgreSQL | Advanced.")
    assert "Docker | Intermediate." in text


def test_damaged_docx_is_rejected() -> None:
    with pytest.raises(ParseError, match="damaged"):
        parse_file(FileType.DOCX, b"PK\x03\x04 broken zip")


# ------------------------------------------------------------------------------ TXT


def test_txt_utf8_with_bom() -> None:
    assert decode_text("﻿Café Lagos".encode()) == "Café Lagos"


def test_txt_in_windows_1252() -> None:
    text = "Naïve résumé for a café in Calabar – “quoted”"
    assert decode_text(text.encode("cp1252")) == text


def test_txt_with_bytes_undefined_in_windows_1252_still_decodes() -> None:
    # 0x81 and 0x90 are undefined in Windows-1252, forcing the later fallbacks.
    text = decode_text(b"Python developer role \x81\x90 in Uyo.")

    assert text.startswith("Python developer role")
    assert text.endswith("in Uyo.")


def test_txt_without_text_is_rejected() -> None:
    with pytest.raises(ParseError, match="no text"):
        parse_file(FileType.TXT, b"   \n\t  ")


# ------------------------------------------------------------------------ cleaning


def test_repeated_headers_and_page_numbers_are_removed() -> None:
    parsed = parse_file(
        FileType.PDF,
        make_pdf(
            [JOB_AD_TEXT, SECURITY_TEXT, FINTECH_TEXT],
            header="Synthetic Careers Bulletin",
            footer=True,
        ),
    )

    cleaned = clean_pages(parsed.pages)

    joined = " ".join(cleaned)
    assert "Synthetic Careers Bulletin" not in joined
    assert "Page 2 of 3" not in joined
    assert "Splunk" in cleaned[1]


def test_headers_are_kept_for_short_documents() -> None:
    pages = ["Report title\nBody one.", "Report title\nBody two."]

    assert remove_headers_footers(pages) == pages


def test_long_repeated_lines_are_not_treated_as_headers() -> None:
    long_line = "This sentence is repeated on every page but it is far too long to be a header line"
    bodies = ["Cloud engineers.", "Data analysts.", "Security teams.", "Mobile developers."]
    pages = [f"{long_line}\n{body}" for body in bodies]

    assert remove_headers_footers(pages) == pages


def test_cleaning_rejoins_hyphenation_and_removes_urls_emails_and_bullets() -> None:
    raw = (
        "We build data pipe-\nlines at scale.\n"
        "• Deploy services to AWS\n"
        "- Write unit tests\n"
        "Apply at https://careers.example.com or hr@example.com today."
    )

    (cleaned,) = clean_pages([raw])

    assert "pipelines" in cleaned
    assert "Deploy services to AWS." in cleaned  # bullet removed, full stop added
    assert "Write unit tests." in cleaned
    assert "example.com" not in cleaned
    assert "•" not in cleaned


def test_cleaning_normalises_unicode_and_whitespace() -> None:
    (cleaned,) = clean_pages(["ﬁnance   and ﬂow"])

    assert cleaned == "finance and flow"


def test_short_headings_become_their_own_sentence() -> None:
    (cleaned,) = clean_pages(["Key Responsibilities\nMaintain Linux servers daily."])

    assert cleaned.startswith("Key Responsibilities. Maintain")


def test_count_words() -> None:
    assert count_words("one two  three\nfour") == 4
