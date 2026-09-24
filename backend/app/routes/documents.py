"""Document library: upload, list, view, download, archive and delete source documents."""

from __future__ import annotations

from flask import Blueprint, Response, request, send_file
from flask_login import current_user
from sqlalchemy import func, or_, select

from app.audit import AuditAction, record_audit
from app.auth.decorators import EDITOR_ROLES, login_required, role_required
from app.extensions import db
from app.models import (
    AnalysisSession,
    Document,
    DocumentSession,
    DocumentStatus,
    FileType,
    NucCoreVersion,
    Passage,
    SourceCategory,
)
from app.schemas.documents import (
    UPLOAD_CATEGORIES,
    DocumentDetailOut,
    DocumentListQuery,
    DocumentOut,
    PassageListQuery,
    PassageOut,
    SessionRef,
)
from app.services.ingestion.validation import UploadRejectedError
from app.services.storage import get_storage
from app.tasks.queue import enqueue
from app.uploads import discard, store_upload
from app.utils.errors import ApiError
from app.utils.responses import success
from app.utils.validation import paginate, parse_query

bp = Blueprint("documents", __name__, url_prefix="/documents")

INGEST_JOB = "app.tasks.ingestion.ingest_document"
PREVIEW_PASSAGES = 5
MIME_TYPES = {
    FileType.PDF: "application/pdf",
    FileType.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    FileType.TXT: "text/plain",
}


def document_json(document: Document) -> dict:
    return DocumentOut.model_validate(document).model_dump(mode="json")


def get_document_or_404(document_id: int) -> Document:
    document = db.session.get(Document, document_id)
    if document is None:
        raise ApiError("NOT_FOUND", "Document not found.", 404)
    return document


def sessions_using(document_id: int) -> list[AnalysisSession]:
    return list(
        db.session.scalars(
            select(AnalysisSession)
            .join(DocumentSession, DocumentSession.session_id == AnalysisSession.id)
            .where(DocumentSession.document_id == document_id)
            .order_by(AnalysisSession.created_at.desc())
        )
    )


@bp.get("")
@login_required
def list_documents() -> tuple[Response, int]:
    """List documents with filters, plus per-category counts of active documents.

    NUC core documents are excluded unless ``category=nuc_core`` is requested; archived
    documents unless ``status=archived`` is requested.
    """
    params = parse_query(DocumentListQuery)
    query = select(Document).order_by(Document.uploaded_at.desc(), Document.id.desc())
    if params.category is not None:
        query = query.where(Document.source_category == params.category)
    else:
        query = query.where(Document.source_category != SourceCategory.NUC_CORE)
    if params.status is not None:
        query = query.where(Document.processing_status == params.status)
    else:
        query = query.where(Document.processing_status != DocumentStatus.ARCHIVED)
    if params.search:
        pattern = f"%{params.search}%"
        query = query.where(
            or_(Document.title.ilike(pattern), Document.original_filename.ilike(pattern))
        )
    documents, meta = paginate(query, params.page, params.per_page)

    counts = dict.fromkeys((category.value for category in UPLOAD_CATEGORIES), 0)
    rows = db.session.execute(
        select(Document.source_category, func.count())
        .where(
            Document.processing_status != DocumentStatus.ARCHIVED,
            Document.source_category != SourceCategory.NUC_CORE,
        )
        .group_by(Document.source_category)
    )
    for category, count in rows:
        counts[SourceCategory(category).value] = count

    return success(
        {
            "items": [document_json(document) for document in documents],
            "pagination": meta,
            "category_counts": counts,
        }
    )


@bp.post("")
@role_required(*EDITOR_ROLES)
def upload_documents() -> tuple[Response, int]:
    """Upload one or more files (multipart ``files``) with one ``categories`` value each.

    Each file is accepted or rejected on its own. Accepted files are queued for ingestion.
    Returns 201 when at least one file was accepted, otherwise 422.
    """
    files = request.files.getlist("files")
    categories = request.form.getlist("categories")
    if not files:
        raise ApiError("VALIDATION_ERROR", "Choose at least one file to upload.", 422)
    if len(categories) != len(files):
        raise ApiError("VALIDATION_ERROR", "Provide one category for each uploaded file.", 422)

    allowed = {category.value for category in UPLOAD_CATEGORIES}
    accepted: list[Document] = []
    rejected: list[dict[str, str]] = []
    try:
        for upload, category in zip(files, categories, strict=True):
            name = upload.filename or "(unnamed)"
            if category not in allowed:
                rejected.append({"filename": name, "reason": "Choose a valid category."})
                continue
            try:
                document = store_upload(upload, SourceCategory(category), current_user)
            except UploadRejectedError as exc:
                rejected.append({"filename": name, "reason": str(exc)})
                continue
            accepted.append(document)
            record_audit(
                AuditAction.DOCUMENT_UPLOADED,
                "document",
                document.id,
                {
                    "filename": document.original_filename,
                    "category": category,
                    "size": document.file_size,
                },
            )
        if accepted:
            db.session.commit()
    except Exception:
        # Nothing was committed: remove the files already written to storage.
        db.session.rollback()
        discard(accepted)
        raise

    if not accepted:
        raise ApiError(
            "VALIDATION_ERROR", "None of the files could be accepted.", 422, {"rejected": rejected}
        )
    for document in accepted:
        enqueue(INGEST_JOB, document.id)
    for document in accepted:
        db.session.refresh(document)
    return success({"accepted": [document_json(d) for d in accepted], "rejected": rejected}, 201)


