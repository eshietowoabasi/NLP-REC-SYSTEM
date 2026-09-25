"""Report content, rendering and the reports API (SYNTHETIC data)."""

from __future__ import annotations

import io
import sys
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from docx import Document as DocxDocument
from sqlalchemy import select

from app.extensions import db
from app.models import AuditLog, CurriculumMap, Report, Setting
from app.services.reports import render as render_module
from app.services.reports.content import (
    REPORT_SECTIONS,
    BulletList,
    DocumentRow,
    KeyValues,
    MappingRow,
    Paragraph,
    RecommendationRow,
    ReportData,
    Table,
    build_report,
    excerpt,
)
from app.services.reports.render import (
    ReportRenderingError,
    render_docx,
    render_html,
    render_pdf,
)
from app.services.storage import get_storage
from tests.conftest import ApiClient
from tests.review_data import ReviewSession, build_review_session

NOW = datetime(2026, 9, 25, 9, 30, tzinfo=UTC)


def weasyprint_available() -> bool:
    try:
        import weasyprint  # noqa: F401
    except (OSError, ImportError):
        return False
    return True


def report_data(**overrides) -> ReportData:
    data = ReportData(
        session_name="Synthetic <2026> review",
        completed_at=NOW,
        generated_at=NOW,
        generated_by="Test Planner",
        nuc_core_version="Synthetic core v1",
        parameters={
            "weights": {"ner": 0.4, "topic": 0.35, "novelty": 0.25},
            "similarity_threshold": 0.8,
        },
        documents=[
            DocumentRow("Synthetic advert", "job_market", "pdf", 2, 800, 6),
            DocumentRow("Synthetic policy", "policy", "docx", None, 1200, 9),
        ],
        keywords={"overall": [{"term": "kubernetes", "score": 0.031, "passage_count": 4}]},
        entities={
            "skills": [
                {"name": "Docker", "label": "TOOL", "mentions": 5, "document_frequency": 2},
                {"name": "AWS Certified", "label": "CERT", "mentions": 1, "document_frequency": 1},
            ],
            "passages_with_skills": 7,
            "passage_count": 15,
        },
        topics={
            "topics": [
                {
                    "title": "Cloud & DevOps",
                    "size": 9,
                    "document_count": 2,
                    "strength": 1.0,
                    "keywords": [{"term": "cloud", "weight": 0.2}],
                }
            ],
            "modelled_passages": 15,
            "outlier_passages": 6,
        },
        similarity={
            "threshold": 0.8,
            "candidates": [
                {
                    "title": "Cloud & DevOps",
                    "max_similarity": 0.83,
                    "novelty": 0.17,
                    "overlap_status": "Potential Duplicate",
                    "closest_nuc_passage": {"text": "Core passage " + "x" * 400},
                }
            ],
        },
        recommendations=[
            RecommendationRow(
                1,
                "Cloud & DevOps",
                "Synthetic description.",
                0.71,
                1.0,
                0.5,
                0.17,
                0.83,
                "Potential Duplicate",
                ["Docker"],
                "accepted",
                "Strong demand",
                "Test Planner",
                NOW,
            ),
            RecommendationRow(
                2,
                "Payments",
                "Other.",
                0.4,
                0.2,
                0.3,
                0.9,
                0.1,
                "No Significant Overlap",
                [],
                None,
                None,
                None,
                None,
            ),
        ],
        mappings=[
            MappingRow("CSC 419", "Cloud Engineering", 3, ["CSC 301"], ["Deploy apps"], 1, "Cloud")
        ],
        credit_unit_allowance=12,
    )
    return replace(data, **overrides)


def blocks_of(doc, key):
    return next(s for s in doc.sections if s.key == key).blocks


# ------------------------------------------------------------------------ content


def test_sections_follow_the_standard_order_whatever_the_request_order() -> None:
    doc = build_report(report_data(), ["proposed_courses", "corpus_summary", "overlap"])

    assert [s.key for s in doc.sections] == ["corpus_summary", "overlap", "proposed_courses"]
    assert doc.subtitle == "Synthetic <2026> review"
    assert ("NUC core reference", "Synthetic core v1") in doc.meta
    with pytest.raises(ValueError, match="Unknown report sections"):
        build_report(report_data(), ["summary"])


