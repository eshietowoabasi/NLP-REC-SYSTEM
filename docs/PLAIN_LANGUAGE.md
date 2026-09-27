# Plain-language pass (Phase 6)

NLP-RS is used by lecturers and curriculum officers without a computing background. All
labels, help text, empty states and messages were rewritten in short, plain sentences with no
library names. The technical terms remain only in "Show calculation" (Recommendation Detail),
the admin "(advanced)" model settings, the documentation and DECISIONS.md.

## Terms

| Before (technical) | After (on screen and in reports) |
|---|---|
| theme | topic |
| passage | extract |
| skill demand | employer demand |
| theme strength | how often it comes up |
| novelty | how new it is (compared with the NUC core) |
| New (badge) | Not in NUC core |
| Potential Duplicate | May already be in NUC core |
| Flag / Flagged | Discuss later |
| Undecided | Not reviewed yet |
| Map to course / Curriculum Mapping | Design course |
| Proposed Curriculum | Proposed courses |
| Job market / Institutional / Policy / Academic | Job adverts / University documents / Policy documents / Academic papers |

## Main wording changes

| Screen | Before | After |
|---|---|---|
| Recommendation title | Project, English and Problem *(keyword lemmas)* | Course-style name when one fits, e.g. "Threat Intelligence and Vulnerability Management"; "Keywords: security, Threat Intelligence, Vulnerability Assessment, remediation…" underneath |
| Recommendation description | A theme found in 41 passages from 16 documents, centred on System, Networking, Technical, Maintain… Most representative passage: "…" | Why this is recommended: 16 of the 56 documents mention this area, mostly job adverts for roles such as "IT Specialist" and "…". Employers ask for skills in IT Support, Information Security, Linux… |
| Example quote | *(inside the description, no source)* | Example from a job advert (Threat Intelligence and Vulnerability Management Associate – Duplo, MyJobMag, Jul 2026): "…" |
| Evidence grouping | myjobmag_cybersecurity_threat-intelligence_…_2026-07-16 · Job market | Threat Intelligence and Vulnerability Management Associate – Duplo, job advert (MyJobMag, Jul 2026) |
| Recommendation Detail, rank line | Rank 1 · theme 0 | Recommendation #1 |
| Score help | Share of passages in the theme × how confidently they belong to it | How much of the material is about this topic (each document counts the same), and how clearly its extracts belong to it |
| Score help | 1 − the highest similarity to any NUC core passage | How different it is from the closest NUC core course. High means the NUC core does not teach it yet |
| Overlap card | Highest similarity 0.70 against a threshold of 0.80: no significant overlap with the NUC core | We compared this topic with every NUC core course. A topic more than 80% similar to a course may already be in the NUC core. Here, the NUC core does not seem to cover it |
| Recommendations intro | Candidate course topics ranked by composite score = 0.40 × skill demand + 0.35 × theme strength + 0.25 × novelty | Suggested topics, best first. Each has a score out of 100: employer demand counts for 40%, how often it comes up counts for 35% and how new it is counts for 25% |
| Recommendations filter | Hide potential duplicates | Hide topics that may already be in the NUC core |
| Recommendations, empty | The analysis completed but found no themes to recommend. Try a session with more documents or a smaller minimum theme size. | The analysis finished but found no topics to recommend. Try again with more documents. |
| Evidence tabs | Keywords · Skills · Themes · NUC overlap | Keywords · Skills · Topics · NUC core |
| Evidence, keywords | Top 20 terms by TF-IDF — Mean TF-IDF weight across 417 passages (normalised text: lower case, lemmas, stop words removed) | Top 20 words that stand out — Words that are common in some extracts but not everywhere, across 417 extracts. Everyday words are left out. |
| Evidence, topics | 31 themes discovered in 417 passages. 67 passages did not fit any theme | 28 topics found in 417 extracts. 67 extracts did not fit any topic and were left out |
| Evidence, NUC core | Highest cosine similarity between each theme and any passage of CCMAS 2023 | How similar each topic is, by meaning, to the closest course of CCMAS 2023 |
| Session stages | Validating · Embeddings ("Reusing stored SBERT embeddings") · Themes ("Discovering themes with BERTopic") · Overlap | Checking · Meaning ("Preparing the meaning of each extract") · Topics ("Grouping extracts into topics and naming them") · NUC core |
| New Session | The pipeline discovers themes in them and ranks candidate course topics against the NUC core. composite = w₁ × skill demand + w₂ × theme strength + w₃ × novelty | The system finds the topics they talk about, compares them with the NUC core and ranks them as possible new courses. The score adds up employer demand, how often the topic comes up and how new it is, weighted as below |
| Document Detail | Passages · Passage 3 · No passages were extracted. | Extracts · Extract 3 · No text could be read from this document. (plus Source, Original link, Published and "Edit details") |
| NUC Core page | Every candidate topic is compared against the active version to flag potential duplicates and measure novelty | Every suggested topic is compared with it, to spot topics that may already be in the NUC core |
| Settings | Minimum theme size — Passages needed to form a theme (BERTopic) | Smallest topic — How many extracts it takes to form a topic |
| Settings | Embedding model (SBERT) · spaCy pipeline | Meaning model (advanced) · Language model (advanced), with plain hints |
| Settings, skills | Patterns of the spaCy EntityRuler that recognise skills… | Words and phrases the system recognises as skills, tools, programming languages and certifications |
| Reports | Corpus summary · NLP findings · Overlap with the NUC core · Themes discovered (BERTopic) · Mean TF-IDF | Documents analysed · What the documents talk about · Comparison with the NUC core · Topics found · Weight |
| Report disclaimer | NLP-RS proposes candidate topics as decision support… | NLP-RS suggests topics to help the department decide. The suggestions and scores are worked out automatically from the documents; the decisions are made by the department's planners and the relevant university bodies. |

The full list of the 104 replacements made by the copy pass is reproducible from the commit
"Plain-language pass across the app".
