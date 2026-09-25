"""Background job: generate a PDF or DOCX report for a completed session.

The job loads everything the report can show into a plain :class:`ReportData`, builds the
format-neutral document (``app.services.reports.content``), renders it and stores the file in
the reports storage area under a UUID name. Failures leave the report ``failed`` with a message.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select

from app.extensions import db
from app.models import (
    AnalysisSession,
    CurriculumMap,
    Document,
    DocumentSession,
    NLPResult,
    Passage,
    Recommendation,
    Report,
    ReportFormat,
    ReportStatus,
)
from app.services.reports.content import (
    DocumentRow,
    MappingRow,
    RecommendationRow,
    ReportData,
    build_report,
)
from app.services.reports.render import ReportRenderingError, render_docx, render_pdf
from app.services.storage import get_storage
from app.settings import get_setting
from app.utils.time import utcnow

logger = logging.getLogger(__name__)


def load_report_data(session: AnalysisSession, generated_by: str) -> ReportData:
    """Collect the session's documents, stored results, recommendations and mappings."""
    passage_counts = dict(
        db.session.execute(
            select(Passage.document_id, func.count())
            .join(DocumentSession, DocumentSession.document_id == Passage.document_id)
            .where(DocumentSession.session_id == session.id)
            .group_by(Passage.document_id)
        ).all()
    )
    documents = [
        DocumentRow(
            title=d.title,
            category=str(d.source_category),
            file_type=str(d.file_type),
            page_count=d.page_count,
            word_count=d.word_count,
            passage_count=passage_counts.get(d.id, 0),
        )
        for d in db.session.scalars(
            select(Document)
            .join(DocumentSession, DocumentSession.document_id == Document.id)
            .where(DocumentSession.session_id == session.id)
            .order_by(DocumentSession.processing_order)
        )
    ]
    results = {
        str(result_type): payload
        for result_type, payload in db.session.execute(
            select(NLPResult.result_type, NLPResult.payload).where(
                NLPResult.session_id == session.id
            )
        ).all()
    }
    recommendations = list(
        db.session.scalars(
            select(Recommendation)
            .where(Recommendation.session_id == session.id)
            .order_by(Recommendation.rank)
        )
    )
    mappings = db.session.execute(
        select(CurriculumMap, Recommendation)
        .join(Recommendation, Recommendation.id == CurriculumMap.recommendation_id)
        .where(Recommendation.session_id == session.id)
        .order_by(CurriculumMap.course_code)
    ).all()
    allowance = get_setting("credit_unit_allowance")
    return ReportData(
        session_name=session.session_name,
        completed_at=session.completed_at,
        generated_at=utcnow(),
        generated_by=generated_by,
        nuc_core_version=(
            session.nuc_core_version.version_label if session.nuc_core_version else None
        ),
        parameters=session.parameter_config or {},
        documents=documents,
        keywords=results.get("tfidf", {}),
        entities=results.get("entities", {}),
        topics=results.get("topics", {}),
        similarity=results.get("similarity", {}),
        recommendations=[
            RecommendationRow(
                rank=r.rank,
                title=r.topic_title,
                description=r.topic_description,
                composite=r.composite_score,
                ner=r.ner_score,
                topic=r.topic_score,
                novelty=r.novelty_score,
                max_similarity=r.max_similarity,
                overlap_status=str(r.overlap_status),
                skills=[s["name"] for s in (r.skills or [])],
                decision=str(r.planner_decision) if r.planner_decision else None,
                notes=r.planner_notes,
                decided_by=r.decided_by.full_name if r.decided_by else None,
                decided_at=r.decided_at,
            )
            for r in recommendations
        ],
        mappings=[
            MappingRow(
                course_code=m.course_code,
                course_title=m.course_title,
                credit_units=m.credit_units,
                prerequisites=list(m.prerequisites or []),
                learning_outcomes=list(m.learning_outcomes or []),
                recommendation_rank=r.rank,
                recommendation_title=r.topic_title,
            )
            for m, r in mappings
        ],
        credit_unit_allowance=int(allowance) if isinstance(allowance, int | float) else None,
    )


def _fail(report_id: int, message: str) -> None:
    db.session.rollback()
    report = db.session.get(Report, report_id)
    if report is not None:
        report.status = ReportStatus.FAILED
        report.error_message = message
        report.completed_at = utcnow()
        db.session.commit()


def generate_report(report_id: int) -> None:
    """Render the report with id ``report_id`` and store the file."""
    report = db.session.get(Report, report_id)
    if report is None or report.status != ReportStatus.QUEUED:
        logger.info("Skipping report %s (missing or not queued)", report_id)
        return
    report.status = ReportStatus.PROCESSING
    db.session.commit()
    try:
        data = load_report_data(report.session, report.created_by.full_name)
        document = build_report(data, list(report.sections))
        if report.format == ReportFormat.PDF:
            content, extension = render_pdf(document), ".pdf"
        else:
            content, extension = render_docx(document), ".docx"
        report.file_path = get_storage().save(content, extension, area="reports")
        report.status = ReportStatus.COMPLETED
        report.completed_at = utcnow()
        db.session.commit()
        logger.info("Report %s generated (%s, %d bytes)", report_id, report.format, len(content))
    except ReportRenderingError as exc:
        logger.warning("Report %s failed: %s", report_id, exc)
        _fail(report_id, str(exc))
    except Exception:
        logger.exception("Report %s failed unexpectedly", report_id)
        _fail(
            report_id, "The report could not be generated. Try again or contact an administrator."
        )
    finally:
        db.session.remove()
