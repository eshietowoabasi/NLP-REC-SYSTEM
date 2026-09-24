"""BERTopic topic modelling over sentence-level passages (spec §8.5, §8.6).

Topic modelling runs on passages (sentences) rather than whole documents: a session
has at most 50 documents, far too few to cluster, but thousands of passages.
Embeddings are computed by our own backend and passed in, so BERTopic never
downloads a model itself.
"""
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer

MIN_PASSAGES = 30
MIN_PASSAGE_WORDS = 6
REPRESENTATIVE_PASSAGES = 3
TOPIC_KEYWORDS = 10
# Words common in formal documents that carry no topical meaning.
EXTRA_STOP_WORDS = {"shall", "will", "must", "may", "also", "including", "etc", "ensure", "within", "upon"}


@dataclass
class Passage:
    text: str
    document_id: int
    source_category: str


@dataclass
class TopicModelResult:
    topics: list[dict]
    document_topics: dict[int, list[dict]]  # document_id -> [{"topic_id", "passages", "share"}]
    passage_count: int
    outlier_count: int
    method: str
    warnings: list[str] = field(default_factory=list)
    assignments: list[int] = field(default_factory=list)  # topic id per input passage (-1 = outlier)


def select_passages(sentences: list[str], document_id: int, source_category: str) -> list[Passage]:
    return [
        Passage(s, document_id, source_category)
        for s in sentences
        if len(s.split()) >= MIN_PASSAGE_WORDS
    ]


_WORD_RE = re.compile(r"\w+")


def surface_forms(texts: list[str]) -> dict[str, str]:
    """Most common original spelling of each lowercase word ("cissp" -> "CISSP")."""
    counts = defaultdict(Counter)
    for text in texts:
        for word in _WORD_RE.findall(text):
            counts[word.lower()][word] += 1
    return {lower: forms.most_common(1)[0][0] for lower, forms in counts.items()}


def _display(term: str, forms: dict[str, str]) -> str:
    words = []
    for word in term.split():
        original = forms.get(word, word)
        words.append(original if original != original.lower() else original.capitalize())
    return " ".join(words)


def make_label(keywords: list[str], n_terms: int = 3, forms: dict[str, str] | None = None) -> str:
    """Readable title from top c-TF-IDF terms, skipping terms contained in ones already used.

    Words keep their source spelling where it has capitals (CISSP, PyTorch); others are
    capitalised. Planners can rename topics when reviewing recommendations.
    """
    chosen = []
    for term in keywords:
        if any(term in c or c in term for c in chosen):
            continue
        chosen.append(term)
        if len(chosen) == n_terms:
            break
    return ", ".join(_display(t, forms or {}) for t in chosen) or "Untitled topic"


def _vectorizer(max_df=1.0):
    # BERTopic fits this on one concatenated document *per topic*, so min_df/max_df count
    # topics, not passages. min_df must stay 1 or topic-specific terms are discarded.
    return CountVectorizer(
        stop_words=sorted(ENGLISH_STOP_WORDS | EXTRA_STOP_WORDS),
        ngram_range=(1, 2),
        min_df=1,
        max_df=max_df,
    )


def _build_model(n_passages: int):
    from bertopic import BERTopic
    from bertopic.vectorizers import ClassTfidfTransformer
    from hdbscan import HDBSCAN
    from umap import UMAP

    umap_model = UMAP(
        n_neighbors=min(15, n_passages - 1),
        n_components=min(5, n_passages - 2),
        min_dist=0.0,
        metric="cosine",
        random_state=42,  # reproducible topics across runs (this forces single-threaded UMAP)
        # 200 epochs instead of 500: ~7x faster on 4,500 passages with identical clusters
        # in our benchmark (ARI 1.0), keeping the run inside the 60 s target (spec §17.5).
        n_epochs=200,
    )
    hdbscan_model = HDBSCAN(
        min_cluster_size=max(5, round(n_passages * 0.01)),
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
    )
    return BERTopic(
        embedding_model=None,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=_vectorizer(),
        ctfidf_model=ClassTfidfTransformer(bm25_weighting=True, reduce_frequent_words=True),
        top_n_words=TOPIC_KEYWORDS,
        calculate_probabilities=False,
        verbose=False,
    )


