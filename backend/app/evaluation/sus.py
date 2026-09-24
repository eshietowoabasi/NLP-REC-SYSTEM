"""System Usability Scale analysis for UAT (spec §17.4): target mean >= 70."""
import csv

from .metrics import describe, sus_score

TARGET_MEAN = 70
ITEMS = [f"q{i}" for i in range(1, 11)]


def load_sus_csv(path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in ITEMS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"SUS CSV needs columns respondent_id, q1..q10; missing {', '.join(missing)}")
        return list(reader)


def evaluate_sus(rows: list[dict]) -> dict:
    respondents, errors = [], []
    for i, row in enumerate(rows, start=2):  # header is line 1
        try:
            answers = [int(row[q]) for q in ITEMS]
            respondents.append({"respondent_id": row.get("respondent_id") or f"row{i}", "sus": sus_score(answers)})
        except (ValueError, TypeError) as exc:
            errors.append(f"line {i}: {exc}")
    if errors:
        raise ValueError("Invalid SUS responses:\n" + "\n".join(errors))
    stats = describe([r["sus"] for r in respondents])
    warnings = []
    if not 5 <= len(respondents) <= 10:
        warnings.append(f"The UAT plan expects 5-10 participants; found {len(respondents)}.")
    return {
        **stats,
        "target_mean": TARGET_MEAN,
        "meets_target": stats.get("mean", 0) >= TARGET_MEAN,
        # Bangor et al. (2009) adjective scale, for interpretation in the write-up.
        "grade": _grade(stats.get("mean", 0)),
        "respondents": respondents,
        "warnings": warnings,
    }


def _grade(mean):
    for limit, label in ((85, "Excellent"), (72, "Good"), (52, "OK"), (38, "Poor")):
        if mean >= limit:
            return label
    return "Awful"
