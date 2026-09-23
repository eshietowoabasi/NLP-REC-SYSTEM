"""Controlled vocabularies from the specification (§7.1, §11.2, §11.3, §14)."""
import enum

import sqlalchemy as sa


class Role(str, enum.Enum):
    ADMIN = "Admin"
    PLANNER = "Curriculum Planner"
    VIEWER = "Viewer"


class SourceCategory(str, enum.Enum):
    NUC_CORE = "NUC Core Reference"
    JOB_MARKET = "Job Market Data"
    INSTITUTIONAL = "Institutional Document"
    POLICY = "Policy Document"
    ACADEMIC = "Academic Literature"


class FileType(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class DocumentStatus(str, enum.Enum):
    UPLOADED = "Uploaded"
    PARSED = "Parsed"
    FAILED = "Failed"


class SessionStatus(str, enum.Enum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"


class OverlapStatus(str, enum.Enum):
    POTENTIAL_DUPLICATE = "Potential Duplicate"
    NO_SIGNIFICANT_OVERLAP = "No Significant Overlap"


class PlannerDecision(str, enum.Enum):
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"
    FLAGGED = "Flagged"


def enum_column(enum_cls, name):
    """Portable enum stored as its human-readable value, with a CHECK constraint."""
    return sa.Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        length=32,
        values_callable=lambda e: [m.value for m in e],
    )
