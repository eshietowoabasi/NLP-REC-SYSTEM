"""Background job: ingest one uploaded document (runs once per document, after upload).

    stored file → parse → clean → passages → normalised text → SBERT embeddings → database

The document moves ``uploaded → parsing → ready`` (or ``failed`` with a message the uploader
can act on). Sessions later reuse the stored passages and embeddings.
"""

from __future__ import annotations

import logging
import time

from sqlalchemy import delete, select, update

from app.extensions import db
from app.models import Document, DocumentStatus, NucCoreVersion, Passage, SourceCategory, StopWord
from app.services.embeddings.encoder import get_encoder
from app.services.ingestion.parsers import ParseError
from app.services.ingestion.passages import PassageConfig
from app.services.ingestion.pipeline import process_document
from app.services.preprocessing.normalise import StopWords
from app.services.preprocessing.spacy_model import get_nlp
from app.services.storage import get_storage
from app.settings import get_setting
from app.utils.time import utcnow

logger = logging.getLogger(__name__)

UNEXPECTED_FAILURE = "Processing failed unexpectedly. Try uploading the file again."


def load_stop_words() -> StopWords:
    """Standard English stop words plus the admin-managed active domain stop words."""
    custom = db.session.scalars(select(StopWord.word).where(StopWord.is_active.is_(True)))
    return StopWords.build(custom)


def activate_nuc_core_version(document: Document) -> None:
    """Make the NUC core version of ``document`` active, unless a newer one already is."""
    version = db.session.scalar(
        select(NucCoreVersion).where(NucCoreVersion.document_id == document.id)
    )
    if version is None:
        return
    active = db.session.scalar(select(NucCoreVersion).where(NucCoreVersion.is_active.is_(True)))
    if active is not None and active.id > version.id:
        logger.info(
            "NUC core version %s is ready but newer version %s is active", version.id, active.id
        )
        return
    # Deactivate first: the partial unique index allows only one active row at a time.
    db.session.execute(
        update(NucCoreVersion).where(NucCoreVersion.is_active.is_(True)).values(is_active=False)
    )
    db.session.flush()
    version.is_active = True


def _fail(document_id: int, message: str) -> None:
    db.session.rollback()
    document = db.session.get(Document, document_id)
    if document is not None:
        document.processing_status = DocumentStatus.FAILED
        document.error_message = message
        db.session.commit()


def ingest_document(document_id: int) -> None:
    """Process the document with id ``document_id`` and store its passages."""
    document = db.session.get(Document, document_id)
    if document is None or document.processing_status == DocumentStatus.ARCHIVED:
        logger.info("Skipping ingestion of document %s (missing or archived)", document_id)
        return
    document.processing_status = DocumentStatus.PARSING
    document.error_message = None
    db.session.commit()

    started = time.perf_counter()
    try:
        content = get_storage().read(document.stored_filename)
        config = PassageConfig.from_settings(
            get_setting("passage_sentences"), get_setting("passage_words")
        )
        output = process_document(
            document.file_type,
            content,
            get_nlp(get_setting("spacy_model")),
            load_stop_words(),
            config,
        )
        encoder = get_encoder(get_setting("sbert_model"))
        vectors = encoder.encode([passage.text for passage in output.passages])

        db.session.execute(delete(Passage).where(Passage.document_id == document.id))
        db.session.add_all(
            Passage(
                document_id=document.id,
                position=passage.position,
                page_number=passage.page_number,
                text=passage.text,
                normalised_text=passage.normalised_text,
                embedding=vector.tolist(),
                embedding_model=encoder.model_name,
            )
            for passage, vector in zip(output.passages, vectors, strict=True)
        )
        document.page_count = output.page_count
        document.word_count = output.word_count
        document.parsed_at = utcnow()
        document.processing_status = DocumentStatus.READY
        if document.source_category == SourceCategory.NUC_CORE:
            activate_nuc_core_version(document)
        db.session.commit()
        logger.info(
            "Ingested document %s: %s passages, %s words in %.1fs",
            document.id,
            len(output.passages),
            output.word_count,
            time.perf_counter() - started,
        )
    except ParseError as exc:
        logger.info("Document %s could not be parsed: %s", document_id, exc)
        _fail(document_id, str(exc))
    except Exception:
        logger.exception("Unexpected error while ingesting document %s", document_id)
        _fail(document_id, UNEXPECTED_FAILURE)
    finally:
        db.session.remove()
