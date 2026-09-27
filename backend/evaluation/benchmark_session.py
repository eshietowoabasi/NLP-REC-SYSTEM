"""Benchmark the analysis of a real session (complements the synthetic benchmark_pipeline).

    python -m evaluation.benchmark_session --session 10 [--runs 3]

Loads the session's stored passages and embeddings once (as the worker does), then runs the
analysis ``--runs`` times and reports each stage's time. The first run in a fresh process
includes one-off UMAP/numba compilation ("cold"); later runs are "warm", like a worker that
has already analysed a session. The corpus size and the timings the worker recorded when the
session ran are reported alongside. The database is not changed.
"""

from __future__ import annotations

import argparse
import platform
import statistics
import time

from sqlalchemy import func, select

from evaluation.common import app_context, completed_session, results_path, stamp, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--session", type=int, required=True)
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()

    from app.extensions import db
    from app.models import Document, DocumentSession, Passage
    from app.services.analysis import run_analysis
    from app.services.ingestion.courses import CourseExclusions
    from app.services.ner.skills import build_skill_pipeline, canonical_lookup
    from app.services.preprocessing.spacy_model import get_nlp
    from app.settings import get_setting
    from app.tasks.analysis import (
        load_core,
        load_corpus,
        load_courses,
        load_naming,
        load_parameters,
        load_skill_patterns,
    )

    with app_context():
        session = completed_session(args.session)
        document_ids = select(DocumentSession.document_id).where(
            DocumentSession.session_id == session.id
        )
        words = db.session.scalar(
            select(func.sum(Document.word_count)).where(Document.id.in_(document_ids))
        )
        passages = db.session.scalar(
            select(func.count(Passage.id)).where(Passage.document_id.in_(document_ids))
        )
        recorded = dict(session.stage_timings or {})
        started = time.perf_counter()
        parameters = load_parameters(session.parameter_config or {})
        core_id = session.nuc_core_version.document_id
        corpus = load_corpus(session)
        core = load_core(core_id)
        courses, excluded = load_courses(
            core_id, CourseExclusions.from_setting(get_setting("nuc_course_exclusions"))
        )
        specs = load_skill_patterns()
        model = (session.parameter_config or {}).get("spacy_model", "en_core_web_sm")
        skill_nlp = build_skill_pipeline(model, specs)
        canonical = canonical_lookup(specs, get_nlp(model))
        text_nlp = get_nlp(model)
        naming = load_naming(
            (session.parameter_config or {}).get("sbert_model") or get_setting("sbert_model")
        )
        titles = {link.document.id: link.document.title for link in session.document_links}
        loading = time.perf_counter() - started
        document_count = len(session.document_links)

    runs = []
    for number in range(1, args.runs + 1):
        started = time.perf_counter()
        output = run_analysis(
            corpus,
            core,
            parameters,
            skill_nlp,
            canonical,
            courses=courses,
            text_nlp=text_nlp,
            naming=naming,
            document_titles=titles,
        )
        total = time.perf_counter() - started
        runs.append({"run": number, "seconds": round(total, 2), "stages": output.stage_timings})
        print(f"run {number}: {total:.1f} s  {output.stage_timings}")

    warm = [r["seconds"] for r in runs[1:]] or [runs[0]["seconds"]]
    result = {
        "session": args.session,
        "documents": document_count,
        "words": words,
        "passages": passages,
        "courses_compared": len(courses),
        "courses_excluded": excluded,
        "loading_seconds": round(loading, 2),
        "cold_seconds": runs[0]["seconds"],
        "warm_seconds_median": round(statistics.median(warm), 2),
        "runs": runs,
        "recorded_by_worker": recorded,
        "machine": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python": platform.python_version(),
        },
    }
    out = write_json(results_path(f"benchmark_session{args.session}_{stamp()}.json"), result)
    print(
        f"{document_count} documents, {words:,} words, {passages} passages\n"
        f"Cold {result['cold_seconds']} s, warm median {result['warm_seconds_median']} s "
        f"(loading {result['loading_seconds']} s)\nSaved → {out}"
    )


if __name__ == "__main__":
    main()
