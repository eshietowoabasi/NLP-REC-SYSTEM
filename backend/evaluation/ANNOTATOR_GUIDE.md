# Helping evaluate NLP-RS: a guide for annotators

NLP-RS reads job adverts and policy documents and suggests topics for new university courses.
To check how well it works, we compare what it finds with what people find. **You do not need
any computing or AI knowledge.** Each task takes about an hour. Work on your own, and send the
file back when you finish.

## Before you start

- Open the spreadsheet you were sent in Excel or Google Sheets. Keep it as a **CSV** file when you
  save it, with the same name.
- **Hide the columns you must not look at** (right-click the column letter → Hide), as the task
  says below. They would influence your answers.
- Take a break every 30 minutes. If you are unsure about a row, give your best answer and write
  a short comment in the `notes` column.

## Task 1: Mark the skills in each extract

File: `ner_gold_…csv` (plus a list of skill names, `…_skills.csv`). Hide the columns
`predicted_skills` and the other annotator's column.

Each row has a short **extract** (a few sentences) from a job advert or a policy document, in the
`text` column. In **your column** (`annotator_a` or `annotator_b`, you will be told which):

1. List every **skill, tool, programming language or certification** the extract asks for or
   says is needed. Separate them with a semicolon: `Python; Amazon Web Services; SQL`.
2. Use the name from the skill list when one fits ("AWS" → `Amazon Web Services`). If the skill
   is not in the list, write it as it appears in the text.
3. Count a general ability only when it is asked for ("excellent **communication skills**" →
   yes; "a dynamic team" → no).
4. If there are none, write a single dash: `-`.

| Extract (example) | Answer |
|---|---|
| "You will build REST APIs in Python and deploy them on AWS. CISSP is an advantage." | `REST APIs; Python; Amazon Web Services; CISSP` |
| "The Ministry will expand broadband access in rural areas by 2025." | `-` |

## Task 2: Is this topic already taught in the NUC core?

File: `overlap_pairs_…csv`. Hide the column `similarity`.

Each row pairs one **suggested topic** (its `theme` name, `theme_keywords` and an example in
`theme_passage`) with one **NUC core course** (`course_code`, `course_title`). In the `covered`
column write:

- `1` if a student who takes that NUC course would **already learn most of** what the topic is
  about (a new course on it would repeat that course);
- `0` if not, or if the course only touches on it.

Judge from the course title and what you know of the CCMAS curriculum. If you are unsure, write
`0` and explain in `notes`. The same topic appears in several rows, each time with a different
course: judge each pair on its own.

| Topic | NUC course | Answer |
|---|---|---|
| Software Testing and Quality Assurance | SEN 304 Software Testing & Quality Assurance | `1` |
| Digital Marketing | CYB 203 Cybercrime, Law and Countermeasures | `0` |

*Thank you. Your answers are used only to measure the system for a final-year project, and your
name does not appear in the results.*
