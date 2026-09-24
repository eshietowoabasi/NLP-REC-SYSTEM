"""Document management (spec §4, §7): upload, validate, categorise, store, list, delete."""
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import undefer

from ..extensions import db
from ..models import (
    AnalysisSession,
    Document,
    DocumentSession,
    DocumentStatus,
    Role,
    SessionStatus,
    SourceCategory,
)
from ..services.ingestion import (
    ParseError,
    content_hash,
    delete_file,
    parse_document,
    save_bytes,
    validate_upload,
)
from ..services.preprocessing import clean_blocks
from ..utils.audit import record_audit
from ..utils.errors import ApiError, ConflictError, NotFoundError, ValidationError
from ..utils.pagination import paginate
from ..utils.params import parse_enum
from ..utils.rbac import WRITE_ROLES, login_required, roles_required

bp = Blueprint("documents", __name__)

# Only Admins manage the CCMAS reference corpus (spec §14).
ADMIN_ONLY_CATEGORIES = {SourceCategory.NUC_CORE}


def get_document_or_404(document_id, *options):
    document = db.session.get(Document, document_id, options=options)
    if document is None:
        raise NotFoundError("Document not found")
    return document


def _check_can_modify(document):
    if current_user.role is Role.ADMIN:
        return
    if document.source_category in ADMIN_ONLY_CATEGORIES:
        raise ApiError("Only Admins can manage NUC Core Reference documents", code="FORBIDDEN", status_code=403)
    if document.user_id != current_user.user_id:
        raise ApiError("You can only modify documents you uploaded", code="FORBIDDEN", status_code=403)


@bp.get("")
@login_required
def list_documents():
    query = select(Document).order_by(Document.upload_timestamp.desc(), Document.document_id.desc())
    if category := request.args.get("source_category"):
        query = query.where(Document.source_category == parse_enum(SourceCategory, category, "source_category"))
    if status := request.args.get("status"):
        query = query.where(Document.processing_status == parse_enum(DocumentStatus, status, "status"))
    if q := request.args.get("q", "").strip():
        query = query.where(Document.title.ilike(f"%{q}%"))
    if request.args.get("mine") in ("1", "true"):
        query = query.where(Document.user_id == current_user.user_id)
    return jsonify(paginate(query, Document.to_dict))


@bp.post("")
@roles_required(*WRITE_ROLES)
def upload_document():
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        raise ValidationError("A file is required", details={"file": "Required"})

    category_value = request.form.get("source_category")
    if not category_value:
        raise ValidationError("source_category is required", details={"source_category": "Required"})
    category = parse_enum(SourceCategory, category_value, "source_category")
    if category in ADMIN_ONLY_CATEGORIES and current_user.role is not Role.ADMIN:
        raise ApiError("Only Admins can upload NUC Core Reference documents", code="FORBIDDEN", status_code=403)

    original_filename = Path(upload.filename).name[:255]
    title = (request.form.get("title") or Path(original_filename).stem).strip()[:255]
    if not title:
        raise ValidationError("title is required", details={"title": "Required"})

    data = upload.read()
    file_type = validate_upload(original_filename, data, current_app.config["MAX_DOCUMENT_BYTES"])

    digest = content_hash(data)
    existing = db.session.execute(select(Document).filter_by(content_hash=digest)).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(
            "This file has already been uploaded",
            code="DUPLICATE_DOCUMENT",
            details={"document_id": existing.document_id, "title": existing.title},
        )

    path = save_bytes(data, current_app.config["UPLOAD_FOLDER"], file_type.value)
    document = Document(
        user_id=current_user.user_id,
        title=title,
        file_path=path,
        file_type=file_type,
        source_category=category,
        original_filename=original_filename,
        file_size=len(data),
        content_hash=digest,
    )

    # Parse immediately so broken files are reported at upload time, not mid-analysis.
    try:
        parsed = parse_document(data, file_type)
    except ParseError as exc:
        document.processing_status = DocumentStatus.FAILED
        document.error_message = str(exc)
    except Exception:
        current_app.logger.exception("Unexpected parser failure for %s", original_filename)
        document.processing_status = DocumentStatus.FAILED
        document.error_message = "Unexpected error while extracting text"
    else:
        document.processing_status = DocumentStatus.PARSED
        document.extracted_text = parsed.text
        document.word_count = parsed.word_count
        document.page_count = parsed.page_count

    db.session.add(document)
    try:
        db.session.flush()
        record_audit(
            "DOCUMENT_UPLOAD",
            "Document",
            document.document_id,
            {"title": title, "source_category": category.value, "status": document.processing_status.value},
            commit=False,
        )
        db.session.commit()
    except IntegrityError:
        # Lost a race with a concurrent upload of the same file.
        db.session.rollback()
        delete_file(path)
        raise ConflictError("This file has already been uploaded", code="DUPLICATE_DOCUMENT")
    except Exception:
        db.session.rollback()
        delete_file(path)
        raise
    return jsonify({"success": True, "document": document.to_dict()}), 201


@bp.get("/<int:document_id>")
@login_required
def get_document(document_id):
    return jsonify({"success": True, "document": get_document_or_404(document_id).to_dict()})


@bp.get("/<int:document_id>/text")
@login_required
def get_document_text(document_id):
    """Extracted text; ?view=clean applies the preprocessing cleanup (no NLP models)."""
    document = get_document_or_404(document_id, undefer(Document.extracted_text))
    if document.processing_status is not DocumentStatus.PARSED:
        raise ConflictError(
            "Text is not available for this document",
            code="NOT_PARSED",
            details={"processing_status": document.processing_status.value, "error_message": document.error_message},
        )
    view = request.args.get("view", "raw")
    if view not in ("raw", "clean"):
        raise ValidationError("view must be 'raw' or 'clean'")
    text = document.extracted_text or ""
    if view == "clean":
        text = "\n\n".join(clean_blocks(text.split("\n\n")))
    return jsonify({"success": True, "document_id": document.document_id, "view": view, "text": text})


@bp.delete("/<int:document_id>")
@roles_required(*WRITE_ROLES)
def delete_document(document_id):
    document = get_document_or_404(document_id)
    _check_can_modify(document)

    in_progress = db.session.execute(
        select(AnalysisSession.session_id)
        .join(DocumentSession)
        .where(DocumentSession.document_id == document_id, AnalysisSession.status == SessionStatus.PROCESSING)
    ).first()
    if in_progress:
        raise ConflictError(
            "Document is being used by an analysis that is still processing",
            code="DOCUMENT_IN_USE",
            details={"session_id": in_progress.session_id},
        )

    path = document.file_path
    record_audit("DOCUMENT_DELETE", "Document", document.document_id, {"title": document.title}, commit=False)
    db.session.delete(document)
    db.session.commit()
    delete_file(path)
    return jsonify({"success": True})
