"""Semantic overlap detection against the NUC 70% core (spec §9).

Core Reference documents are split into short segments (course titles, outlines,
sentences) and embedded. Each candidate's embedding is compared with every segment;
the maximum cosine similarity decides the overlap status and gives novelty:

    novelty = 1 - max_similarity
    overlap_status = "Potential Duplicate" if max_similarity > threshold
"""
import re
from collections import OrderedDict
from dataclasses import dataclass

import numpy as np

from ...models import OverlapStatus
from ..preprocessing.normalize import clean_blocks, split_blocks

MIN_SEGMENT_WORDS = 3     # keeps course titles such as "Cloud Computing Systems"
MAX_SEGMENT_WORDS = 60    # longer blocks are split into sentence windows
TOP_MATCHES = 3
_SENTENCE_END_RE = re.compile(r"(?<=[.!?;])\s+")
_CACHE_SIZE = 32


@dataclass
class CoreSegment:
    text: str
    document_id: int


@dataclass
class CoreIndex:
    segments: list[CoreSegment]
    vectors: np.ndarray
    document_ids: list[int]

    def __len__(self):
        return len(self.segments)


@dataclass
class OverlapResult:
    max_similarity: float
    novelty: float
    status: OverlapStatus
    matches: list[dict]  # [{"text", "document_id", "similarity"}], best first


def segment_core_text(text: str) -> list[str]:
    segments = []
    for block in clean_blocks(split_blocks(text)):
        words = block.split()
        if len(words) < MIN_SEGMENT_WORDS:
            continue
        if len(words) <= MAX_SEGMENT_WORDS:
            segments.append(block)
            continue
        window = []
        for sentence in _SENTENCE_END_RE.split(block):
            if window and len(" ".join(window + [sentence]).split()) > MAX_SEGMENT_WORDS:
                segments.append(" ".join(window))
                window = []
            window.append(sentence)
        if window:
            segments.append(" ".join(window))
    # Preserve order, drop exact repeats (running headers that survived cleanup etc.).
    return list(dict.fromkeys(s for s in segments if len(s.split()) >= MIN_SEGMENT_WORDS))


# Core documents rarely change and can be large (the CCMAS runs to hundreds of pages),
# so their segment embeddings are cached per worker process.
_cache: "OrderedDict[tuple, tuple[list[str], np.ndarray]]" = OrderedDict()


def _embed_document(document_id, content_key, text, embedder):
    key = (document_id, content_key, embedder.backend, embedder.model_name)
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    segments = segment_core_text(text)
    vectors = embedder.encode(segments)
    _cache[key] = (segments, vectors)
    if len(_cache) > _CACHE_SIZE:
        _cache.popitem(last=False)
    return segments, vectors


def clear_cache():
    _cache.clear()


def build_core_index(documents, embedder) -> CoreIndex:
    """``documents``: iterable of (document_id, content_key, text); content_key is e.g. a SHA-256."""
    segments, vectors, doc_ids = [], [], []
    for document_id, content_key, text in documents:
        texts, vecs = _embed_document(document_id, content_key, text, embedder)
        if not texts:
            continue
        segments.extend(CoreSegment(t, document_id) for t in texts)
        vectors.append(vecs)
        doc_ids.append(document_id)
    matrix = np.vstack(vectors).astype(np.float32) if vectors else np.zeros((0, 1), dtype=np.float32)
    return CoreIndex(segments, matrix, doc_ids)


def detect_overlap(candidate_vectors: np.ndarray, index: CoreIndex, threshold: float) -> list[OverlapResult]:
    """Compare L2-normalised candidate vectors with the core index (dot product = cosine)."""
    if len(index) == 0:
        raise ValueError("The core reference index is empty")
    candidate_vectors = np.asarray(candidate_vectors, dtype=np.float32)
    if candidate_vectors.size == 0:
        return []
    similarities = np.clip(candidate_vectors @ index.vectors.T, -1.0, 1.0)
    results = []
    for row in similarities:
        best = np.argsort(-row, kind="stable")[:TOP_MATCHES]
        # Rounded before comparing so float32 noise (0.8000000119) cannot cross the
        # threshold, and the reported value always agrees with the status.
        max_similarity = round(max(float(row[best[0]]), 0.0), 4)  # negative cosine = unrelated
        results.append(OverlapResult(
            max_similarity=max_similarity,
            novelty=round(1.0 - max_similarity, 4),
            status=OverlapStatus.POTENTIAL_DUPLICATE if max_similarity > threshold else OverlapStatus.NO_SIGNIFICANT_OVERLAP,
            matches=[
                {"text": index.segments[i].text, "document_id": index.segments[i].document_id,
                 "similarity": round(float(row[i]), 4)}
                for i in best
            ],
        ))
    return results
