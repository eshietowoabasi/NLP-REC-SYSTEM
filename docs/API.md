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
