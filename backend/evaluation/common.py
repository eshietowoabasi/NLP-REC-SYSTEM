"""Shared helpers for the evaluation scripts: load a completed session and write outputs.

The scripts run against the database configured in ``.env`` (the development database holds
the real corpus). They never change it: sessions are re-analysed in memory when a script needs
data that is not stored (theme members and centres, course similarities).
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from flask import Flask
from numpy.typing import NDArray
from sqlalchemy import select

from app import create_app
from app.extensions import db
from app.models import AnalysisSession, NLPResult, NLPResultType
from app.services.analysis import AnalysisOutput, CoreCourse, CorpusPassage, run_analysis
from app.services.ingestion.courses import CourseExclusions
from app.services.ner.skills import build_skill_pipeline, canonical_lookup
from app.services.preprocessing.spacy_model import get_nlp
from app.settings import get_setting
from app.tasks.analysis import (
    load_core,
    load_corpus,
    load_courses,
    load_parameters,
    load_skill_patterns,
)

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def app_context() -> Any:
    """An application context for the configured (development) database."""
    app: Flask = create_app("development")
    return app.app_context()


def stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def results_path(name: str) -> Path:
    """A file in ``evaluation/results`` (git-ignored: it may contain corpus text)."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return RESULTS_DIR / name


def write_json(path: Path, data: Any) -> Path:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path


def write_csv(path: Path, header: Sequence[str], rows: Iterable[Sequence[Any]]) -> Path:
    # utf-8-sig so that Excel opens accented text correctly; the scripts read it back the same.
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    return path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def completed_session(session_id: int) -> AnalysisSession:
    session = db.session.get(AnalysisSession, session_id)
    if session is None:
        raise SystemExit(f"Session {session_id} does not exist.")
    if session.status.value != "completed":
        raise SystemExit(f"Session {session_id} has not completed (status: {session.status}).")
    return session


def stored_result(session_id: int, result_type: NLPResultType) -> dict[str, Any]:
    payload = db.session.scalar(
        select(NLPResult.payload).where(
            NLPResult.session_id == session_id, NLPResult.result_type == result_type
        )
    )
    return payload or {}


@dataclass
class Reanalysis:
    """A session analysed again in memory, with what the stored results do not keep."""

    session: AnalysisSession
    corpus: list[CorpusPassage]
    courses: list[CoreCourse]
    output: AnalysisOutput
    centres: dict[int, NDArray[np.float32]]  # topic id → L2-normalised theme centre


def reanalyse(session_id: int) -> Reanalysis:
    """Run the session's analysis again (same documents, parameters and random seed).

    BERTopic with a fixed ``random_state`` reproduces the stored themes on the same machine;
    the scripts check that the theme titles match the stored ones.
    """
    session = completed_session(session_id)
    parameters = load_parameters(session.parameter_config or {})
    core_document_id = session.nuc_core_version.document_id
    corpus = load_corpus(session)
    core = load_core(core_document_id)
    courses, _ = load_courses(
        core_document_id, CourseExclusions.from_setting(get_setting("nuc_course_exclusions"))
    )
    specs = load_skill_patterns()
    model_name = (session.parameter_config or {}).get("spacy_model", "en_core_web_sm")
    output = run_analysis(
        corpus,
        core,
        parameters,
        build_skill_pipeline(model_name, specs),
        canonical_lookup(specs, get_nlp(model_name)),
        courses=courses,
    )
    embeddings = {p.id: p.embedding for p in corpus}
    centres = {}
    for candidate in output.candidates:
        mean = np.mean([embeddings[pid] for pid in candidate.member_passage_ids], axis=0)
        centres[candidate.topic_id] = mean / (np.linalg.norm(mean) or 1.0)
    stored_topics = stored_result(session_id, NLPResultType.TOPICS).get("topics", [])
    stored = {t["topic_id"]: t["title"] for t in stored_topics}
    mismatched = [c.topic_id for c in output.candidates if stored.get(c.topic_id) != c.auto_title]
    if mismatched:
        print(
            f"Warning: {len(mismatched)} theme(s) differ from the stored session "
            "(different machine or settings); the evaluation uses the re-analysed themes."
        )
    return Reanalysis(session, corpus, courses, output, centres)
