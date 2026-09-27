"""Readable document references: editing details and importing them from a manifest (SYNTHETIC)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.extensions import db
from app.models import AuditLog, Document
from tests.review_data import make_document


def test_planner_edits_details_and_the_label_follows(login_as, make_user) -> None:
    document = make_document(make_user("planner", username="owner").id, "synthetic-advert-file")
    db.session.commit()
    planner = login_as("planner")

    response = planner.patch(
        f"/api/documents/{document.id}",
        json={
            "title": "Senior QA Engineer – Synthetic Ltd",
            "source": "MyJobMag",
            "source_url": "https://www.example.com/job/1",
            "published_on": "2026-09-18",
        },
    )

    assert response.status_code == 200, response.get_json()
    data = response.get_json()["data"]
    assert data["label"] == "Senior QA Engineer – Synthetic Ltd, job advert (MyJobMag, Sep 2026)"
    assert data["source_url"] == "https://www.example.com/job/1"
    entry = db.session.scalars(select(AuditLog).where(AuditLog.action_type == "document.updated"))
    assert entry.one().detail["source"] == {"from": None, "to": "MyJobMag"}

    cleared = planner.patch(f"/api/documents/{document.id}", json={"published_on": None})
    assert cleared.get_json()["data"]["label"].endswith("job advert (MyJobMag)")


def test_document_details_are_validated_and_protected(login_as, make_user) -> None:
    document = make_document(make_user("planner", username="owner").id, "synthetic-file")
    db.session.commit()

    assert login_as("viewer").patch(f"/api/documents/{document.id}", json={}).status_code == 403
    planner = login_as("planner")
    bad = planner.patch(f"/api/documents/{document.id}", json={"source_url": "ftp://x"})
    assert bad.status_code == 422
    assert planner.patch(f"/api/documents/{document.id}", json={"title": None}).status_code == 422
    assert planner.patch("/api/documents/999999", json={"title": "x"}).status_code == 404


def test_import_manifest_sets_titles_source_and_dates(app, make_user, tmp_path) -> None:
    owner = make_user("planner", username="owner")
    advert = make_document(owner.id, "myjobmag_qa_engineer")
    policy = make_document(owner.id, "national-policy", "policy")
    other = make_document(owner.id, "unlisted-upload")
    db.session.commit()
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "file,source,url,title,company,location,date_posted,date_collected\n"
        "job_market/myjobmag_qa_engineer.txt,MyJobMag,https://www.example.com/job/2,"
        "QA Engineer,Synthetic Bank,Lagos,2026-09-01,2026-09-25\n"
        "policy/national-policy.txt,NITDA,https://www.example.com/policy.pdf,"
        "National Synthetic Policy,Federal Ministry,,,2026-09-25\n",
        encoding="utf-8",
    )

    result = app.test_cli_runner().invoke(args=["import-manifest", str(manifest)])

    assert "Updated 2 of 2" in result.output
    db.session.expire_all()
    advert, policy, other = (db.session.get(Document, d.id) for d in (advert, policy, other))
    assert advert.title == "QA Engineer – Synthetic Bank"
    assert (advert.source, advert.published_on) == ("MyJobMag", date(2026, 9, 1))
    assert policy.title == "National Synthetic Policy"  # no company for non-adverts
    assert policy.published_on is None
    assert other.title == "unlisted-upload" and other.source is None
