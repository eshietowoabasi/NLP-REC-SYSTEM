"""SQLAlchemy ORM models. Importing this package registers every table on the metadata."""

from app.models.audit import AuditLog
from app.models.configuration import Setting, SkillPattern, StopWord
from app.models.document import Document, NucCoreVersion, Passage
from app.models.enums import (
    DocumentStatus,
    FileType,
    NLPResultType,
    OverlapStatus,
    PlannerDecision,
    ReportFormat,
    ReportStatus,
    SessionStatus,
    SkillLabel,
    SourceCategory,
    UserRole,
)
from app.models.recommendation import CurriculumMap, Recommendation, RecommendationEvidence
from app.models.report import Report
from app.models.session import AnalysisSession, DocumentSession, NLPResult
from app.models.user import User

__all__ = [
    "AnalysisSession",
    "AuditLog",
    "CurriculumMap",
    "Document",
    "DocumentSession",
    "DocumentStatus",
    "FileType",
    "NLPResult",
    "NLPResultType",
    "NucCoreVersion",
    "OverlapStatus",
    "Passage",
    "PlannerDecision",
    "Recommendation",
    "RecommendationEvidence",
    "Report",
    "ReportFormat",
    "ReportStatus",
    "SessionStatus",
    "Setting",
    "SkillLabel",
    "SkillPattern",
    "SourceCategory",
    "StopWord",
    "User",
    "UserRole",
]
