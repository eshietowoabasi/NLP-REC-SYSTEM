"""Loading NUC cores for many programmes at once (synthetic CCMAS sections)."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select

from app.extensions import db
from app.models import NucCoreVersion, NucDiscipline, Programme
from app.nuc_catalogue import load_catalogue, programme_code
from tests.documents import make_pdf

COURSES = (
    "GST 111 Communication in English 2 C. "
    "NSC 201 Foundations of Nursing Practice 3 C. "
    "NSC 305 Community Health Nursing 3 C. "
    "Students learn patient assessment, care planning and infection prevention in wards. "
)


def write_catalogue(folder: Path, names: list[str]) -> None:
    entries = []
    for name in names:
        file = f"Synthetic - {name}.pdf"
        (folder / file).write_bytes(make_pdf([f"{name} {COURSES} " * 6, COURSES * 6]))
        entries.append(
            {
                "programme": name,
                "nuc_discipline": "allied_health_sciences",
                "discipline": "Allied Health Sciences",
                "degree": "B.Sc.",
                "file": file,
                "pages": [1, 2],
                "job_titles": ["synthetic nurse"],
            }
        )
    (folder / "_index.json").write_text(json.dumps(entries), "utf-8")


def test_codes_are_short_and_unique() -> None:
    taken = {"CHE"}
    assert programme_code("Chemical Engineering", taken) == "CHE2"
    assert programme_code("Electrical and Electronic Engineering", taken) == "EEE"
    assert programme_code("Nursing Science", taken) == "NS"
    assert programme_code("Pharmacology", taken) == "PHA"


def test_loads_programmes_and_their_nuc_cores_once(app, make_user, tmp_path: Path) -> None:
    make_user("admin", username="catalogue-admin")
    write_catalogue(tmp_path, ["Synthetic Nursing Science", "Synthetic Radiography"])

    first = load_catalogue(tmp_path)

    assert sorted(first.created) == ["Synthetic Nursing Science", "Synthetic Radiography"]
    assert sorted(first.queued) == sorted(first.created) and not first.failed
    nursing = db.session.scalar(
        select(Programme).where(Programme.name == "Synthetic Nursing Science")
    )
    assert nursing.nuc_discipline == NucDiscipline.ALLIED_HEALTH_SCIENCES
    assert nursing.job_search_terms == ["synthetic nurse"]
    version = db.session.scalar(
        select(NucCoreVersion).where(NucCoreVersion.programme_id == nursing.id)
    )
    # Processed right away in tests (TASKS_EAGER), so it is already the active NUC core.
    assert version.is_active and version.version_label == "CCMAS 2023"

    again = load_catalogue(tmp_path, only=["nursing"])
    assert again.queued == [] and again.created == []
    assert again.skipped == ["Synthetic Nursing Science: already has this NUC core"]


def test_admins_load_the_bundled_catalogue_in_the_background(login_as, monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "app.routes.programmes.enqueue", lambda path, *args, **kwargs: calls.append(path)
    )
    admin = login_as("admin")

    status = admin.get("/api/programmes/catalogue").get_json()["data"]
    started = admin.post("/api/programmes/catalogue/load")

    assert status["available"] >= 50 and status["missing"] >= 50
    assert started.status_code == 202
    assert calls == ["app.tasks.catalogue.load_bundled_catalogue"]
    assert login_as("planner").post("/api/programmes/catalogue/load").status_code == 403


def test_catalogue_skips_a_programme_whose_nuc_core_is_still_processing(app, make_user, tmp_path):
    """Synthetic: a programme with an unfinished NUC core is skipped, not a crash."""
    from app.models import Document, DocumentStatus, UserRole
    from app.nuc_catalogue import _busy_or_loaded, catalogue_status
    from app.sessions import default_programme
    from tests.review_data import make_document

    admin = make_user(UserRole.ADMIN)
    programme = default_programme()
    document = make_document(admin.id, "Pending core", "nuc_core")
    document.processing_status = DocumentStatus.PARSING
    db.session.add(
        NucCoreVersion(
            programme_id=programme.id,
            document_id=document.id,
            version_label="CCMAS 2023",
            is_active=False,
            uploaded_by_id=admin.id,
        )
    )
    db.session.commit()
    assert _busy_or_loaded(programme, "CCMAS 2023") == "a NUC core is still being processed"
    assert isinstance(db.session.get(Document, document.id), Document)
    catalogue_status()
