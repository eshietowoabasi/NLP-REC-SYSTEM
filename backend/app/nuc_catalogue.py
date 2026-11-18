"""Load NUC core documents for many programmes at once (the ``load-nuc-cores`` command).

A CCMAS document covers a whole discipline (the Engineering and Technology CCMAS has 34
programmes on 1,332 pages). Each programme is compared with its own section only, so the
documents are first cut into one PDF per programme, listed in an ``_index.json`` beside them::

    [{"programme": "Chemical Engineering", "nuc_discipline": "engineering_and_technology",
      "discipline": "Engineering and Technology", "degree": "B.Eng.",
      "file": "Engineering and Technology - Chemical Engineering (CCMAS 2023).pdf",
      "pages": [198, 231], "job_titles": ["chemical engineer", "process engineer"]}, ...]

:func:`load_catalogue` creates any programme that does not exist yet (matched by name,
ignoring case), fills in its discipline and starter job titles when they are empty, stores the
section as a new NUC core version and queues it for processing. A programme whose active NUC
core already has this version label, or one still being processed, is skipped, so the command
can be run again safely.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from werkzeug.datastructures import FileStorage

from app.audit import AuditAction, record_audit
from app.extensions import db
from app.models import (
    Document,
    DocumentStatus,
    NucCoreVersion,
    NucDiscipline,
    Programme,
    SourceCategory,
    User,
    UserRole,
)
from app.tasks.queue import enqueue
from app.uploads import UploadRejectedError, discard, store_upload

STOP_WORDS = {"and", "of", "the", "in", "for"}

#: The programme sections shipped with SkillBridge (cut from the NUC CCMAS 2023 documents of
#: Computing, Engineering and Technology, and Allied Health Sciences).
BUNDLED_CATALOGUE = Path(__file__).resolve().parents[1] / "nuc_catalogue"


@dataclass
class LoadSummary:
    """What :func:`load_catalogue` did, programme by programme."""

    created: list[str] = field(default_factory=list)
    queued: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


def programme_code(name: str, taken: set[str]) -> str:
    """A short unique code from a programme name: "Chemical Engineering" → "CHE"."""
    words = [w for w in re.findall(r"[A-Za-z]+", name) if w.lower() not in STOP_WORDS]
    if not words:
        words = ["PRG"]
    if len(words) == 1:
        base = words[0][:3].upper()
    elif words[-1].lower() == "engineering":
        base = (words[0][:2] + "E").upper() if len(words) == 2 else "".join(w[0] for w in words)
    else:
        base = "".join(w[0] for w in words)[:4].upper()
    base = base.upper()
    code, n = base, 2
    while code in taken:
        code, n = f"{base}{n}", n + 1
    taken.add(code)
    return code


def _find_programme(name: str) -> Programme | None:
    return db.session.scalar(select(Programme).where(func.lower(Programme.name) == name.lower()))


def _busy_or_loaded(programme: Programme, label: str) -> str | None:
    """Why this programme needs no new upload, or None."""
    rows = db.session.execute(
        select(NucCoreVersion, Document)
        .join(Document, Document.id == NucCoreVersion.document_id)
        .where(NucCoreVersion.programme_id == programme.id)
    ).all()
    for version, document in rows:
        if version.is_active and version.version_label == label:
            return "already has this NUC core"
        if document.processing_status in (DocumentStatus.UPLOADED, DocumentStatus.PROCESSING):
            return "a NUC core is still being processed"
    return None


def _new_programme(entry: dict[str, Any], taken: set[str]) -> Programme:
    name = str(entry["programme"]).strip()
    return Programme(
        name=name,
        discipline_code=programme_code(name, taken),
        nuc_discipline=NucDiscipline(entry["nuc_discipline"]),
        job_search_terms=list(entry.get("job_titles") or []),
        job_field_slugs=[],
        description=f"{entry.get('degree', '')} {name}, NUC CCMAS ({entry['discipline']}).".strip(),
    )


def ensure_catalogue_programmes(folder: Path = BUNDLED_CATALOGUE) -> list[str]:
    """Create every catalogue programme that does not exist yet (no NUC core, just the
    programme), so people can choose it when they sign up. Commits; returns the names added."""
    index = folder / "_index.json"
    if not index.exists():
        return []
    entries: list[dict[str, Any]] = json.loads(index.read_text("utf-8"))
    existing = {name.lower() for name in db.session.scalars(select(Programme.name))}
    missing = [e for e in entries if str(e["programme"]).strip().lower() not in existing]
    if not missing:
        return []
    admin_id = db.session.scalar(
        select(User.id)
        .where(User.role == UserRole.ADMIN, User.is_active.is_(True))
        .order_by(User.id)
    )
    taken = {code for code in db.session.scalars(select(Programme.discipline_code)) if code}
    created: list[str] = []
    for entry in missing:
        programme = _new_programme(entry, taken)
        db.session.add(programme)
        db.session.flush()
        record_audit(
            AuditAction.PROGRAMME_CREATED,
            "programme",
            programme.id,
            {"name": programme.name, "source": "nuc-catalogue"},
            user_id=admin_id,
        )
        created.append(programme.name)
    db.session.commit()
    return created


def load_catalogue(
    folder: Path,
    *,
    version_label: str = "CCMAS 2023",
    only: list[str] | None = None,
    report: Callable[[str], None] = lambda _message: None,
) -> LoadSummary:
    """Load every programme section listed in ``folder/_index.json`` (see the module docs).

    ``only`` limits the run to programmes whose name contains one of the given words.
    Each programme is committed on its own, so one bad file does not stop the others.
    """
    entries: list[dict[str, Any]] = json.loads((folder / "_index.json").read_text("utf-8"))
    admin = db.session.scalar(
        select(User).where(User.role == UserRole.ADMIN, User.is_active.is_(True)).order_by(User.id)
    )
    if admin is None:
        raise RuntimeError("No active admin exists. Run `flask --app wsgi seed` first.")
    taken = {code for code in db.session.scalars(select(Programme.discipline_code)) if code}
    summary = LoadSummary()

    for entry in entries:
        name = str(entry["programme"]).strip()
        if only and not any(word.lower() in name.lower() for word in only):
            continue
        programme = _find_programme(name)
        if programme is None:
            programme = _new_programme(entry, taken)
            db.session.add(programme)
            db.session.flush()
            record_audit(
                AuditAction.PROGRAMME_CREATED,
                "programme",
                programme.id,
                {"name": name, "source": "load-nuc-cores"},
                user_id=admin.id,
            )
            summary.created.append(name)
        else:
            if programme.nuc_discipline is None:
                programme.nuc_discipline = NucDiscipline(entry["nuc_discipline"])
            if not programme.job_search_terms:
                programme.job_search_terms = list(entry.get("job_titles") or [])

        reason = _busy_or_loaded(programme, version_label)
        if reason:
            db.session.commit()
            summary.skipped.append(f"{name}: {reason}")
            report(f"skip   {name} ({reason})")
            continue

        path = folder / entry["file"]
        document: Document | None = None
        try:
            with path.open("rb") as handle:
                upload = FileStorage(stream=handle, filename=path.name)
                document = store_upload(upload, SourceCategory.NUC_CORE, admin, programme.id)
            document.title = f"{name} NUC core ({version_label})"[:255]
            version = NucCoreVersion(
                programme_id=programme.id,
                document_id=document.id,
                version_label=version_label,
                is_active=False,
                uploaded_by_id=admin.id,
            )
            db.session.add(version)
            db.session.flush()
            record_audit(
                AuditAction.NUC_CORE_UPLOADED,
                "nuc_core_version",
                version.id,
                {"version_label": version_label, "filename": path.name, "programme": name},
                user_id=admin.id,
            )
            db.session.commit()
        except (OSError, UploadRejectedError) as exc:
            db.session.rollback()
            if document is not None:
                discard([document])
            summary.failed.append(f"{name}: {exc}")
            report(f"FAILED {name}: {exc}")
            continue
        enqueue("app.tasks.ingestion.ingest_document", document.id)
        summary.queued.append(name)
        report(f"queued {name}")
    return summary


def catalogue_status(folder: Path = BUNDLED_CATALOGUE) -> dict[str, Any]:
    """How many programmes of the catalogue have an active NUC core, are being set up, or
    are not loaded yet (for the admin Programmes page)."""
    index = folder / "_index.json"
    if not index.exists():
        return {"available": 0, "ready": 0, "processing": 0, "missing": 0}
    entries = json.loads(index.read_text("utf-8"))
    counts = {"ready": 0, "processing": 0, "missing": 0}
    for entry in entries:
        programme = _find_programme(str(entry["programme"]))
        if programme is None:
            counts["missing"] += 1
            continue
        statuses = db.session.execute(
            select(NucCoreVersion.is_active, Document.processing_status)
            .join(Document, Document.id == NucCoreVersion.document_id)
            .where(NucCoreVersion.programme_id == programme.id)
        ).all()
        if any(active for active, _ in statuses):
            counts["ready"] += 1
        elif any(
            status in (DocumentStatus.UPLOADED, DocumentStatus.PROCESSING) for _, status in statuses
        ):
            counts["processing"] += 1
        else:
            counts["missing"] += 1
    return {"available": len(entries), **counts}
