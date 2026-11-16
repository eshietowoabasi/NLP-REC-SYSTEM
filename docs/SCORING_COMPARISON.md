# Scoring revision: before/after comparison (Phase 6)

Approved by the project owner; recorded in [DECISIONS.md](DECISIONS.md) (Phase 6, "Skill demand
is specificity-weighted …"). Scores are shown out of 100, as in the application.

## What changed

| Score | Before | After |
|---|---|---|
| Skill demand | `log1p(Σ document frequency of the theme's top skills)`, min-max over all themes | `log1p(Σ document frequency × share of the skill's mentions that fall in this theme)`, min-max over the themes **that have skills**; themes without skills score 0 |
| Theme strength | document-weighted share × mean probability, min-max | the same value, **square root**, then min-max |
| Novelty, composite, weights | unchanged (0.40 / 0.35 / 0.25) | unchanged |

## Data

Real corpus of the dev database, session 9: the CCMAS 2023 NUC core, the NDEPS policy and 55
job adverts (56 documents, 417 passages, 31 themes, 67 outlier passages). Both columns use the
same themes and the same course-level overlap with generic courses excluded (86 of 118 CCMAS
courses compared), so only the scoring differs.

## Spread across all 31 themes (0–1)

| Score | Min | Q1 | Median | Q3 | Max |
|---|---|---|---|---|---|
| Skill demand, before | 0.00 | 0.42 | 0.84 | 0.94 | 1.00 |
| Skill demand, after | 0.00 | 0.07 | 0.60 | 0.84 | 1.00 |
| Theme strength, before | 0.00 | 0.00 | 0.15 | 0.27 | 1.00 |
| Theme strength, after | 0.00 | 0.03 | 0.34 | 0.48 | 1.00 |

Before, 20 of 31 themes had a skill score of 0.80 or more (common skills such as Agile, Linux,
SQL and communication lifted almost every theme), and the median theme strength was 0.15
because the largest theme set the maximum.

## Options considered

| Option | Effect on the real corpus | Outcome |
|---|---|---|
| A: min-max over themes with skills only | barely changes the ranking (`log1p` still compresses) | kept, combined with C |
| B: percentile rank of skill demand | spreads scores evenly but ignores gap sizes; generic themes stay high | rejected |
| C: specificity-weighted skill demand | specific themes rise; generic ones fall | **chosen (with A)** |
| log scaling of theme strength | every theme looks strong (median 0.63); a theme with no skills enters the top 20 | rejected |
| rank scaling of theme strength | a 13-document theme overtakes the 16-document theme that it trails by a factor of 2.3 in size | rejected |
| square-root scaling of theme strength | median 0.34; the largest theme keeps #1 but its lead over #2 shrinks from 17 to 7 points | **chosen** |

## Top 20 before and after

"Was" gives the topic's rank before the change ("=" unchanged, "new" = not in the top 20 before).

| # | Before: topic | Score | Skill | Theme | Novelty | After: topic | Score | Skill | Theme | Novelty | Was |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | System, Networking and Technical | 85 | 98 | 100 | 42 | System, Networking and Technical | 82 | 90 | 100 | 42 | = |
| 2 | Testing Tool, Communication and Agile Methodologies | 68 | 100 | 44 | 49 | Testing Tool, Communication and Agile Methodologies | 75 | 100 | 64 | 49 | = |
| 3 | ITIL, Server and Cloud | 61 | 94 | 31 | 51 | Data Analysis, Education Business and Impact | 66 | 87 | 61 | 41 | #4 |
| 4 | Data Analysis, Education Business and Impact | 61 | 90 | 41 | 41 | React, Stack and .NET | 64 | 90 | 46 | 48 | #13 |
| 5 | Computer Science, System and Linux | 60 | 99 | 26 | 47 | Security, Vulnerability and Threat Intelligence | 61 | 89 | 49 | 36 | #14 |
| 6 | Project, English and Problem | 59 | 92 | 24 | 55 | Threat Intelligence, Vulnerability and Security | 61 | 90 | 53 | 26 | #11 |
| 7 | Product, Android and User | 58 | 90 | 28 | 50 | ITIL, Server and Cloud | 61 | 75 | 52 | 51 | #3 |
| 8 | Unix, Distribute System and Linux | 57 | 100 | 16 | 45 | Openshift Kubernetes, AWS and Cluster | 60 | 94 | 33 | 42 | #15 |
| 9 | Delivery, Product and Partner | 56 | 81 | 27 | 55 | DevOps, Infrastructure and Automation | 59 | 84 | 37 | 48 | #12 |
| 10 | Cloud, Container and Security DevOps | 55 | 97 | 15 | 45 | Computer Science, System and Linux | 58 | 74 | 47 | 47 | #5 |
| 11 | Threat Intelligence, Vulnerability and Security | 55 | 94 | 31 | 26 | Data Engineering, Power BI and Apache | 56 | 84 | 37 | 37 | #16 |
| 12 | DevOps, Infrastructure and Automation | 55 | 92 | 17 | 48 | Product, Android and User | 55 | 63 | 49 | 50 | #7 |
| 13 | React, Stack and .NET | 55 | 85 | 24 | 48 | Delivery, Product and Partner | 54 | 59 | 48 | 55 | #9 |
| 14 | Security, Vulnerability and Threat Intelligence | 54 | 89 | 27 | 36 | Project, English and Problem | 54 | 60 | 45 | 55 | #6 |
| 15 | Openshift Kubernetes, AWS and Cluster | 54 | 95 | 14 | 42 | Cloud, Container and Security DevOps | 53 | 74 | 34 | 45 | #10 |
| 16 | Data Engineering, Power BI and Apache | 50 | 87 | 17 | 37 | Unix, Distribute System and Linux | 50 | 66 | 35 | 45 | #8 |
| 17 | Data Engineering, Pl Pgsql and PostgreSQL | 48 | 84 | 10 | 46 | Data Engineering, Pl Pgsql and PostgreSQL | 48 | 70 | 26 | 46 | = |
| 18 | Growth, Customer and Product | 46 | 74 | 14 | 44 | Test Case, Defect and Execute | 32 | 26 | 33 | 42 | new |
| 19 | Government Interoperability, Digital Platform and Service Infrastructure | 41 | 73 | 0 | 48 | Information Security, Treaty and Protection | 29 | 50 | 3 | 32 | new |
| 20 | Digital Economy, Ministry Communications and Federal | 38 | 67 | 3 | 42 | Emerge Technology, Inclusion and Digital | 29 | 42 | 1 | 47 | new |

Left the top 20: Growth, Customer and Product; Government Interoperability, Digital Platform and
Service Infrastructure; Digital Economy, Ministry Communications and Federal. Entered: Test Case,
Defect and Execute; Information Security, Treaty and Protection; Emerge Technology, Inclusion and
Digital.

## Reading the change

- Themes built around specific, in-demand skills move up: React/.NET (#13 → #4), the two
  security themes (#14 → #5, #11 → #6), OpenShift/AWS (#15 → #8), Data Engineering/Power BI
  (#16 → #11).
- Themes whose skill score came from skills common to every advert move down: Unix/Linux
  (#8 → #16), Cloud/Container (#10 → #15), "Computer Science, System and Linux" (#5 → #10),
  "Project, English and Problem" (#6 → #14).
- The largest theme keeps first place, but its lead over #2 shrinks from 17 points to 7, so it no
  longer wins by default.
- The composite scores of the top 20 range from 29 to 82 (before: 38 to 85), so the ranking
  separates the themes more clearly.

The final real-corpus run after this change (with the same exclusions) is reported with the
evaluation results.

## Merging near-duplicate topics (Phase 6, later)

Session 10 showed the same topic twice: #5 "Security, Vulnerability and Threat Intelligence"
and #6 "Threat Intelligence, Vulnerability and Security". Topics whose centres (the mean
embedding of their extracts) are more similar than **0.83** are now merged after clustering
(average linkage, repeated until no pair is above the threshold); BERTopic then recomputes the
merged topic's words. Recorded in [DECISIONS.md](DECISIONS.md).

**Choosing the threshold.** On session 10 the most similar topic pairs were:

| Similarity | Pair | Merge at 0.83? |
|---|---|---|
| 0.847 | Digital Economy, Infrastructure and Regulation / Indigenous Digital, Pillar and Promote (policy) | yes |
| 0.842 | Threat Intelligence, Vulnerability and Security / Security, Vulnerability and Threat Intelligence | yes |
| 0.841 | Digital Economy, Ministry Communications and Federal / Digital Economy, Infrastructure and Regulation (policy) | yes |
| 0.813 | Government Interoperability… / Digital Economy, Infrastructure and Regulation (policy) | no |
| 0.798 | ITIL, Server and Cloud / Computer Science, System and Linux | no |
| 0.790 | Testing Tool, Communication and Agile / ITIL, Server and Cloud | no |

The median pair similarity is 0.45 and the 95th percentile 0.72. A threshold of 0.85 (as first
suggested) would have missed the security pair (0.842); 0.83 sits in the clear gap between
0.841 and 0.813. It merged two groups: the security pair, and three digital-economy topics from
the policy document (31 → 28 topics).

**Top 20 before and after** (both with the new scoring, the course exclusions and, after, the
course-style names and plain descriptions; scores out of 100):

| # | Before (session 10, 31 topics) | Score | After (session 13, 28 topics) | Score |
|---|---|---|---|---|
| 1 | System, Networking and Technical | 82 | IT Support and Help Desk Operations | 79 |
| 2 | Testing Tool, Communication and Agile Methodologies | 75 | Threat Intelligence and Vulnerability Management | 73 |
| 3 | Data Analysis, Education Business and Impact | 67 | Testing Tools, Communication and Agile Methodologies | 72 |
| 4 | React, Stack and .NET | 64 | Data Analysis, Education Business and Impact | 64 |
| 5 | Security, Vulnerability and Threat Intelligence | 61 | Full-Stack Web Development | 61 |
| 6 | Threat Intelligence, Vulnerability and Security | 61 | IT Service Management (ITIL) | 59 |
| 7 | ITIL, Server and Cloud | 61 | Cloud Infrastructure and Services | 57 |
| 8 | Openshift Kubernetes, AWS and Cluster | 60 | DevOps and Continuous Delivery | 56 |
| 9 | DevOps, Infrastructure and Automation | 59 | Computer Science, System and Linux | 56 |
| 10 | Computer Science, System and Linux | 58 | Data Engineering and Data Pipelines | 54 |
| 11 | Data Engineering, Power BI and Apache | 56 | Mobile Application Development | 53 |
| 12 | Product, Android and User | 55 | Agile Software Development | 53 |
| 13 | Delivery, Product and Partner | 54 | Project, English and Problem | 52 |
| 14 | Project, English and Problem | 54 | Cloud, Container and Security DevOps | 50 |
| 15 | Cloud, Container and Security DevOps | 53 | Linux System Administration | 48 |
| 16 | Unix, Distribute System and Linux | 50 | Data Engineering, Pl Pgsql and PostgreSQL | 46 |
| 17 | Data Engineering, Pl Pgsql and PostgreSQL | 49 | Software Testing and Quality Assurance | 31 |
| 18 | Test Case, Defect and Execute | 32 | Digital Marketing | 28 |
| 19 | Information Security, Treaty and Protection | 29 | Digital Economy and Policy | 27 |
| 20 | Emerge Technology, Inclusion and Digital | 29 | Cyber Law and Data Protection | 27 |

The merged security topic (8 documents, 21 extracts) rises from #5/#6 to **#2 (73)**: combined,
it covers more of the corpus (how often it comes up 75, was 49/53). Titles on the right are
course-style names where one was close enough (25 of 28 topics; see DECISIONS.md), otherwise
keyword titles. The other rankings barely change; with three fewer topics, the ones that were
#21–#23 (marketing, policy) enter the list.
