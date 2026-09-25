"""Admin configuration: settings, skill patterns, stop words and the audit log (SYNTHETIC)."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.audit import AuditAction, record_audit
from app.extensions import db
from app.models import AuditLog, Setting, SkillPattern, StopWord
from app.settings import get_setting
from tests.conftest import ApiClient


@pytest.fixture
def admin(login_as) -> ApiClient:
    return login_as("admin")


def setting(data: dict, key: str) -> dict:
    return next(s for s in data["settings"] if s["key"] == key)


# ------------------------------------------------------------------------------ settings


def test_settings_list_values_defaults_and_descriptions(admin: ApiClient) -> None:
    data = admin.get("/api/admin/settings").get_json()["data"]

    weights = setting(data, "score_weights")
    assert weights["value"] == {"ner": 0.4, "topic": 0.35, "novelty": 0.25}
    assert weights["default"] == weights["value"]
    assert weights["description"] and weights["updated_by"] is None
    assert setting(data, "credit_unit_allowance")["value"] is None


def test_update_changes_only_the_sent_settings_and_audits_them(admin: ApiClient) -> None:
    response = admin.put(
        "/api/admin/settings",
        json={
            "score_weights": {"ner": 0.5, "topic": 0.3, "novelty": 0.2},
            "similarity_threshold": 0.75,
            "credit_unit_allowance": 24,
            "max_recommendations": 20,  # unchanged: not audited
        },
    )

    data = response.get_json()["data"]
    assert data["changed"] == ["credit_unit_allowance", "score_weights", "similarity_threshold"]
    assert setting(data, "similarity_threshold")["value"] == 0.75
    assert setting(data, "similarity_threshold")["updated_by"]["full_name"] == admin.user.full_name
    assert get_setting("credit_unit_allowance") == 24
    entry = db.session.scalars(
        select(AuditLog).where(AuditLog.action_type == "settings.updated")
    ).one()
    assert entry.detail["similarity_threshold"] == {"from": 0.8, "to": 0.75}
    assert "max_recommendations" not in entry.detail

    cleared = admin.put("/api/admin/settings", json={"credit_unit_allowance": None})
    assert setting(cleared.get_json()["data"], "credit_unit_allowance")["value"] is None


def test_new_session_defaults_follow_the_settings(admin: ApiClient, login_as) -> None:
    admin.put("/api/admin/settings", json={"max_recommendations": 12, "min_topic_size": 4})

    defaults = login_as("planner").get("/api/sessions/defaults").get_json()["data"]

    assert defaults["parameters"]["max_recommendations"] == 12
    assert defaults["parameters"]["min_topic_size"] == 4


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"score_weights": {"ner": 0.5, "topic": 0.5, "novelty": 0.5}}, "score_weights"),
        ({"similarity_threshold": 1.0}, "similarity_threshold"),
        ({"max_recommendations": 0}, "max_recommendations"),
        ({"passage_sentences": {"min": 5, "max": 3}}, "passage_sentences"),
        ({"passage_words": {"min": 10, "max": 200}}, "passage_words"),
        ({"sbert_model": "bad name!"}, "sbert_model"),
        ({"spacy_model": "xx_not_installed_sm"}, "spacy_model"),
        ({"min_topic_size": 1}, "min_topic_size"),
        ({"credit_unit_allowance": 0}, "credit_unit_allowance"),
        ({"max_documents_per_session": None}, None),
        ({"unknown_setting": 1}, "unknown_setting"),
        ({}, None),
    ],
)
def test_settings_are_validated(admin: ApiClient, body: dict, field: str | None) -> None:
    response = admin.put("/api/admin/settings", json=body)

    assert response.status_code == 422
    if field:
        fields = response.get_json()["error"]["details"]["fields"]
        assert any(key == field or key.startswith(field + ".") for key in fields), fields
    assert db.session.scalar(select(Setting).where(Setting.updated_by_id.is_not(None))) is None


def test_installed_spacy_model_is_accepted(admin: ApiClient) -> None:
    response = admin.put("/api/admin/settings", json={"spacy_model": "en_core_web_sm"})

    assert response.status_code == 200
    assert response.get_json()["data"]["changed"] == []  # already the default


# ------------------------------------------------------------------------ skill patterns


def test_skill_patterns_can_be_listed_filtered_and_searched(admin: ApiClient) -> None:
    db.session.add_all(
        [
            SkillPattern(label="TOOL", pattern="docker", canonical_name="Docker"),
            SkillPattern(
                label="LANGUAGE",
                pattern=[{"LOWER": "go"}, {"LOWER": "developer"}],
                canonical_name="Go",
            ),
            SkillPattern(label="TOOL", pattern="k8s", canonical_name="Kubernetes", is_active=False),
        ]
    )
    db.session.commit()

    def names(query: str) -> list[str]:
        items = admin.get(f"/api/admin/skill-patterns?{query}").get_json()["data"]["items"]
        return [p["canonical_name"] for p in items]

    assert names("") == ["Docker", "Go", "Kubernetes"]
    assert names("label=TOOL") == ["Docker", "Kubernetes"]
    assert names("is_active=false") == ["Kubernetes"]
    assert names("search=k8s") == ["Kubernetes"]  # matches the pattern text
    assert names("search=developer") == ["Go"]  # inside a token pattern
    assert names("search=kube") == ["Kubernetes"]  # matches the canonical name


def test_create_phrase_and_token_patterns(admin: ApiClient) -> None:
    phrase = admin.post(
        "/api/admin/skill-patterns",
        json={"label": "TOOL", "pattern": " Terraform ", "canonical_name": "Terraform"},
    )
    tokens = admin.post(
        "/api/admin/skill-patterns",
        json={
            "label": "LANGUAGE",
            "pattern": [{"LOWER": "rust"}, {"LOWER": {"IN": ["developer", "engineer"]}}],
            "canonical_name": "Rust",
        },
    )

    assert phrase.status_code == 201 and phrase.get_json()["data"]["pattern"] == "Terraform"
    assert tokens.status_code == 201 and tokens.get_json()["data"]["is_active"] is True
    actions = db.session.scalars(
        select(AuditLog.action_type).where(AuditLog.entity_type == "skill_pattern")
    ).all()
    assert actions == ["skill_pattern.created", "skill_pattern.created"]


def test_duplicate_patterns_are_rejected_case_insensitively(admin: ApiClient) -> None:
    db.session.add(SkillPattern(label="TOOL", pattern="Docker", canonical_name="Docker"))
    db.session.commit()

    same = admin.post(
        "/api/admin/skill-patterns",
        json={"label": "TOOL", "pattern": "docker", "canonical_name": "Docker"},
    )
    other_label = admin.post(
        "/api/admin/skill-patterns",
        json={"label": "SKILL", "pattern": "docker", "canonical_name": "Docker"},
    )

    assert same.status_code == 409
    assert "pattern" in same.get_json()["error"]["details"]["fields"]
    assert other_label.status_code == 201


@pytest.mark.parametrize(
    "pattern",
    [[{"LOWERX": "go"}], [], "", [{"LOWER": "a"}] * 11],
)
def test_invalid_patterns_are_rejected(admin: ApiClient, pattern) -> None:
    response = admin.post(
        "/api/admin/skill-patterns",
        json={"label": "TOOL", "pattern": pattern, "canonical_name": "X"},
    )

    assert response.status_code == 422


def test_invalid_token_patterns_explain_the_problem(admin: ApiClient) -> None:
    response = admin.post(
        "/api/admin/skill-patterns",
        json={"label": "TOOL", "pattern": [{"LOWERX": "go"}], "canonical_name": "Go"},
    )

    message = " ".join(response.get_json()["error"]["details"]["fields"]["pattern"])
    assert "token 1 LOWERX" in message


def test_update_and_deactivate_a_pattern(admin: ApiClient) -> None:
    pattern = SkillPattern(label="TOOL", pattern="docker", canonical_name="Docker")
    other = SkillPattern(label="TOOL", pattern="podman", canonical_name="Podman")
    db.session.add_all([pattern, other])
    db.session.commit()
    url = f"/api/admin/skill-patterns/{pattern.id}"

    renamed = admin.patch(url, json={"canonical_name": "Docker Engine", "is_active": False})
    clash = admin.patch(url, json={"pattern": "Podman"})
    invalid = admin.patch(url, json={"pattern": [{"LOWERX": "d"}]})
    empty = admin.patch(url, json={})

    assert renamed.get_json()["data"]["canonical_name"] == "Docker Engine"
    assert renamed.get_json()["data"]["is_active"] is False
    assert clash.status_code == 409
    assert invalid.status_code == 422
    assert empty.status_code == 422
    assert (
        admin.patch("/api/admin/skill-patterns/9999", json={"is_active": True}).status_code == 404
    )
    entry = db.session.scalars(
        select(AuditLog).where(AuditLog.action_type == "skill_pattern.updated")
    ).one()
    assert entry.detail["is_active"] == {"from": True, "to": False}


# ---------------------------------------------------------------------------- stop words


def test_stop_words_can_be_added_listed_and_deactivated(admin: ApiClient) -> None:
    created = admin.post("/api/admin/stop-words", json={"word": "  Lagos "})
    duplicate = admin.post("/api/admin/stop-words", json={"word": "LAGOS"})
    invalid = admin.post("/api/admin/stop-words", json={"word": "two words"})
    word_id = created.get_json()["data"]["id"]

    deactivated = admin.patch(f"/api/admin/stop-words/{word_id}", json={"is_active": False})

    assert created.status_code == 201 and created.get_json()["data"]["word"] == "lagos"
    assert duplicate.status_code == 409
    assert invalid.status_code == 422
    assert deactivated.get_json()["data"]["is_active"] is False
    active = admin.get("/api/admin/stop-words?is_active=true").get_json()["data"]
    found = admin.get("/api/admin/stop-words?search=lag").get_json()["data"]
    assert active["pagination"]["total"] == 0
    assert [w["word"] for w in found["items"]] == ["lagos"]
    assert admin.patch("/api/admin/stop-words/9999", json={"is_active": True}).status_code == 404
    actions = db.session.scalars(
        select(AuditLog.action_type).where(AuditLog.entity_type == "stop_word")
    ).all()
    assert actions == ["stop_word.created", "stop_word.updated"]


# ----------------------------------------------------------------------------- audit log


def add_entry(
    action: AuditAction, days_ago: int, user_id: int | None = None, entity_id: str = "1"
) -> None:
    entry = record_audit(action, "thing", entity_id, {"note": "synthetic"}, user_id=user_id)
    entry.created_at = datetime.now(UTC) - timedelta(days=days_ago)
    db.session.commit()


def test_audit_log_filters_by_user_area_action_and_dates(admin: ApiClient, make_user) -> None:
    planner = make_user("planner", username="auditplanner")
    add_entry(AuditAction.LOGIN, 10, planner.id)
    add_entry(AuditAction.LOGOUT, 5, planner.id)
    add_entry(AuditAction.SESSION_CREATED, 1, planner.id)
    today = datetime.now(UTC).date()

    def actions(query: str) -> list[str]:
        data = admin.get(f"/api/admin/audit-logs?{query}").get_json()["data"]
        return [e["action_type"] for e in data["items"]]

    assert actions(f"user_id={planner.id}") == ["session.created", "auth.logout", "auth.login"]
    assert actions(f"user_id={planner.id}&action=auth") == ["auth.logout", "auth.login"]
    assert actions(f"user_id={planner.id}&action=auth.login") == ["auth.login"]
    week_ago = (today - timedelta(days=7)).isoformat()
    assert actions(f"user_id={planner.id}&date_from={week_ago}") == [
        "session.created",
        "auth.logout",
    ]
    three_days_ago = (today - timedelta(days=3)).isoformat()
    assert actions(f"user_id={planner.id}&date_to={three_days_ago}") == [
        "auth.logout",
        "auth.login",
    ]
    data = admin.get("/api/admin/audit-logs").get_json()["data"]
    assert "report.generated" in data["actions"]
    assert data["items"][0]["user"] is not None  # the admin's own login is logged too
    bad = admin.get(f"/api/admin/audit-logs?date_from={today}&date_to={three_days_ago}")
    assert bad.status_code == 422


def test_audit_log_csv_export_is_filtered_safe_and_audited(admin: ApiClient, make_user) -> None:
    planner = make_user("planner", username="exportplanner")
    add_entry(AuditAction.LOGIN, 1, planner.id, entity_id="=HYPERLINK(1)")
    add_entry(AuditAction.LOGOUT, 1, planner.id)

    response = admin.get(f"/api/admin/audit-logs/export?user_id={planner.id}&action=auth.login")

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment; filename=" in response.headers["Content-Disposition"]
    text = response.data.decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0][:4] == ["time_utc", "user", "username", "action"]
    assert len(rows) == 2 and rows[1][3] == "auth.login"
    assert rows[1][2] == "exportplanner"
    assert rows[1][5] == "'=HYPERLINK(1)"  # formula-like cells are neutralised
    assert rows[1][6] == '{"note": "synthetic"}'
    exported = db.session.scalars(
        select(AuditLog).where(AuditLog.action_type == "audit_log.exported")
    ).one()
    assert exported.detail == {"user_id": planner.id, "action": "auth.login"}


# -------------------------------------------------------------------------------- access


@pytest.mark.parametrize("role", ["planner", "viewer"])
@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", "/api/admin/settings"),
        ("put", "/api/admin/settings"),
        ("get", "/api/admin/skill-patterns"),
        ("post", "/api/admin/skill-patterns"),
        ("patch", "/api/admin/skill-patterns/1"),
        ("get", "/api/admin/stop-words"),
        ("post", "/api/admin/stop-words"),
        ("patch", "/api/admin/stop-words/1"),
        ("get", "/api/admin/audit-logs"),
        ("get", "/api/admin/audit-logs/export"),
    ],
)
def test_only_admins_can_manage_configuration(login_as, role: str, method: str, url: str) -> None:
    client = login_as(role)

    response = getattr(client, method)(url, json={}) if method != "get" else client.get(url)

    assert response.status_code == 403


def test_stop_words_seeded_list_is_visible(admin: ApiClient) -> None:
    db.session.add(StopWord(word="applicant"))
    db.session.commit()

    data = admin.get("/api/admin/stop-words").get_json()["data"]

    assert [w["word"] for w in data["items"]] == ["applicant"]
