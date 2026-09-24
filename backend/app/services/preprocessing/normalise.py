"""Heavy normalisation for TF-IDF only.

The other branch of preprocessing (light cleaning) keeps the original text. Here each passage
becomes a lowercase string of lemmas with standard English stop words, custom domain stop words,
punctuation and numbers removed, e.g.

    "Candidates must have 3+ years' experience building REST APIs in Python."
    → "build rest api python"
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from spacy.lang.en.stop_words import STOP_WORDS
from spacy.tokens import Span, Token

MIN_TOKEN_LENGTH = 2


@dataclass(frozen=True)
class StopWords:
    """Standard + custom stop words. Multi-word entries ("port harcourt") are phrases."""

    words: frozenset[str]
    phrases: tuple[str, ...]

    @classmethod
    def build(cls, custom: Iterable[str] = ()) -> StopWords:
        single: set[str] = set(STOP_WORDS)
        phrases: list[str] = []
        for entry in custom:
            cleaned = " ".join(entry.lower().replace("-", " ").split())
            if not cleaned:
                continue
            if " " in cleaned:
                phrases.append(cleaned)
            else:
                single.add(cleaned)
        # Longest phrases first so "akwa ibom state" wins over "akwa ibom".
        return cls(frozenset(single), tuple(sorted(phrases, key=len, reverse=True)))


def _keep(token: Token, stop_words: StopWords) -> str | None:
    """The lowercase lemma of a meaningful token, or None to drop it.

    spaCy's ``like_url`` is deliberately not used: it flags technology names such as
    "Node.js", and real URLs/emails were already removed during light cleaning.
    """
    if token.is_space or token.is_punct or token.like_num:
        return None
    if not any(char.isalpha() for char in token.text):
        return None
    lemma = token.lemma_.lower().strip()
    if len(lemma) < MIN_TOKEN_LENGTH:
        return None
    if token.is_stop or lemma in stop_words.words or token.lower_ in stop_words.words:
        return None
    return lemma


def normalise_spans(spans: Iterable[Span], stop_words: StopWords) -> str:
    """Normalised text for a passage made of the given spaCy sentence spans."""
    lemmas = [
        lemma for span in spans for token in span if (lemma := _keep(token, stop_words)) is not None
    ]
    text = " ".join(lemmas)
    for phrase in stop_words.phrases:
        text = re.sub(rf"(?<!\S){re.escape(phrase)}(?!\S)", " ", text)
    return " ".join(text.split())
