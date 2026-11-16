"""Readable forms of topic keywords: "problem solve" → "problem solving".

Topic keywords are lemmas of the normalised text (TF-IDF branch), so they read oddly
("problem solve", "distribute system"). While the extracts are lemmatised again, this records
for every lemma sequence of one to three words (the same sequences the topic vectoriser sees)
how it was actually written, and shows the most frequent written form.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable

from spacy.language import Language
from spacy.tokens import Doc

from app.services.preprocessing.normalise import StopWords, keep_lemma

MAX_WORDS = 3


class SurfaceForms:
    """Lemma phrase → most common written (lowercase) form, learnt from spaCy documents."""

    def __init__(self, stop_words: StopWords | None = None) -> None:
        self.stop_words = stop_words or StopWords.build()
        self._counts: dict[str, Counter[str]] = defaultdict(Counter)

    def add(self, doc: Doc) -> None:
        kept = [
            (lemma, token.lower_)
            for token in doc
            if (lemma := keep_lemma(token, self.stop_words)) is not None
        ]
        for size in range(1, MAX_WORDS + 1):
            for start in range(len(kept) - size + 1):
                window = kept[start : start + size]
                key = " ".join(lemma for lemma, _ in window)
                self._counts[key][" ".join(word for _, word in window)] += 1

    def learn(self, nlp: Language, texts: Iterable[str]) -> SurfaceForms:
        """Lemmatise ``texts`` (tagger and lemmatiser only) and record their written forms."""
        disabled = [name for name in ("parser", "ner") if name in nlp.pipe_names]
        for doc in nlp.pipe(texts, batch_size=64, disable=disabled):
            self.add(doc)
        return self

    def form(self, term: str) -> str:
        """The most common written form of ``term``, word by word when the phrase is unseen."""
        counts = self._counts.get(term)
        if counts:
            return counts.most_common(1)[0][0]
        if " " not in term:
            return term
        return " ".join(self.form(word) for word in term.split())
