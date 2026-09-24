"""Sentence splitting and grouping of sentences into passages (the unit of analysis).

A passage is 3–5 consecutive sentences (configurable) and, where sentences allow, roughly
100–200 words. Passages keep the page number of their first sentence. Passages are needed
because SBERT models truncate long inputs (all-MiniLM-L6-v2 reads at most 256 word pieces).

Grouping rules, applied sentence by sentence:

* a passage is closed once it has at least ``min_sentences`` sentences and ``min_words``
  words, or when it reaches ``max_sentences`` sentences or ``max_words`` words;
* a sentence that would push the passage over ``max_words`` starts a new passage;
* a single sentence longer than ``max_words`` (e.g. a long table row) is cut into chunks;
* a fragment left at the end (fewer than ``min_sentences`` sentences and under half of
  ``min_words``) is merged into the previous passage when the result fits in ``max_words``;
  this is the only case where a passage may exceed ``max_sentences``.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from spacy.language import Language
from spacy.tokens import Span


@dataclass(frozen=True)
class PassageConfig:
    min_sentences: int = 3
    max_sentences: int = 5
    min_words: int = 100
    max_words: int = 200

    def __post_init__(self) -> None:
        if not (1 <= self.min_sentences <= self.max_sentences):
            raise ValueError("Passage sentence limits must satisfy 1 <= min <= max.")
        if not (1 <= self.min_words <= self.max_words):
            raise ValueError("Passage word limits must satisfy 1 <= min <= max.")

    @classmethod
    def from_settings(cls, sentences: dict[str, int], words: dict[str, int]) -> PassageConfig:
        return cls(
            min_sentences=int(sentences["min"]),
            max_sentences=int(sentences["max"]),
            min_words=int(words["min"]),
            max_words=int(words["max"]),
        )


@dataclass
class Sentence:
    """A sentence (or a chunk of an over-long sentence) with its page number."""

    span: Span
    page_number: int | None

    @property
    def text(self) -> str:
        return self.span.text.strip()

    @property
    def words(self) -> int:
        return sum(1 for token in self.span if not (token.is_space or token.is_punct))


@dataclass
class Passage:
    """Consecutive sentences grouped together; ``position`` is 0-based within the document."""

    position: int
    page_number: int | None
    sentences: list[Sentence]

    @property
    def text(self) -> str:
        return " ".join(sentence.text for sentence in self.sentences)

    @property
    def spans(self) -> list[Span]:
        return [sentence.span for sentence in self.sentences]

    @property
    def words(self) -> int:
        return sum(sentence.words for sentence in self.sentences)


def _chunks(span: Span, max_words: int) -> Iterator[Span]:
    """Cut a span into consecutive sub-spans of at most ``max_words`` words."""
    start = span.start
    words = 0
    for token in span:
        if not (token.is_space or token.is_punct):
            words += 1
        if words > max_words:
            yield span.doc[start : token.i]
            start = token.i
            words = 1
    if start < span.end:
        yield span.doc[start : span.end]


def split_sentences(
    pages: list[str], nlp: Language, page_numbers: bool, max_words: int
) -> list[Sentence]:
    """Split every page into sentences. Sentences without letters are dropped.

    ``page_numbers`` is True for PDFs (page ``i`` of ``pages`` is page ``i + 1``); DOCX and TXT
    have no page numbers.
    """
    sentences: list[Sentence] = []
    # Named entities are not needed here; skipping NER makes ingestion faster.
    with nlp.select_pipes(disable=[name for name in ("ner",) if name in nlp.pipe_names]):
        for index, doc in enumerate(nlp.pipe(pages)):
            page_number = index + 1 if page_numbers else None
            for sent in doc.sents:
                if not any(char.isalpha() for char in sent.text):
                    continue
                for chunk in _chunks(sent, max_words):
                    if chunk.text.strip():
                        sentences.append(Sentence(span=chunk, page_number=page_number))
    return sentences


def group_passages(sentences: list[Sentence], config: PassageConfig) -> list[Passage]:
    """Group sentences into passages following the rules in the module docstring."""
    groups: list[list[Sentence]] = []
    current: list[Sentence] = []
    current_words = 0

    def flush() -> None:
        nonlocal current, current_words
        if current:
            groups.append(current)
        current, current_words = [], 0

    for sentence in sentences:
        if current and current_words + sentence.words > config.max_words:
            flush()
        current.append(sentence)
        current_words += sentence.words
        reached_target = len(current) >= config.min_sentences and current_words >= config.min_words
        if (
            reached_target
            or len(current) >= config.max_sentences
            or current_words >= config.max_words
        ):
            flush()
    flush()

    # Merge a fragment left at the end (fewer sentences than the minimum and under half the
    # minimum words) into the previous passage, if the result stays within max_words.
    if len(groups) >= 2:
        tail, previous = groups[-1], groups[-2]
        tail_words = sum(sentence.words for sentence in tail)
        previous_words = sum(sentence.words for sentence in previous)
        is_fragment = len(tail) < config.min_sentences and tail_words < config.min_words / 2
        if is_fragment and previous_words + tail_words <= config.max_words:
            previous.extend(groups.pop())

    return [
        Passage(position=index, page_number=group[0].page_number, sentences=group)
        for index, group in enumerate(groups)
    ]
