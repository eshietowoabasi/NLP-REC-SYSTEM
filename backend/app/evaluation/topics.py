"""Topic-model evaluation (spec §17.2): BERTopic vs an LDA (Gensim) baseline.

Both models see the same passages (sentences of 6+ words, de-duplicated). Coherence is
C_v over the passages' lemmatised tokens; LDA uses as many topics as BERTopic found,
so the comparison is like for like. Topic diversity is reported alongside coherence
because a model can score high coherence by repeating the same words in every topic.
"""
import time

import numpy as np

from ..services.embeddings import get_embedder
from ..services.preprocessing import preprocess
from ..services.topics import model_topics, select_passages
from .metrics import topic_diversity

TOP_WORDS = 10


def _unigram_words(keywords, vocabulary, n=TOP_WORDS):
    """Split BERTopic's uni/bigram keywords into words known to the coherence dictionary."""
    words = []
    for term in keywords:
        for word in term.split():
            if word in vocabulary and word not in words:
                words.append(word)
    return words[:n]


def evaluate_topics(documents: list[str], embedder=None, lda_passes: int = 10, seed: int = 42) -> dict:
    from gensim.corpora import Dictionary
    from gensim.models import CoherenceModel, LdaModel

    embedder = embedder or get_embedder("hashing")
    passages = []
    for doc_id, text in enumerate(documents):
        passages += select_passages(preprocess(text).sentences, doc_id, "evaluation")
    unique = list({" ".join(p.text.lower().split()): p for p in passages}.values())
    token_lists = [preprocess([p.text]).tokens for p in unique]
    keep = [i for i, tokens in enumerate(token_lists) if len(tokens) >= 2]
    unique = [unique[i] for i in keep]
    token_lists = [token_lists[i] for i in keep]
    if len(unique) < 30:
        raise ValueError(f"Need at least 30 distinct passages for a meaningful comparison; found {len(unique)}")

    dictionary = Dictionary(token_lists)
    vocabulary = set(dictionary.token2id)

    started = time.perf_counter()
    bertopic = model_topics(unique, embedder.encode([p.text for p in unique]))
    bertopic_seconds = time.perf_counter() - started
    bertopic_topics = [
        words for words in (_unigram_words([k["term"] for k in t["keywords"]], vocabulary) for t in bertopic.topics)
        if len(words) >= 2
    ]
    if not bertopic_topics:
        raise ValueError("BERTopic found no topics to evaluate")

    started = time.perf_counter()
    corpus = [dictionary.doc2bow(tokens) for tokens in token_lists]
    lda = LdaModel(corpus=corpus, id2word=dictionary, num_topics=len(bertopic_topics),
                   passes=lda_passes, random_state=seed, alpha="auto", eta="auto")
    lda_seconds = time.perf_counter() - started
    lda_topics = [[w for w, _ in lda.show_topic(t, topn=TOP_WORDS)] for t in range(len(bertopic_topics))]

    def coherence(topics):
        model = CoherenceModel(topics=topics, texts=token_lists, dictionary=dictionary, coherence="c_v", processes=1)
        per_topic = model.get_coherence_per_topic()
        return round(float(np.mean(per_topic)), 4), [round(float(c), 4) for c in per_topic]

    b_mean, b_per = coherence(bertopic_topics)
    l_mean, l_per = coherence(lda_topics)
    warnings = []
    if embedder.backend != "sbert":
        warnings.append(f"Embedding backend '{embedder.backend}' is not SBERT; BERTopic results do not reflect the real system.")
    return {
        "documents": len(documents),
        "passages": len(unique),
        "num_topics": len(bertopic_topics),
        "embedding_backend": embedder.backend,
        "bertopic": {"c_v": b_mean, "diversity": topic_diversity(bertopic_topics), "seconds": round(bertopic_seconds, 2),
                     "outlier_passages": bertopic.outlier_count,
                     "topics": [{"words": w, "c_v": c} for w, c in zip(bertopic_topics, b_per)]},
        "lda": {"c_v": l_mean, "diversity": topic_diversity(lda_topics), "seconds": round(lda_seconds, 2),
                "topics": [{"words": w, "c_v": c} for w, c in zip(lda_topics, l_per)]},
        "better_coherence": "bertopic" if b_mean >= l_mean else "lda",
        "warnings": warnings,
    }