def _deduplicate(passages: list[Passage]):
    """Map each passage to the first occurrence of its (normalised) text.

    Boilerplate repeated across job adverts would otherwise form artificial clusters,
    and exact duplicate points make UMAP's nearest-neighbour search very slow.
    """
    first_index, mapping = {}, []
    for i, passage in enumerate(passages):
        key = " ".join(passage.text.lower().split())
        mapping.append(first_index.setdefault(key, i))
    unique = sorted(set(mapping))
    position = {idx: pos for pos, idx in enumerate(unique)}
    return unique, np.array([position[m] for m in mapping])


def model_topics(passages: list[Passage], embeddings: np.ndarray) -> TopicModelResult:
    n = len(passages)
    unique, to_unique = _deduplicate(passages) if passages else ([], np.array([], dtype=int))
    if len(unique) < MIN_PASSAGES:
        return TopicModelResult(
            [], {}, n, 0, "skipped",
            [f"Topic modelling needs at least {MIN_PASSAGES} distinct passages of {MIN_PASSAGE_WORDS}+ words; "
             f"found {len(unique)}."],
        )

    # Fit on distinct passages, then give every passage its text's topic so sizes and
    # per-document counts still reflect how often something is said.
    texts = [passages[i].text for i in unique]
    model = _build_model(len(unique))
    unique_assignments, _ = model.fit_transform(texts, embeddings=embeddings[unique])
    unique_assignments = np.asarray(unique_assignments)
    assignments = unique_assignments[to_unique]

    topic_ids = sorted(t for t in set(unique_assignments.tolist()) if t != -1)
    if len(topic_ids) >= 3:
        # Drop terms shared by most topics (boilerplate such as "company", "work").
        from bertopic.vectorizers import ClassTfidfTransformer

        try:
            model.update_topics(
                texts,
                vectorizer_model=_vectorizer(max_df=0.8),
                ctfidf_model=ClassTfidfTransformer(bm25_weighting=True, reduce_frequent_words=True),
                top_n_words=TOPIC_KEYWORDS,
            )
        except ValueError:
            pass  # every term is shared; keep the original representation
    outliers = int((assignments == -1).sum())
    warnings = []
    if not topic_ids:
        warnings.append("No coherent topics were found; every passage was classed as an outlier.")

    sizes = {t: int((assignments == t).sum()) for t in topic_ids}
    max_size = max(sizes.values(), default=1)
    topics = []
    for t in topic_ids:
        members = np.flatnonzero(assignments == t)
        distinct = np.array(unique)[unique_assignments == t]  # one index per distinct text
        centroid = embeddings[distinct].mean(axis=0)
        centroid /= np.linalg.norm(centroid) or 1.0
        closest = distinct[np.argsort(-(embeddings[distinct] @ centroid))[:REPRESENTATIVE_PASSAGES]]
        words = [(w, s) for w, s in (model.get_topic(t) or []) if w]
        forms = surface_forms([passages[i].text for i in members])
        topics.append({
            "topic_id": int(t),
            "label": make_label([w for w, _ in words], forms=forms),
            "keywords": [{"term": w, "score": round(float(s), 4)} for w, s in words],
            "size": sizes[t],
            "distinct_passages": int(len(distinct)),
            # Prevalence normalised to 0-1 against the largest topic (spec §8.6).
            "relevance": round(sizes[t] / max_size, 4),
            "representative_passages": [
                {"text": passages[i].text, "document_id": passages[i].document_id} for i in closest
            ],
            # A list, not a dict: JSON storage would turn integer document ids into strings.
            "document_counts": [
                {"document_id": doc_id, "passages": count}
                for doc_id, count in Counter(passages[i].document_id for i in members).most_common()
            ],
            "source_category_counts": dict(Counter(passages[i].source_category for i in members)),
            "embedding": [round(float(x), 6) for x in centroid],
        })
    topics.sort(key=lambda tp: -tp["size"])

    per_doc_total = Counter(p.document_id for p in passages)
    per_doc_topic = defaultdict(Counter)
    for passage, t in zip(passages, assignments.tolist()):
        if t != -1:
            per_doc_topic[passage.document_id][t] += 1
    document_topics = {
        doc_id: [
            {"topic_id": int(t), "passages": c, "share": round(c / per_doc_total[doc_id], 4)}
            for t, c in counts.most_common()
        ]
        for doc_id, counts in per_doc_topic.items()
    }
    return TopicModelResult(topics, document_topics, n, outliers, "bertopic", warnings, assignments.tolist())
