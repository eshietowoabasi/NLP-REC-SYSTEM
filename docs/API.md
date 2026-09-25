# API reference

Base path: `/api`. All requests and responses are JSON unless stated otherwise.

## Conventions

**Success envelope**

```json
{ "success": true, "data": { } }
```

**Error envelope**

```json
{
  "success": false,
  "error": { "code": "VALIDATION_ERROR", "message": "Human-readable message.", "details": {} }
}
```

| Status | `error.code` | Meaning |
|---|---|---|
| 400 | `BAD_REQUEST` | Malformed request (e.g. the body is not JSON) |
| 400 | `CSRF_FAILED` | Missing, invalid or expired CSRF token; fetch a new one and retry |
| 401 | `UNAUTHORIZED` | Not logged in (or the session has ended) |
| 401 | `INVALID_CREDENTIALS` | Login failed: wrong username/email or password |
| 403 | `FORBIDDEN` | Logged in, but the role does not allow this |
| 403 | `ACCOUNT_DEACTIVATED` | Correct password, but the account has been deactivated |
| 404 | `NOT_FOUND` | Unknown route or resource |
| 405 | `METHOD_NOT_ALLOWED` | Route exists but not for this HTTP method |
| 409 | `CONFLICT` | State conflict (e.g. username already taken, document in use) |
| 413 | `PAYLOAD_TOO_LARGE` | Request or file too large |
| 422 | `VALIDATION_ERROR` | Well-formed but invalid input; see *Validation errors* |
| 422 | `SELF_MODIFICATION` | An admin tried to change their own role or deactivate themselves |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Unexpected error (generic message; details are only in server logs) |
| 503 | `SERVICE_UNAVAILABLE` | A dependency (database, Redis) is unavailable |

### Validation errors

