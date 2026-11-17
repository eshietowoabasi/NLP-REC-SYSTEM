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


class NucDiscipline(StrEnum):
    """The 17 disciplines of the NUC Core Curriculum and Minimum Academic Standards (CCMAS).

    A programme belongs to one; its skills list is the discipline's plus the general skills.
    """

    ADMINISTRATION_AND_MANAGEMENT = "administration_and_management"
    AGRICULTURE = "agriculture"
    ALLIED_HEALTH_SCIENCES = "allied_health_sciences"
    ARCHITECTURE = "architecture"
    ARTS = "arts"
    BASIC_MEDICAL_SCIENCES = "basic_medical_sciences"
    COMMUNICATION_AND_MEDIA_STUDIES = "communication_and_media_studies"
    COMPUTING = "computing"
    EDUCATION = "education"
    ENGINEERING_AND_TECHNOLOGY = "engineering_and_technology"
    ENVIRONMENTAL_SCIENCES = "environmental_sciences"
    LAW = "law"
    MEDICINE_AND_DENTISTRY = "medicine_and_dentistry"
    PHARMACEUTICAL_SCIENCE = "pharmaceutical_science"
    SCIENCES = "sciences"
    SOCIAL_SCIENCES = "social_sciences"
    VETERINARY_MEDICINE = "veterinary_medicine"


NUC_DISCIPLINE_NAMES: dict[NucDiscipline, str] = {
    NucDiscipline.ADMINISTRATION_AND_MANAGEMENT: "Administration and Management",
    NucDiscipline.AGRICULTURE: "Agriculture",
    NucDiscipline.ALLIED_HEALTH_SCIENCES: "Allied Health Sciences",
    NucDiscipline.ARCHITECTURE: "Architecture",
    NucDiscipline.ARTS: "Arts",
    NucDiscipline.BASIC_MEDICAL_SCIENCES: "Basic Medical Sciences",
    NucDiscipline.COMMUNICATION_AND_MEDIA_STUDIES: "Communication and Media Studies",
    NucDiscipline.COMPUTING: "Computing",
    NucDiscipline.EDUCATION: "Education",
    NucDiscipline.ENGINEERING_AND_TECHNOLOGY: "Engineering and Technology",
    NucDiscipline.ENVIRONMENTAL_SCIENCES: "Environmental Sciences",
    NucDiscipline.LAW: "Law",
    NucDiscipline.MEDICINE_AND_DENTISTRY: "Medicine and Dentistry",
    NucDiscipline.PHARMACEUTICAL_SCIENCE: "Pharmaceutical Science",
    NucDiscipline.SCIENCES: "Sciences",
    NucDiscipline.SOCIAL_SCIENCES: "Social Sciences",
    NucDiscipline.VETERINARY_MEDICINE: "Veterinary Medicine",
}


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
