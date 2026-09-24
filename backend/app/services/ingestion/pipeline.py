"""Document ingestion pipeline (without the database).

    bytes → parse → light clean → sentences → passages → normalised text

Embeddings are added afterwards by the ingestion job, which also stores the results.
"""

from __future__ import annotations

from dataclasses import dataclass

from spacy.language import Language

from app.models.enums import FileType
from app.services.ingestion.cleaning import clean_pages, count_words
from app.services.ingestion.parsers import ParseError, parse_file
from app.services.ingestion.passages import PassageConfig, group_passages, split_sentences
from app.services.preprocessing.normalise import StopWords, normalise_spans


@dataclass(frozen=True)
class PassageData:
    """One passage ready to be stored."""

    position: int
    page_number: int | None
    text: str
    normalised_text: str
    word_count: int


@dataclass(frozen=True)
class IngestionOutput:
    page_count: int | None
    word_count: int
    passages: list[PassageData]


def process_document(
    file_type: FileType,
    content: bytes,
    nlp: Language,
    stop_words: StopWords,
    config: PassageConfig,
) -> IngestionOutput:
    """Turn an uploaded file into passages. Raises ParseError for unusable documents."""
    parsed = parse_file(file_type, content)
    pages = clean_pages(parsed.pages)
    word_count = sum(count_words(page) for page in pages)
    if word_count == 0:
        raise ParseError("The document contains no text after cleaning.")

    sentences = split_sentences(
        pages, nlp, page_numbers=parsed.page_count is not None, max_words=config.max_words
    )
    passages = group_passages(sentences, config)
    if not passages:
        raise ParseError("No sentences could be extracted from the document.")

    return IngestionOutput(
        page_count=parsed.page_count,
        word_count=word_count,
        passages=[
            PassageData(
                position=passage.position,
                page_number=passage.page_number,
                text=passage.text,
                normalised_text=normalise_spans(passage.spans, stop_words),
                word_count=passage.words,
            )
            for passage in passages
        ],
    )