422 responses (and 409 conflicts on specific fields) list messages per field:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Some fields are invalid.",
    "details": { "fields": { "email": ["value is not a valid email address: ..."] } }
  }
}
```

Request bodies reject unknown fields and trim surrounding whitespace from strings.

### Pagination

List endpoints accept `?page=` (from 1, default 1) and `?per_page=` (1–100, default 20) and
return:

```json
{
  "success": true,
  "data": {
    "items": [ ],
    "pagination": { "page": 1, "per_page": 20, "total": 42, "pages": 3 }
  }
}
```

### Authentication, sessions and CSRF

- Sessions use an HttpOnly, `SameSite=Lax` cookie (`nlprs_session`; `Secure` in production)
  that lasts 8 hours.
- Every **state-changing request** (POST, PUT, PATCH, DELETE) must send the header
  `X-CSRFToken: <token>`. Get a token from `GET /api/auth/csrf`. Login and logout reset the
  session and return a new token in `data.csrf_token`, which replaces the old one.
- Changing or resetting a password, or deactivating a user, ends all of that user's existing
  sessions.
- Access is enforced on the server for every route. The *Access* line of each endpoint below
  lists the roles allowed: **public**, **any** (any signed-in user), or specific roles.

### User object

```json
{
  "id": 1,
  "username": "ada",
  "email": "ada@example.com",
  "full_name": "Ada Lovelace",
  "role": "planner",
  "is_active": true,
  "created_at": "2026-09-24T09:00:00+00:00",
  "last_login_at": "2026-09-24T10:15:00+00:00"
}
```

`role` is one of `admin`, `planner`, `viewer`. Password hashes and session tokens are never
returned.

---

## Health

### `GET /api/health`

Access: public. Reports whether the API can reach PostgreSQL and Redis.

**200 OK**

```json
{
  "success": true,
  "data": {
    "status": "ok",
    "version": "0.1.0",
    "checks": { "database": "ok", "redis": "ok" }
  }
}
```

**503 Service Unavailable** (at least one dependency is unreachable):

```json
{
  "success": false,
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "One or more backend services are unavailable.",
    "details": {
      "version": "0.1.0",
      "checks": { "database": "ok", "redis": "unavailable" }
    }
  }
}
```

---

## Auth

### `GET /api/auth/csrf`

Access: public. Returns a CSRF token for the current session.

**200** `{ "csrf_token": "IjNk..." }`

### `POST /api/auth/login`

Access: public (CSRF token required). Logs in with a username **or** email (case-insensitive).

```json
{ "identifier": "ada", "password": "••••••••" }
```

**200**, with the session cookie set:

```json
{ "user": { "...": "User object" }, "csrf_token": "new-token-for-this-session" }
```

Errors: `401 INVALID_CREDENTIALS` (same message for unknown users and wrong passwords),
`403 ACCOUNT_DEACTIVATED`, `422 VALIDATION_ERROR`. Every attempt, successful or not, is
recorded in the audit log.

### `POST /api/auth/logout`

Access: any. Ends the session. **200** `{ "csrf_token": "token-for-the-anonymous-session" }`

### `GET /api/auth/me`

Access: any. **200** returns the signed-in user (User object). **401** if not signed in.

### `POST /api/auth/change-password`

Access: any. Changes the signed-in user's password. The current session stays signed in; other
sessions of this user are ended.

```json
{ "current_password": "••••••••", "new_password": "at least 8 characters" }
```

**200** `{ "message": "Password changed." }`

Errors: `422 VALIDATION_ERROR` when `current_password` is wrong (reported on that field), the
new password is shorter than 8 characters or longer than 72 bytes, or it equals the current one.

---

## Admin: users

Users are never deleted; deactivate them instead.

### `GET /api/admin/users`

Access: admin. Paginated list of users, newest first.

| Query parameter | Meaning |
|---|---|
| `role` | `admin`, `planner` or `viewer` |
| `is_active` | `true` or `false` |
| `search` | Case-insensitive match on username, email or full name |
| `page`, `per_page` | Pagination |

**200** `{ "items": [User, ...], "pagination": { ... } }`

### `POST /api/admin/users`

Access: admin. Creates a user.

```json
{
  "username": "ada",
  "email": "ada@example.com",
  "full_name": "Ada Lovelace",
  "role": "planner",
  "password": "initial password, 8+ characters"
}
```

Usernames are 3–64 characters (letters, digits, `.`, `_`, `-`). Usernames and emails are stored
in lowercase.

**201** returns the User object. Errors: `409 CONFLICT` if the username or email is taken
(reported per field), `422 VALIDATION_ERROR`.

### `PATCH /api/admin/users/{id}`

Access: admin. Changes only the fields supplied:

```json
{
  "full_name": "New Name",
  "email": "new@example.com",
  "role": "viewer",
  "is_active": false,
  "new_password": "reset to this password"
}
```

- Deactivating a user or resetting their password ends all their sessions.
- Admins cannot change their own role or deactivate themselves (`422 SELF_MODIFICATION`), so
  at least one active admin always remains.
- Each kind of change is audited separately (`user.updated`, `user.role_changed`,
  `user.activated`, `user.deactivated`, `user.password_reset`); unchanged values are not audited.

**200** returns the updated User object. Errors: `404`, `409 CONFLICT` (email taken), `422`.

---

## Documents

Source documents for analysis. Every uploaded file is validated, stored under a random name and
processed in the background (text extraction → cleaning → passages → normalised text →
embeddings). The `processing_status` moves `uploaded → parsing → ready`, or to `failed` with an
`error_message` the uploader can act on (for example "No extractable text (scanned PDF). OCR is
not supported.").

### Document object

```json
{
  "id": 12,
  "title": "backend engineer advert",
  "original_filename": "backend_engineer-advert.pdf",
  "file_type": "pdf",
  "file_size": 48213,
  "source_category": "job_market",
  "processing_status": "ready",
  "error_message": null,
  "page_count": 2,
  "word_count": 812,
  "uploaded_at": "2026-09-24T10:00:00+00:00",
  "parsed_at": "2026-09-24T10:00:04+00:00",
  "uploaded_by": { "id": 2, "full_name": "Ada Lovelace" }
}
```

`source_category`: `job_market`, `institutional`, `policy`, `academic` (and `nuc_core`, which is
managed on the NUC core endpoints). `file_type`: `pdf`, `docx`, `txt`. `page_count` is null for
DOCX and TXT.

### `GET /api/documents`

Access: any. Paginated, newest first. NUC core documents are excluded unless
`category=nuc_core`; archived documents are excluded unless `status=archived`.

| Query parameter | Meaning |
|---|---|
| `category` | One source category |
| `status` | `uploaded`, `parsing`, `ready`, `failed` or `archived` |
| `search` | Case-insensitive match on title or original filename |
| `page`, `per_page` | Pagination |

**200** `{ "items": [Document, ...], "pagination": {...}, "category_counts": { "job_market": 3, "institutional": 0, "policy": 1, "academic": 2 } }`

`category_counts` counts non-archived library documents per category (ignoring the filters).

### `POST /api/documents`

Access: admin, planner. `multipart/form-data` with one or more `files` and exactly one
`categories` value per file (same order). Each file is checked on its own:

- extension `.pdf`, `.docx` or `.txt`, and content that really is that type (magic bytes);
- not empty and at most 25 MB;
- not identical (same SHA-256) to a document already in the library (archived ones excepted).

**201** when at least one file was accepted: `{ "accepted": [Document, ...], "rejected": [{ "filename": "photo.png", "reason": "Unsupported file type. Upload PDF, DOCX or TXT files." }] }`.
Accepted documents start in `uploaded` and are processed in the background.

**422** `VALIDATION_ERROR` when no file was accepted, with `details.rejected` as above.

### `GET /api/documents/{id}`

Access: any. The Document object plus `passage_count`, `preview` (the first 5 passages),
`sessions` (analysis sessions using the document: `id`, `session_name`, `status`, `created_at`)
and `is_nuc_core`.

### `GET /api/documents/{id}/passages`

Access: any. The document's passages in order, paginated (`per_page` up to 100, default 50):
`{ "items": [{ "id", "position", "page_number", "text" }], "pagination": {...} }`. `page_number`
is the PDF page of the passage's first sentence (null for DOCX/TXT).

### `GET /api/documents/{id}/file`

Access: any. Downloads the original file (`Content-Disposition: attachment` with the original
filename). Uploaded files are never served from a public path.

### `POST /api/documents/{id}/archive`

Access: admin, planner. Hides the document from the library and from new sessions; sessions that
already used it keep it. **409** while the document is still being processed, and for NUC core
documents.

### `DELETE /api/documents/{id}`

Access: admin, planner. Deletes the document, its passages and its file. **409** `CONFLICT` if any
analysis session uses it (`details.sessions` lists them; archive it instead), and for NUC core
documents.

---

## NUC core reference

The NUC CCMAS core (the fixed 70%) against which candidate topics are compared. Exactly one
version is active. A newly uploaded version becomes active automatically once its document has
been processed successfully; until then (or if processing fails) the previous version stays
active.

### NUC core version object

```json
{
  "id": 3,
  "version_label": "CCMAS 2023",
  "is_active": true,
  "created_at": "2026-09-24T09:00:00+00:00",
  "uploaded_by": { "id": 1, "full_name": "System Administrator" },
  "document": { "...": "Document object (source_category nuc_core)" }
}
```

### `GET /api/nuc-core`

Access: any (planners need to know whether sessions can run). **200**
`{ "active": Version | null, "latest": Version | null }`: `latest` is the most recent upload,
which may still be processing or may have failed.

### `GET /api/nuc-core/versions`

Access: any. Every version, newest first.

### `POST /api/nuc-core`

Access: admin. `multipart/form-data` with `file` and `version_label` (1–64 characters). The file
is validated as for documents. **201** returns the new (not yet active) version; **422** with
`details.fields.file` or `details.fields.version_label` otherwise.

---

## Analysis sessions

A session analyses a chosen set of ready library documents against the active NUC core and
produces ranked recommendations. Runs happen in the background: `run` and `retry` return
**202 Accepted** and the client polls `GET /api/sessions/{id}` (every 2–3 s) while
`status` is `processing`.

`status`: `pending` (created, not run) → `processing` → `completed` or `failed`.
`current_stage` while processing: `queued`, `validating`, `loading`, `keywords`, `skills`,
`embeddings`, `themes`, `overlap`, `scoring`; `completed` when done. After a failure it keeps the
stage that failed, and `error_message` explains why (for example "Too little text to discover
themes: 8 passages were found but at least 10 are needed. Add more documents to the session.").

### Session object (list item)

```json
{
  "id": 5,
  "session_name": "2026 review",
  "status": "processing",
  "current_stage": "themes",
  "progress_percent": 55,
  "created_by": { "id": 2, "full_name": "Ada Lovelace" },
  "document_count": 20,
  "recommendation_count": 0,
  "created_at": "2026-09-25T09:00:00+00:00",
  "started_at": "2026-09-25T09:00:02+00:00",
  "completed_at": null
}
```

The detail adds:

| Field | Meaning |
|---|---|
| `parameter_config` | Snapshot taken at creation: `weights` (`ner`, `topic`, `novelty`), `similarity_threshold`, `max_recommendations`, `min_topic_size`, `evidence_per_recommendation`, `sbert_model`, `spacy_model` |
| `stage_timings` | Seconds per stage of the last run, e.g. `{"themes": 4.2}` |
| `error_message` | Why the last run failed (null otherwise) |
| `nuc_core_version` | `{ "id", "version_label" }` the session was compared against (set when it runs) |
| `documents` | `[{ "id", "title", "source_category", "processing_status" }]` in processing order |
| `topic_count` | Number of themes found (null before a successful run) |

### `GET /api/sessions`

Access: any. Paginated, newest first. Filters: `status`, `search` (name).

### `GET /api/sessions/defaults`

Access: any. Values for the New Session form:
`{ "parameters": {...parameter_config defaults}, "max_documents": 50, "nuc_core_version": {...} | null }`.

### `POST /api/sessions`

Access: admin, planner.

```json
{
  "session_name": "2026 review",
  "document_ids": [12, 15, 18],
  "parameters": {
    "weights": { "ner": 0.4, "topic": 0.35, "novelty": 0.25 },
    "similarity_threshold": 0.8,
    "max_recommendations": 20
  },
  "run": true
}
```

`parameters` and each of its fields are optional (defaults are used). The weights must each be
0–1 and sum to 1.0 ± 0.001. Every document must exist, be `ready`, not be a NUC core document,
and appear once; at most `max_documents_per_session` (default 50) documents.
With `"run": true` the session is queued immediately.

**201** returns the session detail. Errors: `422 VALIDATION_ERROR` (problems listed under
`details.fields.document_ids` or the parameter field), `409 NO_NUC_CORE` when `run` is true and
there is no active NUC core.

### `GET /api/sessions/{id}`

Access: any. Session detail (see above). **404** if unknown.

### `POST /api/sessions/{id}/run`

Access: admin, planner. Queues a `pending` session. **202** with the session detail.
**409** `CONFLICT` if the session is not pending, or `NO_NUC_CORE`.

### `POST /api/sessions/{id}/retry`

Access: admin, planner. Clears the results of a `failed` session and queues it again. **202**.
**409** if the session has not failed, or `NO_NUC_CORE`.

### `DELETE /api/sessions/{id}`

Access: admin, planner. Deletes the session with its results, recommendations, decisions,
mappings and reports; documents are kept. **409** while the session is processing.

### What a completed run stores

- **Recommendations** (top `max_recommendations`, ranked by composite score): title, description,
  keywords, top skills, the three normalised scores, composite, `max_similarity`, overlap status,
  closest NUC core passage and up to `evidence_per_recommendation` evidence passages. Served by
  the recommendation endpoints below.
- **Session-level results** for the Evidence Dashboard: TF-IDF keywords (overall and per
  category), skill counts (mentions and document frequency), every discovered theme, and the
  overlap of every theme with the NUC core.

## Session results (Evidence Dashboard)

Access: any. All four return the stored result of a **completed** session:
**404** if the session is unknown, **409** `RESULTS_NOT_READY` otherwise.

### `GET /api/sessions/{id}/keywords`

```json
{
  "overall": [{ "term": "kubernetes", "score": 0.031, "passage_count": 12 }],
  "by_category": { "job_market": [...], "policy": [...] },
  "passage_count": 300
}
```

`?category=job_market` limits `by_category` to that category (**422** for an unknown one).
Terms come from the normalised text; `score` is the mean TF-IDF weight across passages.

### `GET /api/sessions/{id}/entities`

`{ "skills": [{ "name", "label", "mentions", "document_frequency", "by_category" }],
"passages_with_skills", "passage_count", "document_count" }`. `label` is SKILL, TOOL, LANGUAGE
or CERT; skills are ordered by document frequency, then mentions.

### `GET /api/sessions/{id}/topics`

`{ "topic_count", "outlier_passages", "modelled_passages", "topics": [...] }`. Each topic has
`topic_id`, `title`, `keywords` (`[{ "term", "weight" }]`), `size`, `document_count`,
`mean_probability`, `strength_raw`, `strength` (0–1) and `samples`
(`[{ "passage_id", "document_id", "document_title", "text" }]`). Every theme is listed, not only
the recommended ones.

### `GET /api/sessions/{id}/similarity`

`{ "threshold", "nuc_core_version": { "id", "version_label" }, "candidates": [...] }`, ranked
like the recommendations. Each candidate: `topic_id`, `title`, `max_similarity`, `novelty`,
`overlap_status`, `closest_nuc_passage` (`{ "id", "text", "page_number" }`).

## Recommendations

### Recommendation object

| Field | Notes |
|-------|-------|
| `id`, `session_id`, `rank`, `topic_id` | |
| `auto_title` | Generated title (never changes) |
| `topic_title`, `topic_description` | Editable by planners |
| `keywords` | `[{ "term", "weight" }]` (c-TF-IDF) |
| `skills` | `[{ "name", "label", "mentions", "document_frequency" }]` |
| `ner_score`, `topic_score`, `novelty_score` | 0–1, normalised across the session's themes |
| `composite_score` | Weighted sum with the session's weights |
| `max_similarity`, `overlap_status` | `"Potential Duplicate"` or `"No Significant Overlap"` |
| `planner_decision` | `accepted`, `rejected`, `flagged` or null |
| `planner_notes`, `decided_at`, `decided_by` (`{ "id", "full_name" }`) | Null while undecided |
| `has_mapping` | Whether the recommendation is mapped to a course |

### `GET /api/sessions/{id}/recommendations`

Access: any. Every recommendation of the session in rank order (not paginated: at most
`max_recommendations`, ≤ 100). Filters: `decision` = `all` (default), `undecided`, `accepted`,
`rejected`, `flagged`; `hide_duplicates=true`. Response:
`{ "items": [...], "counts": { "total", "reviewed", "undecided", "accepted", "rejected",
"flagged", "potential_duplicates" } }`; the counts always cover the whole session. **404** if
the session is unknown.

### `GET /api/recommendations/{id}`

Access: any. The recommendation object plus:

- `evidence`: `[{ "passage_id", "relevance_score", "text", "page_number", "position",
  "document": { "id", "title", "source_category" } }]`, most relevant first;
- `closest_nuc_passage`: `{ "id", "text", "page_number", "document_title", "version_label" }`
  or null;
- `session`: `{ "id", "session_name", "weights", "similarity_threshold" }` (for the formula);
- `mapping`: the course mapping or null.

### `PATCH /api/recommendations/{id}`

Access: admin, planner. `{ "topic_title"?, "topic_description"? }` (at least one; title 1–255,
description 1–5,000 characters). `auto_title` is kept. Audited as `recommendation.edited`.

### `PATCH /api/recommendations/{id}/decision`

Access: admin, planner. `{ "decision": "accepted" | "rejected" | "flagged" | null, "notes"? }`
(notes ≤ 2,000 characters). `null` clears the decision. Records who decided and when; audited
as `recommendation.decided`. **409** when the recommendation is mapped to a course and the new
decision is not `accepted` (remove the mapping first).

## Curriculum mapping

### Mapping object

`{ "id", "recommendation_id", "course_code", "course_title", "credit_units", "prerequisites",
"learning_outcomes", "created_by", "created_at", "updated_at" }`.

### `POST /api/recommendations/{id}/mapping`

Access: admin, planner.

```json
{
  "course_code": "CSC 419",
  "course_title": "Cloud Security Engineering",
  "credit_units": 3,
  "prerequisites": ["CSC 301"],
  "learning_outcomes": ["Secure cloud workloads", "Operate Kubernetes clusters"]
}
```

- `course_code`: 2–4 letters and 3 digits (optional trailing letter); normalised to upper case
  with one space (`csc419` → `CSC 419`); unique within the session (**409** with
  `details.fields.course_code`).
- `credit_units`: 1, 2 or 3.
- `prerequisites`: up to 10; `learning_outcomes`: 1–15; blanks dropped, duplicates rejected.

**201** with the mapping; audited as `mapping.created`. **409** if the recommendation is not
accepted or is already mapped.

### `GET /api/recommendations/{id}/mapping`

Access: any. **404** if the recommendation is not mapped.

### `PUT /api/mappings/{id}` · `DELETE /api/mappings/{id}`

Access: admin, planner. `PUT` takes the same body as `POST` (audited as `mapping.updated`);
`DELETE` removes the course (audited as `mapping.deleted`) and leaves the recommendation
accepted.

### `GET /api/sessions/{id}/curriculum`

Access: any. The proposed curriculum of a session:
`{ "session": { "id", "session_name" }, "courses": [mapping + "recommendation": { "id", "rank",
"topic_title", "composite_score", "overlap_status" }], "total_units", "credit_unit_allowance",
"remaining_units" }`. Courses are ordered by code; `credit_unit_allowance` and
`remaining_units` are null until an admin sets the allowance.

## Reports

Reports are generated by a background job from a completed session's stored results and its
current decisions and mappings. Files are stored under UUID names and served only by the
download endpoint.

### Report object

| Field | Notes |
|-------|-------|
| `id` | |
| `session` | `{ "id", "session_name" }` |
| `format` | `pdf` or `docx` |
| `sections` | Chosen sections, in report order |
| `status` | `queued`, `processing`, `completed` or `failed` |
| `error_message` | Why generation failed (null otherwise) |
| `file_size` | Bytes, once the file exists |
| `created_by`, `created_at`, `completed_at` | |

Sections: `corpus_summary`, `nlp_findings`, `overlap`, `recommendations`, `decisions`,
`proposed_courses`.

### `POST /api/sessions/{id}/reports`

Access: admin, planner. `{ "format": "pdf" | "docx", "sections": [...] }` (at least one
section, each once). **202** with the queued report; poll `GET /api/reports/{id}`. Audited as
`report.generated`. **404** unknown session; **409** `RESULTS_NOT_READY` if the session has not
completed.

A PDF report fails with "PDF generation is not available on this server" when WeasyPrint's
system libraries (Pango) are missing, e.g. natively on Windows; the Docker image includes them.

### `GET /api/reports`

Access: any. Paginated, newest first. Filters: `session_id`, `status`, `format`.

### `GET /api/reports/{id}`

Access: any. **404** if unknown.

### `GET /api/reports/{id}/download`

Access: any. The file as an attachment named
`NLP-RS report - <session> - <date>.<pdf|docx>`. **409** `REPORT_NOT_READY` until the report
has completed; **404** if the file is missing.

### `DELETE /api/reports/{id}`

Access: admin, planner. Deletes the report and its file; audited as `report.deleted`. **409**
while it is queued or being generated. Deleting a session also deletes its report files.

## Dashboard

### `GET /api/dashboard/summary`

Access: any.

```json
{
  "documents": { "total": 12, "ready": 10, "processing": 1, "failed": 1,
                 "by_category": { "job_market": 8, "policy": 4 } },
  "sessions": { "total": 3, "by_status": { "pending": 0, "processing": 1, "completed": 2, "failed": 0 } },
  "recommendations": { "total": 30, "pending_review": 18, "accepted": 7, "rejected": 3, "flagged": 2 },
  "courses_mapped": 4,
  "reports": 2,
  "nuc_core_version": { "id": 1, "version_label": "CCMAS 2023" },
  "recent_sessions": [ ...five newest session objects... ]
}
```

Documents exclude archived ones and the NUC core; recommendation counts cover completed sessions.

## Admin: settings

### `GET /api/admin/settings`

Access: admin. `{ "settings": [{ "key", "value", "default", "description", "updated_at",
"updated_by" }] }` for every key: `score_weights`, `similarity_threshold`,
`max_recommendations`, `passage_sentences`, `passage_words`, `sbert_model`, `spacy_model`,
`min_topic_size`, `evidence_per_recommendation`, `max_documents_per_session`,
`credit_unit_allowance`.

### `PUT /api/admin/settings`

Access: admin. Any subset of the settings; only the keys sent change.

| Key | Rule |
|-----|------|
| `score_weights` | `{ "ner", "topic", "novelty" }`, each 0–1, sum 1.0 ± 0.001 |
| `similarity_threshold` | 0 < value < 1 |
| `max_recommendations` | 1–100 |
| `passage_sentences` | `{ "min", "max" }`, 1–10, min ≤ max |
| `passage_words` | `{ "min", "max" }`, 20–500, min ≤ max |
| `sbert_model`, `spacy_model` | Model name (letters, digits, `. _ / -`); the spaCy pipeline must be installed |
| `min_topic_size` | 2–100 |
| `evidence_per_recommendation` | 1–20 |
| `max_documents_per_session` | 1–200 |
| `credit_unit_allowance` | 1–300, or `null` to clear |

Response: `{ "settings": [...], "changed": [keys whose value changed] }`. Changes are audited as
`settings.updated` with the old and new values. Scoring and analysis settings apply to
sessions created afterwards; passage size and models apply to documents uploaded afterwards.

## Admin: skill patterns

### Skill pattern object

`{ "id", "label", "pattern", "canonical_name", "is_active", "created_at" }`. `label` is SKILL,
TOOL, LANGUAGE or CERT; `pattern` is a phrase (matched case-insensitively) or a spaCy token
pattern (a list of 1–10 token objects).

### `GET /api/admin/skill-patterns`

Access: admin. Paginated, by canonical name. Filters: `label`, `is_active`, `search` (canonical
name or pattern text).

### `POST /api/admin/skill-patterns`

Access: admin. `{ "label", "pattern", "canonical_name" }`. Token patterns are validated by
spaCy; problems are returned under `details.fields.pattern` (e.g. "token 1 LOWERX: Extra inputs
are not permitted"). **409** if the same pattern (phrases compared case-insensitively) already
exists for the label. **201**; audited as `skill_pattern.created`.

### `PATCH /api/admin/skill-patterns/{id}`

Access: admin. Any of `label`, `pattern`, `canonical_name`, `is_active`. Same validation;
audited as `skill_pattern.updated`. Patterns are used by sessions run afterwards.

## Admin: stop words

### `GET /api/admin/stop-words`

Access: admin. Paginated, alphabetical. Filters: `is_active`, `search`.

### `POST /api/admin/stop-words`

Access: admin. `{ "word" }`: one word (letters, digits and `+ # . ' -`), stored in lower case.
**409** if it already exists. **201**; audited as `stop_word.created`.

### `PATCH /api/admin/stop-words/{id}`

Access: admin. `{ "is_active": true | false }`; audited as `stop_word.updated`.

Active stop words are removed at ingestion and again before TF-IDF and theme words in every
session run, so words added later take effect without re-uploading documents.

## Admin: audit log

### Audit entry object

`{ "id", "created_at", "user": { "id", "full_name" } | null, "action_type", "entity_type",
"entity_id", "detail", "ip_address" }`. `user` is null for anonymous actions such as failed
sign-ins.

### `GET /api/admin/audit-logs`

Access: admin. Paginated, newest first. Filters:

- `user_id`;
- `action`: one action (`auth.login`) or an area (`auth` selects every `auth.*` action);
- `entity_type`;
- `date_from`, `date_to`: `YYYY-MM-DD`, UTC days, inclusive (**422** if from > to).

The response also lists every recorded action type under `actions`.

### `GET /api/admin/audit-logs/export`

Access: admin. The same filters (no paging) as a UTF-8 CSV attachment, at most 100,000 rows:
`time_utc, user, username, action, entity_type, entity_id, detail, ip`. Cells that a
spreadsheet would treat as formulas are prefixed with `'`. The export itself is audited as
`audit_log.exported`.
