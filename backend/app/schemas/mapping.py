"""Validation for curriculum mappings (spec §11, §16)."""
import re

from ..models import ALLOWED_CREDIT_UNITS
from ..utils.errors import ValidationError

# NUC-style course codes: "CSC 413", "CYB401", "SEN 312L".
COURSE_CODE_RE = re.compile(r"^[A-Z]{2,4} ?\d{3}[A-Z]?$")
MAX_OUTCOMES = 12
MAX_PREREQUISITES = 8


def normalise_course_code(value: str) -> str:
    """'csc413' -> 'CSC 413' so the same course is never stored two ways."""
    compact = re.sub(r"\s+", "", value or "").upper()
    match = re.match(r"^([A-Z]{2,4})(\d{3}[A-Z]?)$", compact)
    return f"{match.group(1)} {match.group(2)}" if match else (value or "").strip().upper()


def validate_mapping(payload) -> dict:
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object")
    errors, data = {}, {}

    code = normalise_course_code(payload.get("course_code") if isinstance(payload.get("course_code"), str) else "")
    if not COURSE_CODE_RE.match(code):
        errors["course_code"] = "Use a course code such as 'CSC 413'"
    data["course_code"] = code

    title = payload.get("course_title")
    if not isinstance(title, str) or not title.strip():
        errors["course_title"] = "Required"
    elif len(title.strip()) > 255:
        errors["course_title"] = "At most 255 characters"
    data["course_title"] = title.strip() if isinstance(title, str) else ""

    units = payload.get("credit_units")
    if isinstance(units, bool) or units not in ALLOWED_CREDIT_UNITS:
        errors["credit_units"] = "Must be 1, 2 or 3"
    data["credit_units"] = units

    outcomes = payload.get("learning_outcomes", [])
    if not isinstance(outcomes, list) or not all(isinstance(o, str) for o in outcomes):
        errors["learning_outcomes"] = "Must be a list of strings"
    else:
        outcomes = [o.strip() for o in outcomes if o.strip()]
        if not outcomes:
            errors["learning_outcomes"] = "Add at least one learning outcome"
        elif len(outcomes) > MAX_OUTCOMES:
            errors["learning_outcomes"] = f"At most {MAX_OUTCOMES} learning outcomes"
        elif any(len(o) > 500 for o in outcomes):
            errors["learning_outcomes"] = "Each outcome must be at most 500 characters"
    data["learning_outcomes"] = outcomes if isinstance(outcomes, list) else []

    prerequisites = payload.get("prerequisites", [])
    if not isinstance(prerequisites, list) or not all(isinstance(p, str) for p in prerequisites):
        errors["prerequisites"] = "Must be a list of course codes"
    else:
        prerequisites = list(dict.fromkeys(normalise_course_code(p) for p in prerequisites if p.strip()))
        bad = [p for p in prerequisites if not COURSE_CODE_RE.match(p)]
        if bad:
            errors["prerequisites"] = f"Invalid course code(s): {', '.join(bad)}"
        elif len(prerequisites) > MAX_PREREQUISITES:
            errors["prerequisites"] = f"At most {MAX_PREREQUISITES} prerequisites"
        elif code in prerequisites:
            errors["prerequisites"] = "A course cannot be its own prerequisite"
    data["prerequisites"] = prerequisites if isinstance(prerequisites, list) else []

    if errors:
        raise ValidationError("Invalid curriculum mapping", details=errors)
    return data
