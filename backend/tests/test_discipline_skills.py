"""Skills lists per NUC discipline (synthetic patterns; the seed lists are tested in test_seed)."""

from __future__ import annotations

from sqlalchemy import select

from app.extensions import db
from app.models import AuditLog, NucDiscipline, Programme, SkillLabel, SkillPattern
from app.seed.discipline_topic_names import DISCIPLINE_TOPIC_NAMES
from app.tasks.analysis import load_naming, load_skill_patterns
from tests.conftest import ApiClient


def add_pattern(name: str, phrase: str, discipline: NucDiscipline | None) -> SkillPattern:
    pattern = SkillPattern(
        label=SkillLabel.SKILL, pattern=phrase, canonical_name=name, discipline=discipline
    )
    db.session.add(pattern)
    db.session.commit()
    return pattern


def names(discipline: NucDiscipline | None) -> set[str]:
    return {spec.canonical_name for spec in load_skill_patterns(discipline)}


def test_an_analysis_uses_general_skills_and_its_own_disciplines(app) -> None:
    add_pattern("Synthetic Teamwork", "synthetic teamwork", None)
    add_pattern(
        "Synthetic Wound Care", "synthetic wound care", NucDiscipline.ALLIED_HEALTH_SCIENCES
    )
    add_pattern("Synthetic Docker", "synthetic docker", NucDiscipline.COMPUTING)
    retired = add_pattern("Synthetic Old", "synthetic old", None)
    retired.is_active = False
    db.session.commit()

    assert names(NucDiscipline.ALLIED_HEALTH_SCIENCES) == {
        "Synthetic Teamwork",
        "Synthetic Wound Care",
    }
    assert names(NucDiscipline.COMPUTING) == {"Synthetic Teamwork", "Synthetic Docker"}
    # A programme without a discipline is never scored on another field's skills.
    assert names(None) == {"Synthetic Teamwork"}


def test_the_disciplines_endpoint_lists_all_seventeen_with_skill_counts(login_as) -> None:
    add_pattern(
        "Synthetic Wound Care", "synthetic wound care", NucDiscipline.ALLIED_HEALTH_SCIENCES
    )
    add_pattern(
        "Synthetic Wound Care", "synthetic wound dressing", NucDiscipline.ALLIED_HEALTH_SCIENCES
    )
    add_pattern("Synthetic Teamwork", "synthetic teamwork", None)
    planner = login_as("planner")

    data = planner.get("/api/programmes/disciplines").get_json()["data"]

    assert len(data["disciplines"]) == 17
    health = next(d for d in data["disciplines"] if d["value"] == "allied_health_sciences")
    assert health == {
        "value": "allied_health_sciences",
        "name": "Allied Health Sciences",
        "skills": 1,
    }
    assert data["general_skills"] == 1


def test_admins_set_a_programmes_discipline(login_as) -> None:
    admin = login_as("admin")

    created = admin.post(
        "/api/programmes",
        json={"name": "Synthetic Nursing Science", "nuc_discipline": "allied_health_sciences"},
    ).get_json()["data"]
    moved = admin.patch(
        f"/api/programmes/{created['id']}", json={"nuc_discipline": "medicine_and_dentistry"}
    ).get_json()["data"]
    bad = admin.post("/api/programmes", json={"name": "Synthetic X", "nuc_discipline": "magic"})

    assert created["nuc_discipline"] == "allied_health_sciences"
    assert moved["nuc_discipline"] == "medicine_and_dentistry"
    assert db.session.get(Programme, created["id"]).nuc_discipline == "medicine_and_dentistry"
    assert bad.status_code == 422


def test_admins_manage_each_disciplines_list(login_as) -> None:
    admin: ApiClient = login_as("admin")
    body = {"label": "TOOL", "pattern": "synthetic autocad", "canonical_name": "Synthetic CAD"}

    general = admin.post("/api/admin/skill-patterns", json=body)
    engineering = admin.post(
        "/api/admin/skill-patterns", json={**body, "discipline": "engineering_and_technology"}
    )
    again = admin.post(
        "/api/admin/skill-patterns", json={**body, "discipline": "engineering_and_technology"}
    )

    assert general.status_code == 201
    assert general.get_json()["data"]["discipline"] is None
    assert engineering.status_code == 201  # the same phrase may sit in several lists
    assert again.status_code == 409

    listed = admin.get("/api/admin/skill-patterns?discipline=engineering_and_technology")
    general_list = admin.get("/api/admin/skill-patterns?discipline=general")
    assert [p["id"] for p in listed.get_json()["data"]["items"]] == [
        engineering.get_json()["data"]["id"]
    ]
    assert [p["id"] for p in general_list.get_json()["data"]["items"]] == [
        general.get_json()["data"]["id"]
    ]


def test_moving_a_pattern_between_lists_is_audited_and_checked(login_as) -> None:
    admin: ApiClient = login_as("admin")
    first = add_pattern("Synthetic GIS", "synthetic gis", NucDiscipline.SCIENCES)
    add_pattern("Synthetic GIS", "synthetic gis", NucDiscipline.AGRICULTURE)

    clash = admin.patch(f"/api/admin/skill-patterns/{first.id}", json={"discipline": "agriculture"})
    to_general = admin.patch(f"/api/admin/skill-patterns/{first.id}", json={"discipline": None})

    assert clash.status_code == 409
    assert to_general.status_code == 200
    assert to_general.get_json()["data"]["discipline"] is None
    log = db.session.scalar(select(AuditLog).where(AuditLog.action_type == "skill_pattern.updated"))
    assert log.detail["discipline"] == {"from": "sciences", "to": None}


def test_topics_are_named_from_the_programmes_discipline_list(app) -> None:
    nursing = load_naming("fake-model", NucDiscipline.ALLIED_HEALTH_SCIENCES)
    computing = load_naming("fake-model", "computing")

    assert nursing is not None and computing is not None
    assert "Infection Prevention and Control" in nursing.names
    assert "Software Testing and Quality Assurance" not in nursing.names
    assert "Software Testing and Quality Assurance" in computing.names
    assert nursing.name_vectors.shape[0] == len(nursing.names)
    # A programme without a discipline keeps keyword titles.
    assert load_naming("fake-model", None) is None


def test_every_discipline_has_its_own_topic_names() -> None:
    for discipline in NucDiscipline:
        names = DISCIPLINE_TOPIC_NAMES[discipline]
        assert len(names) >= 15, discipline
        assert len({name.lower() for name in names}) == len(names), discipline
        assert all(2 <= len(name) <= 120 for name in names), discipline
