"""Usability study kit: a task sheet from a real session, a response sheet and SUS scoring.

    python -m evaluation.sus_eval template --session 10 [--participants 8]
    python -m evaluation.sus_eval score results/sus_responses_<stamp>.csv

``template`` writes (to evaluation/results/) a task sheet for participants that names real
topics of the session, and a response CSV with one row per participant (q1–q10 = the answers
1–5 to evaluation/sus/questionnaire.md, plus task completion and time). ``score`` computes each
participant's SUS score, the mean with SD and 95% CI, the adjective rating (Bangor et al.,
2009), and the task completion rate.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import select

from evaluation import metrics
from evaluation.common import (
    app_context,
    completed_session,
    read_csv,
    results_path,
    stamp,
    write_csv,
    write_json,
)

TASKS = 5
COLUMNS = [
    "participant",
    "role",
    "date",
    *[f"q{i}" for i in range(1, 11)],
    *[f"task{i}_completed" for i in range(1, TASKS + 1)],
    "minutes_total",
    "comments",
]


def make_template(session_id: int, participants: int) -> None:
    from app.extensions import db
    from app.models import Recommendation

    with app_context():
        session = completed_session(session_id)
        name = session.session_name
        recs = db.session.scalars(
            select(Recommendation)
            .where(Recommendation.session_id == session_id)
            .order_by(Recommendation.rank)
        ).all()
        if len(recs) < 3:
            raise SystemExit("The session needs at least three recommendations for the tasks.")
        first, second, third = recs[0], recs[1], recs[2]
        duplicate_note = sum(r.overlap_status.value == "Potential Duplicate" for r in recs)

    sheet = f"""# NLP-RS usability study: tasks

Session: **{name}** (session {session_id}). Sign in with the account you were given, then
work through the tasks in order. Think aloud if you can; the observer notes where you hesitate
but will not help unless you are stuck for more than two minutes. After the tasks, fill in the
questionnaire.

1. **Find the session.** From the Dashboard, open the session "{name}" and its
   Recommendations. *Done when the ranked list is on screen.*
2. **Understand a score.** Open the top recommendation, "{first.topic_title}". Say in your own
   words why it ranks first (which of its three scores is highest) and which NUC course it is
   closest to. *Done when you have stated both.*
3. **Decide.** Accept "{first.topic_title}", reject "{second.topic_title}" and mark
   "{third.topic_title}" to discuss later, adding a short note to one of them. *Done when the
   three decisions show on the list.*
4. **Design a course.** For "{first.topic_title}", design a course: a code (for example
   CSC 4xx), a title, credit units and at least two learning outcomes. *Done when the course
   shows on the recommendation.*
5. **Report.** Download the session report. *Done when the Word file has downloaded.*

({duplicate_note} of the session's recommendations are marked "Potential Duplicate" of NUC core
content.)
"""
    stem = f"session{session_id}_{stamp()}"
    tasks = results_path(f"sus_tasks_{stem}.md")
    tasks.write_text(sheet, encoding="utf-8")
    responses = write_csv(
        results_path(f"sus_responses_{stem}.csv"),
        COLUMNS,
        [[f"P{n:02d}", "", "", *[""] * (len(COLUMNS) - 3)] for n in range(1, participants + 1)],
    )
    print(
        f"Task sheet → {tasks}\nResponse sheet ({participants} participants) → {responses}\n"
        "Questionnaire: evaluation/sus/questionnaire.md. Enter q1–q10 as 1–5 and task columns as "
        f"1/0, then run: python -m evaluation.sus_eval score {responses}"
    )


def score(path: Path) -> None:
    rows = read_csv(path)
    participants = []
    tasks_done = tasks_total = 0
    for row in rows:
        answers = [(row.get(f"q{i}") or "").strip() for i in range(1, 11)]
        if not all(answers):
            continue  # not (fully) answered yet
        value = metrics.sus_score([int(a) for a in answers])
        completed = [(row.get(f"task{i}_completed") or "").strip() for i in range(1, TASKS + 1)]
        done = [c for c in completed if c in {"0", "1"}]
        tasks_done += sum(int(c) for c in done)
        tasks_total += len(done)
        participants.append(
            {"participant": row["participant"], "role": row.get("role"), "sus": value}
        )
    if not participants:
        raise SystemExit("No complete questionnaires yet (q1–q10 must all be filled).")
    summary = metrics.summarise([p["sus"] for p in participants])
    result = {
        "file": str(path),
        "participants": participants,
        "summary": summary,
        "adjective": metrics.sus_adjective(summary["mean"]),
        "above_average": summary["mean"] > 68,
        "task_completion_rate": tasks_done / tasks_total if tasks_total else None,
        "note": "68 is the average SUS score across studies (Sauro, 2011).",
    }
    out = write_json(results_path(f"sus_scores_{stamp()}.json"), result)
    ci = (
        f" (95% CI {summary['ci95_low']:.1f}–{summary['ci95_high']:.1f})"
        if summary["ci95_low"] is not None
        else ""
    )
    completion = result["task_completion_rate"]
    print(
        f"Participants: {summary['n']}\nMean SUS {summary['mean']:.1f}{ci}: "
        f"{result['adjective']}\n"
        + (f"Task completion: {completion:.0%}\n" if completion is not None else "")
        + f"Saved → {out}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    template = commands.add_parser("template", help="Write the task and response sheets")
    template.add_argument("--session", type=int, required=True)
    template.add_argument("--participants", type=int, default=8)
    scoring = commands.add_parser("score", help="Score the filled response sheet")
    scoring.add_argument("file", type=Path)
    args = parser.parse_args()
    if args.command == "template":
        make_template(args.session, args.participants)
    else:
        score(args.file)


if __name__ == "__main__":
    main()
