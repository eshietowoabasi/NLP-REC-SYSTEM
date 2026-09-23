import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class NLPResult(db.Model):
    __tablename__ = "nlp_results"

    result_id: Mapped[int] = mapped_column(primary_key=True)
    doc_session_id: Mapped[int] = mapped_column(
        sa.ForeignKey("document_sessions.doc_session_id", ondelete="CASCADE"), index=True
    )
    tfidf_keywords: Mapped[list | None] = mapped_column(sa.JSON)
    ner_entities: Mapped[list | None] = mapped_column(sa.JSON)
    topics: Mapped[list | None] = mapped_column(sa.JSON)
    # Stored as a JSON float array for portability; see docs/DECISIONS.md (D1).
    embedding: Mapped[list | None] = mapped_column(sa.JSON)

    doc_session = relationship("DocumentSession", back_populates="nlp_results")

    def to_dict(self, include_embedding=False):
        data = {
            "result_id": self.result_id,
            "doc_session_id": self.doc_session_id,
            "document_id": self.doc_session.document_id if self.doc_session else None,
            "tfidf_keywords": self.tfidf_keywords,
            "ner_entities": self.ner_entities,
            "topics": self.topics,
        }
        if include_embedding:
            data["embedding"] = self.embedding
        return data
