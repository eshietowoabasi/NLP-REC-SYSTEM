"""Benchmark the analysis pipeline: 20 synthetic documents of ~3,000 words each.

    python -m evaluation.benchmark_pipeline            (from backend/, in the virtualenv)
    python -m evaluation.benchmark_pipeline --documents 20 --words 3000

Target (brief §6.2): a session analysis over 20 documents × ~3,000 words completes in
≤ 60 s on a normal laptop CPU, excluding the first-time model download.

What is timed:
* ingestion of every document (parse → clean → passages → normalised text → SBERT), reported
  separately because it happens once per document at upload time, not per session;
* the session analysis (keywords → skills → embeddings → themes → overlap → scoring), which is
  what the 60 s target applies to.

Model loading (spaCy, SBERT) is done before timing, as in a running worker. The first analysis
in a fresh process includes one-off compilation by UMAP/numba; a second run shows the warm time.
Results are written to ``evaluation/results/benchmark_<timestamp>.json``. All text is synthetic.
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from app.config import BaseConfig  # noqa: F401  (loads .env, e.g. USE_SYSTEM_CERTS)
from app.models.enums import FileType
from app.seed.skill_patterns import iter_skill_patterns
from app.seed.stop_words import DOMAIN_STOP_WORDS
from app.services.analysis import (
    AnalysisParameters,
    CorePassage,
    CorpusPassage,
    run_analysis,
)
from app.services.embeddings.encoder import get_encoder
from app.services.ingestion.passages import PassageConfig
from app.services.ingestion.pipeline import process_document
from app.services.ner.skills import SkillPatternSpec, build_skill_pipeline, canonical_lookup
from app.services.preprocessing.normalise import StopWords
from app.services.preprocessing.spacy_model import get_nlp
from app.services.recommendations.scoring import ScoreWeights
from app.settings import DEFAULT_SETTINGS
from evaluation.synthetic_corpus import make_corpus, make_nuc_core

RESULTS_DIR = Path(__file__).resolve().parent / "results"
TARGET_SECONDS = 60.0
CATEGORIES = ["job_market", "institutional", "policy", "academic"]


def ingest(
    texts: list[str], nlp, stop_words: StopWords, encoder
) -> list[list[tuple[str, str, np.ndarray]]]:
    """Ingest each text; returns (text, normalised_text, embedding) per passage per document."""
    documents = []
    for text in texts:
        output = process_document(FileType.TXT, text.encode(), nlp, stop_words, PassageConfig())
        vectors = encoder.encode([p.text for p in output.passages])
        documents.append(
            [(p.text, p.normalised_text, v) for p, v in zip(output.passages, vectors, strict=True)]
        )
    return documents


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--documents", type=int, default=20)
    parser.add_argument("--words", type=int, default=3000)
    args = parser.parse_args()

    import os

    if os.environ.get("USE_SYSTEM_CERTS", "").lower() == "true":
        from app.utils.tls import use_system_certificates

        use_system_certificates()

    print(
        f"Loading models ({DEFAULT_SETTINGS['spacy_model']}, {DEFAULT_SETTINGS['sbert_model']})..."
    )
    started = time.perf_counter()
    nlp = get_nlp(DEFAULT_SETTINGS["spacy_model"])
    encoder = get_encoder(DEFAULT_SETTINGS["sbert_model"])
    encoder.encode(["warm-up"])
    specs = [
        SkillPatternSpec(label, pattern, name) for label, name, pattern in iter_skill_patterns()
    ]
    skill_nlp = build_skill_pipeline(DEFAULT_SETTINGS["spacy_model"], specs)
    canonical = canonical_lookup(specs, nlp)
    model_load = time.perf_counter() - started
    stop_words = StopWords.build(DOMAIN_STOP_WORDS)

    corpus = make_corpus(args.documents, args.words)
    total_words = sum(len(text.split()) for _, text in corpus)
    print(f"Ingesting {len(corpus)} synthetic documents ({total_words:,} words)...")
    started = time.perf_counter()
    ingested = ingest([text for _, text in corpus], nlp, stop_words, encoder)
    core_ingested = ingest([make_nuc_core(args.words)], nlp, stop_words, encoder)[0]
    ingestion_seconds = time.perf_counter() - started

    passages, next_id = [], 1
    for doc_index, document in enumerate(ingested):
        for text, normalised, vector in document:
            passages.append(
                CorpusPassage(
                    next_id,
                    doc_index + 1,
                    CATEGORIES[doc_index % len(CATEGORIES)],
                    text,
                    normalised,
                    vector,
                )
            )
            next_id += 1
    core = [
        CorePassage(next_id + i, text, vector) for i, (text, _, vector) in enumerate(core_ingested)
    ]
    parameters = AnalysisParameters(
        weights=ScoreWeights.from_dict(DEFAULT_SETTINGS["score_weights"]),
        similarity_threshold=DEFAULT_SETTINGS["similarity_threshold"],
        max_recommendations=DEFAULT_SETTINGS["max_recommendations"],
        min_topic_size=DEFAULT_SETTINGS["min_topic_size"],
        evidence_per_recommendation=DEFAULT_SETTINGS["evidence_per_recommendation"],
    )

    runs = []
    for label in ("first run (fresh process)", "second run (warm)"):
        started = time.perf_counter()
        output = run_analysis(passages, core, parameters, skill_nlp, canonical)
        seconds = time.perf_counter() - started
        runs.append({"label": label, "seconds": round(seconds, 2), "stages": output.stage_timings})
        print(f"Analysis {label}: {seconds:.1f}s  {output.stage_timings}")

    result = {
        "timestamp": datetime.now(UTC).isoformat(),
        "machine": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python": platform.python_version(),
        },
        "documents": len(corpus),
        "words": total_words,
        "passages": len(passages),
        "nuc_core_passages": len(core),
        "model_load_seconds": round(model_load, 2),
        "ingestion_seconds": round(ingestion_seconds, 2),
        "analysis_runs": runs,
        "topics": output.topics["topic_count"],
        "recommendations": len(output.recommendations),
        "top_recommendations": [
            {
                "rank": c.rank,
                "title": c.auto_title,
                "composite": round(c.composite_score, 3),
                "overlap": c.overlap_status.value,
            }
            for c in output.recommendations[:5]
        ],
        "target_seconds": TARGET_SECONDS,
        "meets_target": runs[0]["seconds"] <= TARGET_SECONDS,
    }
    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"benchmark_{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    path.write_text(json.dumps(result, indent=2))

    print(
        f"\n{len(passages)} passages, {result['topics']} themes, "
        f"{result['recommendations']} recommendations."
        f"\nIngestion (once per document): {ingestion_seconds:.1f}s"
        f"\nSession analysis: {runs[0]['seconds']}s first run, {runs[1]['seconds']}s warm"
        f" - target {TARGET_SECONDS:.0f}s: {'MET' if result['meets_target'] else 'NOT MET'}"
        f"\nSaved {path}"
    )


if __name__ == "__main__":
    main()