@bp.get("/<int:document_id>")
@login_required
def get_document(document_id: int) -> tuple[Response, int]:
    """Document metadata, a short text preview and the sessions that use it."""
    document = get_document_or_404(document_id)
    passage_count = db.session.scalar(
        select(func.count()).select_from(Passage).where(Passage.document_id == document.id)
    )
    preview = db.session.scalars(
        select(Passage)
        .where(Passage.document_id == document.id)
        .order_by(Passage.position)
        .limit(PREVIEW_PASSAGES)
    )
    data = DocumentDetailOut.model_validate(
        {
            **DocumentOut.model_validate(document).model_dump(),
            "passage_count": passage_count or 0,
            "preview": [PassageOut.model_validate(p) for p in preview],
            "sessions": [SessionRef.model_validate(s) for s in sessions_using(document.id)],
            "is_nuc_core": document.source_category == SourceCategory.NUC_CORE,
        }
    )
    return success(data.model_dump(mode="json"))


@bp.get("/<int:document_id>/passages")
@login_required
def list_passages(document_id: int) -> tuple[Response, int]:
    """All extracted passages of a document, in order (paginated)."""
    document = get_document_or_404(document_id)
    params = parse_query(PassageListQuery)
    query = select(Passage).where(Passage.document_id == document.id).order_by(Passage.position)
    passages, meta = paginate(query, params.page, params.per_page)
    return success(
        {
            "items": [PassageOut.model_validate(p).model_dump(mode="json") for p in passages],
            "pagination": meta,
        }
    )


@bp.get("/<int:document_id>/file")
@login_required
def download_document(document_id: int) -> Response:
    """Download the original file (never served from a public path)."""
    document = get_document_or_404(document_id)
    path = get_storage().path(document.stored_filename)
    if not path.exists():
        raise ApiError("NOT_FOUND", "The stored file is missing.", 404)
    return send_file(
        path,
        mimetype=MIME_TYPES[FileType(document.file_type)],
        as_attachment=True,
        download_name=document.original_filename,
    )


def _reject_nuc_core(document: Document, action: str) -> None:
    if document.source_category == SourceCategory.NUC_CORE:
        raise ApiError(
            "CONFLICT",
            f"NUC core documents cannot be {action} here; manage them on the NUC Core "
            "Reference screen.",
            409,
        )


@bp.post("/<int:document_id>/archive")
@role_required(*EDITOR_ROLES)
def archive_document(document_id: int) -> tuple[Response, int]:
    """Hide a document from the library and from new sessions; past sessions keep it."""
    document = get_document_or_404(document_id)
    _reject_nuc_core(document, "archived")
    if document.processing_status == DocumentStatus.ARCHIVED:
        return success(document_json(document))
    if document.processing_status in (DocumentStatus.UPLOADED, DocumentStatus.PARSING):
        raise ApiError(
            "CONFLICT", "The document is still being processed; archive it once it is done.", 409
        )
    document.processing_status = DocumentStatus.ARCHIVED
    record_audit(AuditAction.DOCUMENT_ARCHIVED, "document", document.id, {"title": document.title})
    db.session.commit()
    return success(document_json(document))


@bp.delete("/<int:document_id>")
@role_required(*EDITOR_ROLES)
def delete_document(document_id: int) -> tuple[Response, int]:
    """Permanently delete a document that no analysis session has used."""
    document = get_document_or_404(document_id)
    _reject_nuc_core(document, "deleted")
    used_by = sessions_using(document.id)
    if used_by:
        raise ApiError(
            "CONFLICT",
            "This document is used by an analysis session and cannot be deleted. "
            "Archive it instead.",
            409,
            {"sessions": [{"id": s.id, "session_name": s.session_name} for s in used_by]},
        )
    if db.session.scalar(
        select(NucCoreVersion.id).where(NucCoreVersion.document_id == document.id)
    ):
        raise ApiError("CONFLICT", "This document is a NUC core version.", 409)
    stored_filename = document.stored_filename
    record_audit(
        AuditAction.DOCUMENT_DELETED,
        "document",
        document.id,
        {"title": document.title, "filename": document.original_filename},
    )
    db.session.delete(document)
    db.session.commit()
    get_storage().delete(stored_filename)
    return success({"deleted": True})
