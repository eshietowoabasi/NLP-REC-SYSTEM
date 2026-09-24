"""Sentence splitting, passage grouping, heavy normalisation and the whole pipeline."""

from __future__ import annotations

import pytest
from spacy.language import Language

from app.models import FileType
from app.services.ingestion.parsers import ParseError
from app.services.ingestion.passages import PassageConfig, group_passages, split_sentences
from app.services.ingestion.pipeline import process_document
from app.services.preprocessing.normalise import StopWords, normalise_spans
from app.services.preprocessing.spacy_model import get_nlp
from tests.documents import JOB_AD_TEXT, SECURITY_TEXT, make_docx, make_pdf


@pytest.fixture(scope="module")
def nlp() -> Language:
    return get_nlp("en_core_web_sm")


def sentences_of(nlp: Language, text: str, max_words: int = 200):
    return split_sentences([text], nlp, page_numbers=False, max_words=max_words)


FILLER = [
    "engineers",
    "build",
    "reliable",
    "cloud",
    "services",
    "for",
    "banking",
    "customers",
    "across",
    "Nigeria",
]


def numbered(count: int, words_each: int) -> str:
    """``count`` natural-looking sentences of exactly ``words_each`` words each."""
    sentences = []
    for _ in range(count):
        words = [FILLER[i % len(FILLER)] for i in range(words_each)]
        words[0] = words[0].capitalize()
        sentences.append(" ".join(words) + ".")
    return " ".join(sentences)


# ------------------------------------------------------------------------- config


def test_passage_config_validation() -> None:
    with pytest.raises(ValueError):
        PassageConfig(min_sentences=4, max_sentences=3)
    with pytest.raises(ValueError):
        PassageConfig(min_words=300, max_words=200)
    config = PassageConfig.from_settings({"min": 2, "max": 4}, {"min": 50, "max": 120})
    assert (config.min_sentences, config.max_words) == (2, 120)


# ---------------------------------------------------------------------- grouping


def test_long_sentences_close_a_passage_at_the_word_target(nlp: Language) -> None:
    passages = group_passages(sentences_of(nlp, numbered(9, 40)), PassageConfig())

    # 3 sentences x 40 words = 120 words reaches both minimums (3 sentences, 100 words).
    assert [len(p.sentences) for p in passages] == [3, 3, 3]
    assert all(100 <= p.words <= 200 for p in passages)


def test_short_sentences_are_capped_at_max_sentences(nlp: Language) -> None:
    passages = group_passages(sentences_of(nlp, numbered(10, 8)), PassageConfig())

    assert [len(p.sentences) for p in passages] == [5, 5]


def test_a_passage_never_exceeds_max_words(nlp: Language) -> None:
    passages = group_passages(sentences_of(nlp, numbered(6, 90)), PassageConfig())

    assert all(p.words <= 200 for p in passages)


def test_over_long_sentence_is_split_into_chunks(nlp: Language) -> None:
    one_long_sentence = "Skills " + " ".join(["python"] * 449) + "."

    sentences = sentences_of(nlp, one_long_sentence, max_words=200)

    assert [s.words for s in sentences] == [200, 200, 50]


def test_short_tail_is_merged_into_the_previous_passage(nlp: Language) -> None:
    text = numbered(3, 40) + " Short tail here."

    passages = group_passages(sentences_of(nlp, text), PassageConfig())

    assert len(passages) == 1
    assert passages[0].text.endswith("Short tail here.")


def test_positions_are_sequential_and_pdf_pages_are_kept(nlp: Language) -> None:
    sentences = split_sentences(
        [numbered(3, 40), numbered(3, 40)], nlp, page_numbers=True, max_words=200
    )

    passages = group_passages(sentences, PassageConfig())

    assert [(p.position, p.page_number) for p in passages] == [(0, 1), (1, 2)]


def test_sentences_without_letters_are_dropped(nlp: Language) -> None:
    sentences = sentences_of(nlp, "2024. 10:30. Python developers wanted.")

    assert [s.text for s in sentences] == ["Python developers wanted."]


# ------------------------------------------------------------------ normalisation


def test_normalisation_lowercases_lemmatises_and_drops_stop_words(nlp: Language) -> None:
    stop_words = StopWords.build(["candidate", "experience", "year"])
    doc = nlp("Candidates must have 3 years' experience with REST APIs in Python.")

    tokens = normalise_spans([doc[:]], stop_words).split()

    assert tokens == ["rest", "api", "python"]  # lemmas, lowercase, stop words and "3" gone


def test_normalisation_removes_multi_word_custom_stop_words(nlp: Language) -> None:
    stop_words = StopWords.build(["Port Harcourt", "full-time"])
    doc = nlp("Full-time DevOps role based in Port Harcourt with Kubernetes.")

    normalised = normalise_spans([doc[:]], stop_words)

    assert "port" not in normalised and "harcourt" not in normalised
    assert "full" not in normalised
    assert "devops" in normalised and "kubernetes" in normalised


def test_normalisation_keeps_technology_names(nlp: Language) -> None:
    doc = nlp("We use C++, Node.js and HTML5 daily.")

    normalised = normalise_spans([doc[:]], StopWords.build())

    assert "c++" in normalised and "node.js" in normalised and "html5" in normalised


# ----------------------------------------------------------------------- pipeline


def test_pipeline_on_a_pdf(nlp: Language) -> None:
    output = process_document(
        FileType.PDF,
        make_pdf([JOB_AD_TEXT, SECURITY_TEXT]),
        nlp,
        StopWords.build(["candidate"]),
        PassageConfig(),
    )

    assert output.page_count == 2
    assert output.word_count > 40
    assert output.passages[0].page_number == 1
    # Original wording kept for NER/SBERT; normalised copy for TF-IDF.
    assert "RESTful APIs" in output.passages[0].text
    assert output.passages[0].normalised_text == output.passages[0].normalised_text.lower()


def test_pipeline_on_a_docx_has_no_page_numbers(nlp: Language) -> None:
    output = process_document(
        FileType.DOCX, make_docx([JOB_AD_TEXT]), nlp, StopWords.build(), PassageConfig()
    )

    assert output.page_count is None
    assert all(p.page_number is None for p in output.passages)


def test_pipeline_rejects_documents_without_sentences(nlp: Language) -> None:
    with pytest.raises(ParseError):
        process_document(FileType.TXT, b"12345 67890", nlp, StopWords.build(), PassageConfig())
