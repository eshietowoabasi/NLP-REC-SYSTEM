"""Classify job titles into computing role families (allow-list) or reject them (deny-list).

Families are checked in the order below; the first family with a matching phrase wins, so more
specific families (cybersecurity, cloud/devops, database, QA) come before the broad software
family. Phrases match whole words in the lower-cased title ("ui/ux" and "c#" included).
A title that matches the deny-list is rejected unless it also matches a family phrase, e.g.
"Security Officer" is rejected but "Information Security Officer" is cybersecurity.
"""

from __future__ import annotations

import functools
import re

FAMILIES: dict[str, tuple[str, ...]] = {
    "cybersecurity": (
        "cyber",
        "cybersecurity",
        "information security",
        "security analyst",
        "security engineer",
        "security architect",
        "soc analyst",
        "soc engineer",
        "penetration tester",
        "pentester",
        "ethical hacker",
        "vulnerability",
        "appsec",
        "application security",
        "iam engineer",
        "identity and access",
        "threat",
        "incident responder",
        "grc analyst",
        "it security",
        "network security",
        "cloud security",
        "security operations",
    ),
    "cloud_devops": (
        "devops",
        "devsecops",
        "cloud engineer",
        "cloud architect",
        "cloud administrator",
        "site reliability",
        "sre",
        "platform engineer",
        "kubernetes",
        "aws engineer",
        "azure engineer",
        "infrastructure engineer",
        "release engineer",
        "mlops",
    ),
    "database": (
        "database administrator",
        "database engineer",
        "database developer",
        "dba",
        "sql developer",
        "oracle dba",
        "data architect",
        "database",
    ),
    "qa": (
        "qa engineer",
        "qa analyst",
        "qa tester",
        "quality assurance engineer",
        "quality assurance analyst",
        "software tester",
        "test engineer",
        "test analyst",
        "test automation",
        "automation tester",
        "sdet",
        "manual tester",
    ),
    "data_ai": (
        "data scientist",
        "data analyst",
        "data engineer",
        "data science",
        "data analytics",
        "machine learning",
        "ml engineer",
        "ai engineer",
        "artificial intelligence",
        "business intelligence",
        "bi analyst",
        "bi developer",
        "analytics engineer",
        "nlp",
        "computer vision",
        "deep learning",
        "ai specialist",
        "big data",
        "power bi",
        "data annotator",
        "data management",
    ),
    "ui_ux": (
        "ui/ux",
        "ux/ui",
        "ui ux",
        "ux designer",
        "ui designer",
        "product designer",
        "user experience",
        "user interface",
        "interaction designer",
        "ux researcher",
        "web designer",
    ),
    "product_agile": (
        "product manager",
        "product owner",
        "scrum master",
        "agile coach",
        "agile delivery",
        "delivery manager",
        "technical project manager",
        "it project manager",
        "digital product",
        "product lead",
        "technical program manager",
    ),
    "networking_systems": (
        "network engineer",
        "network administrator",
        "network technician",
        "network support",
        "systems administrator",
        "system administrator",
        "sysadmin",
        "systems engineer",
        "noc engineer",
        "linux administrator",
        "windows administrator",
        "it infrastructure",
        "telecommunications engineer",
        "voip engineer",
        "unix administrator",
        "unix",
        "linux",
    ),
    "it_support": (
        "it support",
        "help desk",
        "helpdesk",
        "service desk",
        "desktop support",
        "technical support",
        "it officer",
        "it technician",
        "ict officer",
        "ict support",
        "it administrator",
        "it specialist",
        "it assistant",
        "it executive",
        "it analyst",
        "application support",
        "it intern",
        "ict intern",
        "tech support",
        "it lead",
        "it manager",
    ),
    "software_dev": (
        "software engineer",
        "software developer",
        "developer",
        "programmer",
        "frontend",
        "front-end",
        "front end",
        "backend",
        "back-end",
        "back end",
        "full stack",
        "fullstack",
        "full-stack",
        "mobile engineer",
        "android",
        "ios",
        "flutter",
        "react",
        "angular",
        "node.js",
        "nodejs",
        ".net",
        "java",
        "python",
        "php",
        "golang",
        "laravel",
        "django",
        "wordpress",
        "web engineer",
        "solutions architect",
        "solution architect",
        "software architect",
        "blockchain",
        "embedded software",
        "firmware",
        "c#",
        "ruby",
        "salesforce developer",
        "odoo",
        "erp developer",
        "sap abap",
    ),
}

