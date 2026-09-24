# API reference

Base path: `/api`. JSON in and out, except document uploads (multipart) and
report downloads (files).

**Authentication.** Sign in with `POST /api/auth/login`. The session is kept in
an `HttpOnly`, `SameSite=Lax` cookie that lasts 8 hours (`Secure` in
production). Browsers must send state-changing requests from the app's own
origin; others are refused with `403 CSRF_ORIGIN_MISMATCH`.

**Roles** (spec §14):
- **Admin:** everything.
- **Curriculum Planner** ("Planner" below): upload documents, create and run
  sessions, and review, map and report on their own sessions.
- **Viewer:** read-only.

"Owner" means the user who created the session.

**Errors** always have this shape:

```json
{"success": false, "error": {"code": "VALIDATION_ERROR", "message": "…", "details": {"field": "problem"}}}
```

| HTTP | Typical codes |
|---|---|
| 401 | `UNAUTHORIZED`, `INVALID_CREDENTIALS` |
| 403 | `FORBIDDEN`, `CSRF_ORIGIN_MISMATCH` |
| 404 | `NOT_FOUND` |
| 409 | `CONFLICT`, `DUPLICATE_DOCUMENT`, `DOCUMENT_IN_USE`, `SESSION_NOT_RUNNABLE`, `SESSION_PROCESSING`, `NO_CORE_REFERENCE`, `RESULTS_NOT_READY`, `NOT_PARSED`, `NOT_ACCEPTED`, `MAPPING_EXISTS`, `COURSE_CODE_IN_USE`, `USER_EXISTS` |
| 413 | `PAYLOAD_TOO_LARGE` |
| 415 | `UNSUPPORTED_FILE_TYPE` |
| 422 | `VALIDATION_ERROR`, `JUSTIFICATION_REQUIRED` |
| 429 | `ACCOUNT_LOCKED` (5 failed logins within 15 minutes) |
| 503 | `QUEUE_UNAVAILABLE` |

**Pagination.** List endpoints take `?page=` and `?per_page=` (at most 100)
and return
`{"items": [...], "pagination": {"page", "per_page", "total", "pages"}}`.

---

## Health and authentication

| Method | Path | Access | Notes |
|---|---|---|---|
| GET | `/api/health` | public | `{"status": "ok", "database": "ok"}`; returns 503 if the database is down |
| POST | `/api/auth/login` | public | `{"username", "password", "remember"?}` returns `{"user"}` |
| POST | `/api/auth/logout` | signed in | |
| GET | `/api/auth/me` | signed in | The current user |
| GET | `/api/dashboard/summary` | signed in | Document and session counts, recent sessions, your pending reviews, `core_reference_available` |

## Documents (§7)

| Method | Path | Access | Notes |
|---|---|---|---|
| GET | `/api/documents` | signed in | Filters: `source_category`, `status` (`Uploaded`, `Parsed`, `Failed`), `q` (title search), `mine=1` |
| POST | `/api/documents` | Planner, Admin | Multipart: `file` (PDF/DOCX/TXT, ≤ 25 MB), `source_category`, optional `title`. Parsed immediately; returns 201 with `processing_status` `Parsed` or `Failed` plus `error_message`. Only Admins may use `NUC Core Reference`. |
| GET | `/api/documents/{id}` | signed in | Metadata |
| GET | `/api/documents/{id}/text` | signed in | `?view=raw\|clean` |
| DELETE | `/api/documents/{id}` | uploader or Admin | Returns 409 if the document is used by a session that is processing |

Source categories: `NUC Core Reference`, `Job Market Data`,
`Institutional Document`, `Policy Document`, `Academic Literature`.

## Analysis sessions (§6, §15)

| Method | Path | Access | Notes |
|---|---|---|---|
| GET | `/api/sessions` | signed in | Filters: `status`, `mine=1` |
| POST | `/api/sessions` | Planner, Admin | See the example below |
| GET | `/api/sessions/{id}` | signed in | Includes `document_ids`, `progress {stage, step, total_steps}`, `pipeline_info` (models, timings, counts, warnings) |
| DELETE | `/api/sessions/{id}` | owner or Admin | Not allowed while processing |
| POST | `/api/sessions/{id}/run` | owner or Admin | **202**; runs in the background. Allowed only from `Pending` or `Failed`, and needs a parsed NUC Core Reference in the library. |

```json
POST /api/sessions
{"session_name": "2026 Computing Curriculum Review",
 "document_ids": [12, 15, 19],
 "parameter_config": {"similarity_threshold": 0.80, "ner_weight": 0.40, "topic_weight": 0.35,
                      "novelty_weight": 0.25, "max_recommendations": 20}}
```

`parameter_config` is optional; unset values take the defaults shown. The
weights must sum to 1.0. A session can contain 1–50 documents, all `Parsed`.

