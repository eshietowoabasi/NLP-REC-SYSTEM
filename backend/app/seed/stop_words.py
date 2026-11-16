"""Starter domain stop words (seeded by ``flask seed``).

Words that are frequent in job adverts but say nothing about the skills demanded. They are
removed only from the TF-IDF text, in addition to the standard English stop-word list.
"""

from __future__ import annotations

# fmt: off
DOMAIN_STOP_WORDS: tuple[str, ...] = (
    # Recruitment vocabulary
    "candidate", "candidates", "applicant", "applicants", "apply", "application", "applications",
    "role", "roles", "position", "positions", "job", "jobs", "vacancy", "vacancies", "hiring",
    "recruit", "recruitment", "opportunity", "opportunities", "employer", "employee",
    "company", "organisation", "organization", "team", "teams", "salary", "benefits",
    "package", "competitive", "deadline", "cv", "resume", "email", "interview", "shortlisted",
    # Requirement boilerplate
    "experience", "experienced", "requirement", "requirements", "responsibility",
    "responsibilities", "ability", "able", "excellent", "strong", "good", "proven",
    "minimum", "preferred", "plus", "must", "required", "etc", "including", "work", "working",
    "year", "years", "successful", "highly", "knowledge", "understanding", "skill", "skills",
    # More requirement boilerplate, found in the real job-advert corpus (Phase 6). Words that
    # are part of skill names ("deep learning", "scrum master") are deliberately not listed.
    "ensure", "familiarity", "familiar", "proficiency", "proficient", "fluency", "fluent",
    "relevant", "advantage", "advantageous", "degree", "bachelor", "bsc", "hnd", "msc",
    "qualification", "qualifications", "certification", "certified", "demonstrate",
    "demonstrated", "desirable", "seek", "seeking", "verify", "understand", "identify",
    "related", "respect", "manner", "equivalent", "ideal", "ideally", "passionate",
    "motivated",
    # Work arrangements
    "full-time", "part-time", "contract", "remote", "hybrid", "onsite", "location",
    # Places (the corpus is Nigerian; location names are not skills)
    "lagos", "abuja", "port harcourt", "ibadan", "uyo", "akwa ibom", "nigeria", "nigerian",
)
# fmt: on