def test_corpus_summary_counts_documents_words_and_passages() -> None:
    blocks = blocks_of(build_report(report_data(), ["corpus_summary"]), "corpus_summary")

    assert "2 documents (2,000 words, 15 passages)" in blocks[0].text
    assert blocks[1] == KeyValues([("Job market", "1 document"), ("Policy", "1 document")])
    table = blocks[2]
    assert table.rows[1] == ["Synthetic policy", "Policy", "DOCX", "—", "1,200", "9"]


def test_findings_overlap_and_recommendations_use_the_stored_results() -> None:
    doc = build_report(report_data(), ["nlp_findings", "overlap", "recommendations"])

    findings = blocks_of(doc, "nlp_findings")
    tables = [b for b in findings if isinstance(b, Table)]
    assert tables[0].rows == [["kubernetes", "0.031", "4"]]
    assert tables[1].rows[1][1] == "Certification"
    assert "6 passages fitted no theme" in findings[-2].text

    overlap = blocks_of(doc, "overlap")
    assert "above 0.80" in overlap[0].text and "1 of 1" in overlap[0].text
    assert overlap[1].rows[0][3] == "Potential Duplicate"
    assert overlap[1].rows[0][4].endswith("…") and len(overlap[1].rows[0][4]) <= 220

    recs = blocks_of(doc, "recommendations")
    assert "0.40 × skill demand + 0.35 × theme strength + 0.25 × novelty" in recs[0].text
    assert recs[1].rows[0] == [
        "1",
        "Cloud & DevOps",
        "0.71",
        "1.00",
        "0.50",
        "0.17",
        "Potential duplicate",
    ]
    assert recs[1].rows[1][-1] == "New"


def test_decisions_summarise_and_list_reviewed_recommendations() -> None:
    blocks = blocks_of(build_report(report_data(), ["decisions"]), "decisions")

    assert ("Accepted", "1") in blocks[0].items and ("Not yet reviewed", "1") in blocks[0].items
    assert blocks[1].rows == [
        ["1", "Cloud & DevOps", "Accepted", "Test Planner", "25 Sep 2026", "Strong demand"]
    ]
    undecided = report_data(recommendations=report_data().recommendations[1:])
    empty = blocks_of(build_report(undecided, ["decisions"]), "decisions")
    assert empty[1] == Paragraph("No recommendation has been reviewed yet.", muted=True)


@pytest.mark.parametrize(
    ("allowance", "expected"),
    [
        (12, "3 of 12 credit units (9 remaining)."),
        (2, "3 of 2 credit units: over the allowance by 1."),
        (None, "3 credit units proposed. No 30% credit-unit allowance has been configured."),
    ],
)
def test_proposed_courses_compare_units_with_the_allowance(allowance, expected) -> None:
    doc = build_report(report_data(credit_unit_allowance=allowance), ["proposed_courses"])

    blocks = blocks_of(doc, "proposed_courses")
    assert blocks[0].text == expected
    assert blocks[1].rows[0] == ["CSC 419", "Cloud Engineering", "3", "CSC 301", "#1 Cloud"]
    assert blocks[-1] == BulletList(["Deploy apps"])


def test_empty_sections_say_so() -> None:
    data = report_data(keywords={}, entities={}, topics={}, mappings=[])
    doc = build_report(data, ["nlp_findings", "proposed_courses"])

    findings = blocks_of(doc, "nlp_findings")
    assert Paragraph("No terms were extracted.", muted=True) in findings
    assert Paragraph("No skill patterns matched the documents.", muted=True) in findings
    assert blocks_of(doc, "proposed_courses")[0].muted


def test_excerpt_collapses_whitespace_and_shortens() -> None:
    assert excerpt("a  b\nc") == "a b c"
    assert excerpt("x" * 10, limit=5) == "xxxx…"


# ---------------------------------------------------------------------- rendering


def test_html_escapes_user_text_and_numbers_sections() -> None:
    html = render_html(build_report(report_data(), list(REPORT_SECTIONS)))

    assert "Synthetic &lt;2026&gt; review" in html
    assert "<2026>" not in html
    assert "Cloud &amp; DevOps" in html
    assert "6. Proposed courses" in html
    assert "counter(pages)" in html  # page numbers in the PDF footer


def test_docx_contains_the_report_content() -> None:
    content = render_docx(build_report(report_data(), list(REPORT_SECTIONS)))

    document = DocxDocument(io.BytesIO(content))
    text = "\n".join(p.text for p in document.paragraphs)
    cells = {c.text for t in document.tables for row in t.rows for c in row.cells}
    assert "Curriculum Recommendation Report" in text
    assert "1. Corpus summary" in text and "6. Proposed courses" in text
    assert "Deploy apps" in text
    assert {"CSC 419", "Cloud Engineering", "Synthetic core v1"} <= cells


