# Evaluation

Scripts that measure how well NLP-RS works, for the project write-up (brief §6). They read the
database configured in `.env` (the development database holds the real corpus) and never
change it. Run them from `backend/` in the virtualenv:

```bash
python -m evaluation.<script> ...
```

Everything they write goes to `evaluation/results/`, which is **git-ignored**: templates and
results can contain text from the collected corpus, which must not be committed. The metric
functions are in `metrics.py` and unit-tested in `tests/test_evaluation.py` (synthetic data).

| What | Script | Needs people? |
|---|---|---|
| Skill extraction: precision, recall, F1, Cohen's kappa | `ner_eval.py` | yes: two annotators |
| Topic quality: BERTopic vs LDA (C_v, UMass) | `topic_coherence.py` | no |
| NUC overlap: AUC-ROC, P/R/F1 at 0.80, threshold calibration | `overlap_eval.py` | yes: one or two annotators |
| Speed: synthetic 20 × 3,000 words, and the real session | `benchmark_pipeline.py`, `benchmark_session.py` | no |
| Usability: System Usability Scale (SUS) | `sus_eval.py` + `sus/questionnaire.md` | yes: participants |

Session 10 is the final real-corpus run ("Real corpus (final): specificity scoring, course
overlap, exclusions": 56 documents = CCMAS 2023 core, NDEPS policy, 55 job adverts; 417 extracts,
31 themes).

## 1. Skill extraction (NER)

```bash
python -m evaluation.ner_eval template --session 10          # 60 extracts, stratified by category
python -m evaluation.ner_eval score results/ner_gold_session10_<stamp>.csv
```

The template (already generated: `results/ner_gold_session10_20260927T183202Z.csv`, with the
skill list `…_skills.csv`) has one row per extract with the extractor's `predicted_skills`.

**Annotation guidelines**

1. Two people annotate **independently**: annotator A fills `annotator_a`, annotator B fills
   `annotator_b`. Do not look at each other's column (hide it) or, ideally, at
   `predicted_skills`.
2. List every **skill, tool, programming language or certification** the extract asks for or
   mentions as needed for the job, separated by `;`. Use the names in the skill list where one
   fits (e.g. "Amazon Web Services" for "AWS"); add other names as written. Write `-` when there
   are none.
3. Count generic abilities only if they are named as a requirement (e.g. "communication
   skills" yes, "a dynamic team" no).
4. Afterwards, agree on disagreements and write the agreed list in `adjudicated` (optional; if
   empty, annotator A's list is the reference).

**Output**: micro precision/recall/F1 over (extract, skill) pairs, a breakdown by type (SKILL,
TOOL, LANGUAGE, CERT; gold skills unknown to the extractor count as OTHER: these are coverage
gaps to add as skill patterns), the most missed and most wrongly found skills, and Cohen's kappa
between A and B (Landis & Koch: 0.61–0.80 substantial, above 0.80 almost perfect).

## 2. Topic quality: BERTopic vs LDA

```bash
python -m evaluation.topic_coherence --session 10 [--lda-runs 3]
```

Both models are scored on the same tokenised extracts (lemmas, stop words removed). BERTopic's
words are the stored c-TF-IDF keywords; LDA (Gensim, evaluation only) gets the same number of
topics, 20 passes, three seeds. C_v uses Gensim's CoherenceModel (Röder et al., 2015).

**Result on session 10 (27 Sep 2026)**: 417 extracts, 2,997 distinct tokens, 31 topics, top 10
words.

| Model | C_v (higher is better) | UMass (closer to 0 is better) |
|---|---|---|
| BERTopic (NLP-RS) | **0.726** | **−2.857** |
| LDA baseline (3 seeds) | 0.521 ± 0.041 | −3.282 |

## 3. NUC overlap (duplicate detection)

```bash
python -m evaluation.overlap_eval template --session 10      # 3 closest + 2 random courses per theme
python -m evaluation.overlap_eval score results/overlap_pairs_session10_<stamp>.csv
```

The template (already generated: `results/overlap_pairs_session10_20260927T183630Z.csv`) has
155 theme–course pairs (31 themes × the 3 most similar NUC courses + 2 random ones, shuffled),
each with the theme's keywords and a representative extract, the course, and the cosine
similarity. Only the 86 courses the session compares are used (general studies, SIWES, project
and seminar courses excluded).

**Labelling**: in `covered`, write `1` if the NUC course already teaches what the theme is about
(a course built on this theme would duplicate it), `0` if not. A second person may fill
`annotator_b` for an agreement check. Judge from the course title and your knowledge of CCMAS;
the similarity column may be hidden while labelling.

**Output**: AUC-ROC (how well the similarity separates covered from not covered), precision,
recall and F1 at the current 0.80 threshold, and a sweep of thresholds 0.40–0.95 with the one
giving the highest F1 (and Youden's J). If the calibrated threshold differs clearly from 0.80,
change it in Settings and record the change in `docs/DECISIONS.md`.

Current similarities on session 10 range from 0.45 to 0.74 for the closest course (no theme is
above 0.80), so the labels will show whether 0.80 is too strict for course-level comparison.

## 4. Speed

```bash
python -m evaluation.benchmark_pipeline                     # synthetic: 20 documents × ~3,000 words
python -m evaluation.benchmark_session --session 10 --runs 3
```

| Benchmark | Documents | Words | Extracts | Analysis time |
|---|---|---|---|---|
| Synthetic (25 Sep 2026, brief target ≤ 60 s) | 20 | 60,143 | 896 | within target (`meets_target: true`) |
| Real session 10 (27 Sep 2026) | 56 | 30,822 | 417 | cold 104.6 s, warm median 13.9 s |

"Cold" is the first analysis in a fresh process: it includes one-off UMAP/numba compilation
(the themes stage: 92.5 s cold, 3–6 s warm). The worker keeps its process, so later sessions run
warm. Laptop: Intel Core (Family 6 Model 142), Windows 11, Python 3.13, CPU only.

## 5. Usability (SUS)

```bash
python -m evaluation.sus_eval template --session 10 [--participants 8]
python -m evaluation.sus_eval score results/sus_responses_session10_<stamp>.csv
```

Kit: `sus/questionnaire.md` (the standard ten SUS items, printable), a task sheet generated from
session 10 (`results/sus_tasks_session10_20260927T183231Z.md`: find the session, explain a
score, decide on three topics, design a course, download the report) and a response sheet
(`results/sus_responses_…csv`).

**Procedure**: 5–8 participants (lecturers, HOD, curriculum officers); a two-minute
introduction, then the tasks without help (the observer records completion as 1/0 and the total
minutes), then the questionnaire. Enter the answers (1–5) in `q1`–`q10`.

**Output**: each participant's SUS score (0–100), the mean with SD and 95% confidence interval,
the adjective rating (Bangor et al., 2009: 68 is average, 73+ good, 85+ excellent) and the task
completion rate.
