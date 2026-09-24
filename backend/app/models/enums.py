"""Enumerations used by the data model.

Stored as VARCHAR with a CHECK constraint (not native PostgreSQL enums) so that adding a value
later is a simple migration.
"""

from __future__ import annotations

from enum import StrEnum

import sqlalchemy as sa


class UserRole(StrEnum):
    ADMIN = "admin"
    PLANNER = "planner"
    VIEWER = "viewer"


class SourceCategory(StrEnum):
    JOB_MARKET = "job_market"
    INSTITUTIONAL = "institutional"
    POLICY = "policy"
    ACADEMIC = "academic"
    NUC_CORE = "nuc_core"


class FileType(StrEnum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    READY = "ready"
    FAILED = "failed"
    ARCHIVED = "archived"


class SessionStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class NLPResultType(StrEnum):
    TFIDF = "tfidf"
    ENTITIES = "entities"
    TOPICS = "topics"
    SIMILARITY = "similarity"


class PlannerDecision(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    FLAGGED = "flagged"


class OverlapStatus(StrEnum):
    POTENTIAL_DUPLICATE = "Potential Duplicate"
    NO_SIGNIFICANT_OVERLAP = "No Significant Overlap"


class ReportFormat(StrEnum):
    PDF = "pdf"
    DOCX = "docx"


class ReportStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SkillLabel(StrEnum):
    SKILL = "SKILL"
    TOOL = "TOOL"
    CERT = "CERT"
    LANGUAGE = "LANGUAGE"


def enum_type(enum_cls: type[StrEnum], name: str) -> sa.Enum:
    """VARCHAR column type restricted (by a CHECK constraint) to the values of ``enum_cls``."""
    return sa.Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )
