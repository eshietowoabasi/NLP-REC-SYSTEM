"""Preprocessing pipeline (spec §8.1).

Produces two views of each document:
- ``sentences``: normalised, original-case sentences for SBERT embeddings and NER;
- ``tokens``: lowercased lemmas with stop words, punctuation and numbers removed, for TF-IDF.
"""
from dataclasses import dataclass
from functools import lru_cache

from .normalize import clean_blocks, split_blocks

DEFAULT_SPACY_MODEL = "en_core_web_sm"
_MAX_CHUNK_CHARS = 100_000  # stay well under spaCy's nlp.max_length
# Content-word parts of speech kept for TF-IDF; drops modals ("shall"), determiners, etc.
# X covers unknown tokens, which often are tool/technology names.
_CONTENT_POS = {"NOUN", "PROPN", "VERB", "ADJ", "X"}


@dataclass
class PreprocessedDocument:
    clean_text: str
    sentences: list[str]
    tokens: list[str]

    @property
    def sentence_count(self) -> int:
        return len(self.sentences)

    @property
    def token_count(self) -> int:
        return len(self.tokens)


@lru_cache(maxsize=2)
def load_nlp(model_name: str = DEFAULT_SPACY_MODEL):
    import spacy

    # NER runs later as its own stage; the statistical parser is swapped for the
    # much faster rule-trained sentence recogniser.
    nlp = spacy.load(model_name, disable=["parser", "ner"])
    if "senter" in nlp.disabled:
        nlp.enable_pipe("senter")
    elif not nlp.has_pipe("senter"):
        nlp.add_pipe("sentencizer")
    return nlp


def _chunks(blocks):
    for block in blocks:
        if len(block) <= _MAX_CHUNK_CHARS:
            yield block
            continue
        for start in range(0, len(block), _MAX_CHUNK_CHARS):
            yield block[start:start + _MAX_CHUNK_CHARS]


def _keep_token(tok, stop_words) -> bool:
    if tok.pos_ not in _CONTENT_POS:
        return False
    if tok.is_stop or tok.is_punct or tok.is_space or tok.like_num or tok.like_url or tok.like_email:
        return False
    lemma = tok.lemma_.lower()
    return len(lemma) >= 2 and any(ch.isalpha() for ch in lemma) and lemma not in stop_words  # e.g. "be" from "is"


def preprocess(text_or_blocks, model_name: str = DEFAULT_SPACY_MODEL) -> PreprocessedDocument:
    blocks = split_blocks(text_or_blocks) if isinstance(text_or_blocks, str) else list(text_or_blocks)
    blocks = clean_blocks(blocks)
    nlp = load_nlp(model_name)

    stop_words = nlp.Defaults.stop_words
    sentences, tokens = [], []
    for doc in nlp.pipe(_chunks(blocks), batch_size=64):
        for sent in doc.sents:
            sentence = sent.text.strip()
            if sentence:
                sentences.append(sentence)
        tokens.extend(tok.lemma_.lower() for tok in doc if _keep_token(tok, stop_words))

    return PreprocessedDocument(clean_text="\n\n".join(blocks), sentences=sentences, tokens=tokens)