DENY: tuple[str, ...] = (
    "driver",
    "accountant",
    "accounting",
    "sales",
    "marketing",
    "marketer",
    "nurse",
    "doctor",
    "physician",
    "pharmacist",
    "teacher",
    "tutor",
    "lecturer",
    "chef",
    "cook",
    "cashier",
    "receptionist",
    "secretary",
    "front desk",
    "human resource",
    "hr ",
    "recruiter",
    "lawyer",
    "legal",
    "counsel",
    "administrative",
    "admin officer",
    "customer service",
    "customer care",
    "customer experience",
    "mechanic",
    "electrician",
    "plumber",
    "welder",
    "civil engineer",
    "mechanical engineer",
    "structural engineer",
    "chemical engineer",
    "petroleum",
    "mining",
    "auditor",
    "audit",
    "finance",
    "financial",
    "banker",
    "relationship manager",
    "logistics",
    "procurement",
    "supply chain",
    "security guard",
    "security officer",
    "security personnel",
    "cleaner",
    "housekeeper",
    "store keeper",
    "storekeeper",
    "warehouse",
    "production",
    "operations officer",
    "loan",
    "credit",
    "insurance",
    "real estate",
    "estate",
    "architect",
    "quantity surveyor",
    "surveyor",
    "agronomist",
    "farm",
    "hospitality",
    "waiter",
    "barista",
    "fashion",
    "tailor",
    "graphic designer",
    "video editor",
    "content writer",
    "copywriter",
    "social media",
    "brand",
    "business development",
    "business developer",
    "property",
    "curriculum developer",
)

_WORD = r"(?<![a-z0-9]){}(?![a-z0-9])"


@functools.cache
def _pattern(phrase: str) -> re.Pattern[str]:
    """Compiled once per phrase (the sitemap mode classifies tens of thousands of titles)."""
    return re.compile(_WORD.format(re.escape(phrase.strip())))


def _matches(phrase: str, title: str) -> bool:
    return _pattern(phrase).search(title) is not None


IT_WORDS = ("it", "ict", "information technology")

# Family phrases that are too general to outweigh a deny-list match
# ("Business Developer", "Real Estate Developer", "Customer Service Technical Support").
GENERIC: frozenset[str] = frozenset(
    {
        "developer",
        "technical support",
        "application support",
        "it officer",
        "digital product",
        "data management",
        "web designer",
        "product designer",
        "delivery manager",
        "java",
        "python",
        "react",
    }
)


def _normalise(title: str) -> str:
    return " ".join(title.lower().replace("–", "-").split())


def is_denied(title: str) -> bool:
    """Whether the title names a non-computing role."""
    text = _normalise(title) + " "
    return any(_matches(phrase, text) for phrase in DENY)


# Roles that are rejected even when a computing phrase matches: academic posts ("Lecturer II -
# Cyber Security") and sales roles ("Head of Sales - Cybersecurity Solutions") describe
# teaching or selling, not the skills demanded of practitioners.
STRONG_DENY: tuple[str, ...] = (
    "lecturer",
    "professor",
    "professors",
    "reader",
    "academic staff",
    "sales",
    "account manager",
    "business development",
)


def classify_title(title: str) -> str | None:
    """The role family of a job title, or None for non-computing roles."""
    text = _normalise(title)
    if any(_matches(phrase, text) for phrase in STRONG_DENY):
        return None
    denied = is_denied(title)
    for family, phrases in FAMILIES.items():
        matched = [phrase for phrase in phrases if _matches(phrase, text)]
        if not matched:
            continue
        if denied and all(phrase in GENERIC for phrase in matched):
            return None  # e.g. "Business Developer": only a generic word matched
        return family
    # Last resort: a title that names IT itself ("Information Technology Lead",
    # "Volunteer - IT & Digital Support") is IT support, unless it is a denied role.
    if not denied and any(_matches(word, text) for word in IT_WORDS):
        return "it_support"
    return None
