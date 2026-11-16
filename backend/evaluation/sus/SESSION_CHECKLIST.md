# Usability sessions: checklist for the observer

Each session takes about 30 minutes: 2 minutes of introduction, about 15 minutes of tasks, 5
minutes for the questionnaire and a short chat. Plan 5–8 participants (lecturers, HOD,
curriculum officers).

## A week before

- [ ] Book the participants and a quiet room; send them the date and a one-line description
      ("try a new tool for suggesting course topics; 30 minutes").
- [ ] Prepare a **fresh session for each participant**, so everyone starts with nothing
      reviewed: New Session → the same documents as the real-corpus session → name it
      "Usability – P01", "Usability – P02", … (about 2 minutes each).
- [ ] Create a **planner account** for each participant (or one shared test account), and check
      that it can sign in.
- [ ] Generate the task sheet and response sheet:
      `python -m evaluation.sus_eval template --session <id> --participants 8`, and adapt the
      session name on the task sheet if you use one session per participant.
- [ ] Print, per participant: the task sheet and `sus/questionnaire.md`, plus a consent note.

## On the day, before each participant

- [ ] Start the app (`start-demo.ps1`) and open http://localhost:5173 on the Dashboard.
- [ ] Sign out, clear the browser's downloads folder, and have a stopwatch ready.
- [ ] Check the participant's session has no decisions yet.

## During the session

- [ ] Read out: "We are testing the system, not you. There are no wrong answers. Please say
      what you are thinking as you go. I can't help unless you are stuck for more than two
      minutes."
- [ ] Ask for consent (voluntary, anonymous, can stop at any time); give a participant number.
- [ ] Start the stopwatch; hand over the task sheet.
- [ ] For each task, note **done (1) / not done (0)**, where they hesitated, and anything they
      said about it. Do not explain the screens.
- [ ] If they are stuck for two minutes, give a hint and mark that task **0**.
- [ ] Stop the stopwatch after task 5; note the total minutes.

## Straight afterwards

- [ ] Hand over the questionnaire; ask them to answer every item quickly (tick 3 if unsure).
- [ ] Ask two questions and write down the answers: "What was most useful?" "What was most
      confusing?"
- [ ] Thank them.
- [ ] Enter the row in the response sheet: participant number, role, date, q1–q10 (1–5),
      task1–task5 (1/0), minutes, comments. Keep names out of the file.

## After all sessions

- [ ] `python -m evaluation.sus_eval score results/sus_responses_<stamp>.csv`
- [ ] Keep the paper questionnaires and the response sheet private (they stay out of the
      repository, like everything in `evaluation/results/`).