def test_pdf_reports_missing_system_libraries_clearly(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "weasyprint", None)  # makes "import weasyprint" fail

    with pytest.raises(ReportRenderingError, match="PDF generation is not available"):
        render_pdf(build_report(report_data(), ["decisions"]))


@pytest.mark.skipif(not weasyprint_available(), reason="WeasyPrint system libraries missing")
def test_pdf_renders_with_weasyprint() -> None:
    content = render_pdf(build_report(report_data(), list(REPORT_SECTIONS)))

    assert content.startswith(b"%PDF")
    assert len(content) > 5000


# ----------------------------------------------------------------------------- API


@pytest.fixture
def review(make_user) -> ReviewSession:
    return build_review_session(make_user("planner", username="owner"))


@pytest.fixture
def planner(login_as) -> ApiClient:
    return login_as("planner")


def generate(client: ApiClient, session_id: int, **body):
    payload = {"format": "docx", "sections": list(REPORT_SECTIONS), **body}
    return client.post(f"/api/sessions/{session_id}/reports", json=payload)


def test_generate_and_download_a_docx_report(planner: ApiClient, review: ReviewSession) -> None:
    db.session.merge(Setting(key="credit_unit_allowance", value=12))
    db.session.commit()

    response = generate(planner, review.session.id)

    assert response.status_code == 202
    report_id = response.get_json()["data"]["id"]
    detail = planner.get(f"/api/reports/{report_id}").get_json()["data"]
    assert detail["status"] == "completed"
    assert detail["session"] == {"id": review.session.id, "session_name": "Synthetic review"}
    assert detail["created_by"]["full_name"] == planner.user.full_name
    assert detail["file_size"] > 1000
    download = planner.get(f"/api/reports/{report_id}/download")
    assert download.status_code == 200
    assert download.mimetype.endswith("wordprocessingml.document")
    assert "NLP-RS report - Synthetic review - " in download.headers["Content-Disposition"]
    document = DocxDocument(io.BytesIO(download.data))
    text = "\n".join(p.text for p in document.paragraphs)
    assert "Synthetic description of Cloud Security and Kubernetes." in text
    entry = db.session.scalars(
        select(AuditLog).where(AuditLog.action_type == "report.generated")
    ).one()
    assert entry.detail["format"] == "docx"


def test_pdf_reports_use_the_pdf_renderer(
    planner: ApiClient, review: ReviewSession, monkeypatch
) -> None:
    monkeypatch.setattr("app.tasks.reports.render_pdf", lambda doc: b"%PDF-1.7 synthetic")

    report_id = generate(planner, review.session.id, format="pdf").get_json()["data"]["id"]

    download = planner.get(f"/api/reports/{report_id}/download")
    assert download.mimetype == "application/pdf"
    assert download.data == b"%PDF-1.7 synthetic"
    assert "Synthetic review" in download.headers["Content-Disposition"]
    assert ".pdf" in download.headers["Content-Disposition"]


def test_rendering_problems_fail_the_report_with_a_message(
    planner: ApiClient, review: ReviewSession, monkeypatch
) -> None:
    def unavailable(doc):
        raise ReportRenderingError("PDF generation is not available on this server.")

    monkeypatch.setattr("app.tasks.reports.render_pdf", unavailable)
    report_id = generate(planner, review.session.id, format="pdf").get_json()["data"]["id"]

    detail = planner.get(f"/api/reports/{report_id}").get_json()["data"]
    assert detail["status"] == "failed"
    assert detail["error_message"] == "PDF generation is not available on this server."
    assert planner.get(f"/api/reports/{report_id}/download").status_code == 409


def test_unexpected_failures_are_reported_generically(
    planner: ApiClient, review: ReviewSession, monkeypatch
) -> None:
    def explode(doc):
        raise RuntimeError("internal detail")

    monkeypatch.setattr("app.tasks.reports.render_docx", explode)
    report_id = generate(planner, review.session.id).get_json()["data"]["id"]

    detail = planner.get(f"/api/reports/{report_id}").get_json()["data"]
    assert detail["status"] == "failed"
    assert "internal detail" not in detail["error_message"]


@pytest.mark.parametrize(
    "body",
    [
        {"sections": []},
        {"sections": ["overlap", "overlap"]},
        {"sections": ["summary"]},
        {"format": "html"},
    ],
)
def test_report_requests_are_validated(planner: ApiClient, review: ReviewSession, body) -> None:
    assert generate(planner, review.session.id, **body).status_code == 422


