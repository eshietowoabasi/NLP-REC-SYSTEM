"""TF-IDF keyword extraction (spec §8.2) over preprocessed lemma tokens."""
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


@dataclass
class TfidfResult:
    per_document: list[list[dict]]  # [[{"term", "score"}]] aligned with the input order
    corpus: list[dict]              # [{"term", "score", "document_frequency"}]


def _identity(tokens):
    return tokens


def extract_keywords(token_lists: list[list[str]], top_n: int = 25, corpus_top_n: int = 50,
                     ngram_range=(1, 2)) -> TfidfResult:
    """Score terms per document; the corpus list averages scores across documents.

    With several documents, terms appearing in more than 90% of them are dropped so
    boilerplate shared by every source does not surface as a keyword.
    """
    non_empty = [i for i, tokens in enumerate(token_lists) if tokens]
    per_document = [[] for _ in token_lists]
    if not non_empty:
        return TfidfResult(per_document, [])

    vectorizer = TfidfVectorizer(
        analyzer="word",
        tokenizer=_identity,
        preprocessor=_identity,
        token_pattern=None,
        lowercase=False,
        ngram_range=ngram_range,
        sublinear_tf=True,
        max_df=0.9 if len(non_empty) >= 5 else 1.0,
    )
    matrix = vectorizer.fit_transform([token_lists[i] for i in non_empty])
    terms = vectorizer.get_feature_names_out()

    for row, index in enumerate(non_empty):
        scores = matrix.getrow(row).toarray().ravel()
        top = np.argsort(-scores, kind="stable")[:top_n]
        per_document[index] = [
            {"term": terms[j], "score": round(float(scores[j]), 4)} for j in top if scores[j] > 0
        ]

    mean_scores = np.asarray(matrix.mean(axis=0)).ravel()
    doc_freq = np.asarray((matrix > 0).sum(axis=0)).ravel()
    top = np.argsort(-mean_scores, kind="stable")[:corpus_top_n]
    corpus = [
        {"term": terms[j], "score": round(float(mean_scores[j]), 4), "document_frequency": int(doc_freq[j])}
        for j in top if mean_scores[j] > 0
    ]
    return TfidfResult(per_document, corpus)