The progress stages are `queued`, `parsing`, `preprocessing`, `keywords`,
`entities`, `embeddings`, `topics`, `overlap`, `scoring` and `saving`. A run
whose worker stops reporting for `STALE_RUN_MINUTES` (default 30) is marked
`Failed` automatically and can be retried.

## NLP results (session must be `Completed`, otherwise 409 `RESULTS_NOT_READY`)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/sessions/{id}/results` | Everything: `pipeline_info`, the corpus output, and the output for each document |
| GET | `/api/sessions/{id}/keywords` | TF-IDF `corpus_keywords` `[{term, score, document_frequency}]` and keywords per document |
| GET | `/api/sessions/{id}/entities` | `skill_demand` `[{text, label, mentions, document_frequency, document_ids}]` and entities per document. `?label=SKILL\|TOOL\|CERT\|ORG\|PRODUCT\|GPE` |
| GET | `/api/sessions/{id}/topics` | BERTopic topics `[{topic_id, label, keywords, size, distinct_passages, relevance, representative_passages, document_counts, source_category_counts}]` and topic shares per document |
| GET | `/api/sessions/{id}/similarity` | `similarity_threshold`, `core_document_ids`, and for each recommendation `max_similarity`, `novelty_score`, `overlap_status`, `core_matches` |

All of these are available to any signed-in user.

## Recommendations (§10, §13.1)

| Method | Path | Access | Notes |
|---|---|---|---|
| GET | `/api/sessions/{id}/recommendations` | signed in | Ranked. Filters: `overlap_status`, `decision` (`Accepted`, `Rejected`, `Flagged` or `pending`), `include_evidence=1` |
| GET | `/api/recommendations/{id}` | signed in | Includes `evidence`: topic, keywords, passages, documents, skills and `core_matches` |
| PATCH | `/api/recommendations/{id}` | owner or Admin | `{"topic_title"?, "topic_description"?}` |
| PATCH | `/api/recommendations/{id}/decision` | owner or Admin | `{"decision": "Accepted"\|"Rejected"\|"Flagged"\|null, "notes"?}`. Accepting a *Potential Duplicate* requires notes (422 `JUSTIFICATION_REQUIRED`). While a mapping exists, the decision can't change (409 `MAPPING_EXISTS`). |

```json
{"rec_id": 55, "rank": 1, "topic_title": "Cloud Computing and Kubernetes",
 "topic_description": "Theme found in 24 passages across 3 source document(s)…",
 "ner_score": 0.96, "topic_score": 1.0, "novelty_score": 0.92, "composite_score": 0.96,
 "max_similarity": 0.08, "overlap_status": "No Significant Overlap",
 "planner_decision": null, "planner_notes": null}
```

## Curriculum mapping (§16)

| Method | Path | Access | Notes |
|---|---|---|---|
| GET | `/api/recommendations/{id}/mapping` | signed in | Courses mapped from this recommendation |
| POST | `/api/recommendations/{id}/mapping` | owner or Admin | The recommendation must be Accepted. Body below; returns 201. |
| GET | `/api/mappings/{id}` | signed in | |
| PUT | `/api/mappings/{id}` | owner or Admin | Same body as POST |
| DELETE | `/api/mappings/{id}` | owner or Admin | |
| GET | `/api/sessions/{id}/mappings` | signed in | Every mapping in a session, ordered by course code |

```json
{"course_code": "CSC 413", "course_title": "Cloud Infrastructure and DevOps", "credit_units": 3,
 "prerequisites": ["CSC 201"], "learning_outcomes": ["Deploy containerised services on a public cloud"]}
```

Course codes are normalised (`csc413` becomes `CSC 413`) and must be unique
within a session. Credit units must be 1, 2 or 3. Each mapping needs 1–12
learning outcomes and up to 8 prerequisites.

## Reports (§16)

| Method | Path | Access | Notes |
|---|---|---|---|
| POST | `/api/sessions/{id}/reports` | Planner, Admin | `{"format": "pdf"\|"docx"}` (default pdf); returns 201 |
| GET | `/api/reports` | signed in | History. `?session_id=` filter. |
| GET | `/api/reports/{id}` | signed in | Metadata |
| GET | `/api/reports/{id}/download` | signed in | The file |

## Administration (Admin only)

| Method | Path | Notes |
|---|---|---|
| GET | `/api/admin/users` | `?q=` searches username and email |
| POST | `/api/admin/users` | `{"username", "email", "password" (≥ 8 chars), "role"?}` |
| PATCH | `/api/admin/users/{id}` | Any of `role`, `is_active`, `email`, `password`. You can't demote or deactivate yourself. |
| GET | `/api/admin/audit` | Filters: `user_id`, `action_type`, `entity_type`, `from`, `to` (ISO dates) |