def test_reports_need_a_completed_session(planner: ApiClient, review: ReviewSession) -> None:
    review.session.status = "processing"
    db.session.commit()

    response = generate(planner, review.session.id)

    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "RESULTS_NOT_READY"
    assert generate(planner, 9999).status_code == 404


def test_list_filters_and_viewer_access(
    login_as, planner: ApiClient, review: ReviewSession
) -> None:
    generate(planner, review.session.id)
    generate(planner, review.session.id, format="pdf", sections=["decisions"])
    viewer = login_as("viewer")

    listing = viewer.get("/api/reports").get_json()["data"]
    only_docx = viewer.get("/api/reports?format=docx").get_json()["data"]
    by_session = viewer.get(f"/api/reports?session_id={review.session.id}").get_json()["data"]

    assert listing["pagination"]["total"] == 2
    assert listing["items"][0]["format"] == "pdf"  # newest first
    assert [r["format"] for r in only_docx["items"]] == ["docx"]
    assert by_session["pagination"]["total"] == 2
    docx_id = only_docx["items"][0]["id"]
    assert viewer.get(f"/api/reports/{docx_id}/download").status_code == 200
    assert generate(viewer, review.session.id).status_code == 403
    assert viewer.delete(f"/api/reports/{docx_id}").status_code == 403
    assert viewer.get("/api/reports/9999").status_code == 404


def test_delete_removes_the_report_and_its_file(planner: ApiClient, review: ReviewSession) -> None:
    report_id = generate(planner, review.session.id).get_json()["data"]["id"]
    file_path = db.session.get(Report, report_id).file_path
    path = get_storage().path(file_path, area="reports")
    assert path.exists()

    assert planner.delete(f"/api/reports/{report_id}").status_code == 200

    assert not path.exists()
    assert db.session.get(Report, report_id) is None
    assert planner.get(f"/api/reports/{report_id}").status_code == 404


def test_reports_being_generated_cannot_be_deleted(
    planner: ApiClient, review: ReviewSession, monkeypatch
) -> None:
    monkeypatch.setattr("app.routes.reports.enqueue", lambda *args: None)  # stays queued
    report_id = generate(planner, review.session.id).get_json()["data"]["id"]

    assert planner.delete(f"/api/reports/{report_id}").status_code == 409
    assert planner.get(f"/api/reports/{report_id}/download").status_code == 409


def test_missing_report_files_are_404(planner: ApiClient, review: ReviewSession) -> None:
    report_id = generate(planner, review.session.id).get_json()["data"]["id"]
    get_storage().delete(db.session.get(Report, report_id).file_path, area="reports")

    assert planner.get(f"/api/reports/{report_id}/download").status_code == 404
    assert planner.get(f"/api/reports/{report_id}").get_json()["data"]["file_size"] is None


def test_deleting_a_session_removes_its_report_files(
    planner: ApiClient, review: ReviewSession
) -> None:
    report_id = generate(planner, review.session.id).get_json()["data"]["id"]
    path = get_storage().path(db.session.get(Report, report_id).file_path, area="reports")

    assert planner.delete(f"/api/sessions/{review.session.id}").status_code == 200

    assert not path.exists()
    assert db.session.get(Report, report_id) is None


def test_report_includes_mapped_courses(planner: ApiClient, review: ReviewSession) -> None:
    first = review.recommendations[0]
    planner.patch(f"/api/recommendations/{first.id}/decision", json={"decision": "accepted"})
    planner.post(
        f"/api/recommendations/{first.id}/mapping",
        json={
            "course_code": "CSC 419",
            "course_title": "Cloud Security Engineering",
            "credit_units": 3,
            "prerequisites": [],
            "learning_outcomes": ["Secure cloud workloads"],
        },
    )
    assert db.session.scalar(select(CurriculumMap.course_code)) == "CSC 419"

    report_id = generate(planner, review.session.id, sections=["proposed_courses"]).get_json()[
        "data"
    ]["id"]

    document = DocxDocument(io.BytesIO(planner.get(f"/api/reports/{report_id}/download").data))
    text = "\n".join(p.text for p in document.paragraphs)
    assert "CSC 419: Cloud Security Engineering" in text
    assert "Secure cloud workloads" in text
    assert "Corpus summary" not in text


def test_render_module_uses_the_template_directory() -> None:
    assert (render_module.TEMPLATES / "report.html").exists()
