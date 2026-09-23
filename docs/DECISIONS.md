# Implementation Decisions

The developer guide (§21) lists details the source specification leaves open.
This log records how each one is resolved. **Status** is one of:

- **Decided**: implemented in the codebase.
- **Proposed**: the default the team will build towards unless someone objects before that sprint starts.
- **Open**: needs input from the project owner or supervisor.

| # | Gap (guide §21) | Resolution | Status |
|---|-----------------|------------|--------|
| D1 | SBERT checkpoint and embedding dimension | `sentence-transformers/all-MiniLM-L6-v2` (384-d): fast on CPU and well suited to the ≤ 60 s target for 20 documents. `all-mpnet-base-v2` (768-d) is the fallback if the evaluation in §17.3 shows too little separation. Embeddings are stored as JSON float arrays in `nlp_results.embedding`, so the schema works with either model; `pgvector` can be added later if similarity search moves into the database. | Proposed (storage: Decided) |
| D2 | Authentication mechanism | Server-side cookie session using Flask-Login. The cookie is `HttpOnly` and `SameSite=Lax`, and `Secure` in production. The Vue app and API share one origin behind Nginx, so no tokens are held in browser storage. Passwords are hashed with bcrypt. | Decided |
| D3 | Background jobs and progress transport | Celery with a Redis broker. The frontend polls `GET /api/sessions/{id}` (the `status` and `progress_stage` fields) every 2–3 s. A worker service and a Redis service will be added to `docker-compose.yml` in Sprint 3. | Proposed |
| D4 | 0–1 normalisation of the NER and topic scores | NER score: `log(1 + freq) / log(1 + max_freq)` across the candidates in a session, which keeps very frequent skills from swamping the rest. Topic score: the candidate's BERTopic probability divided by the session maximum (min–max scaling). Both are clipped to [0, 1]. The database enforces the 0–1 range on every score column. | Proposed |
| D5 | Human-readable topic titles | Take the top 3 c-TF-IDF terms of each BERTopic cluster and generate a title from them with KeyBERTInspired representation. Planners can edit the title before accepting a recommendation. | Proposed |
| D6 | Dedicated Evidence table | Not in v1. Passages are stored in `nlp_results.topics` and `ner_entities` (JSON with `document_id` and character offsets). This will be revisited if the dashboard needs to query across passages. | Proposed |
| D7 | File storage | Files are stored on the local filesystem under `UPLOAD_FOLDER` (`data/raw` in development, a Docker volume at `/data/raw` in containers) and named with UUIDs rather than the uploaded filename. | Decided |
| D8 | Report formats | PDF as the primary format, with DOCX as an optional second format. | Open |
| D9 | Retention, deletion and backup | Deleting a document removes the file and its session links. Nightly `pg_dump` and a backup of the uploads volume. The retention period is still to be agreed with the department. | Open |

## Other decisions made during implementation

- **Recommendation.max_similarity**: stored in addition to `novelty_score` (which equals `1 − max_similarity`) so that overlap results can be audited and shown on the similarity endpoint.
- **Document diagnostics**: `original_filename`, `file_size` and `error_message` were added to `Document`, and `progress_stage` and `error_message` to `AnalysisSession`. These support the "failed documents are diagnosable" requirement (§7.2) and progress display (§15).
- **Document statuses**: `Uploaded`, `Parsed` and `Failed`. The specification lists statuses only for sessions.
- **Enums**: stored as their human-readable values in `VARCHAR` columns with `CHECK` constraints rather than native PostgreSQL enums. This makes migrations easier when values change.
- **AuditLog.user_id**: nullable, so failed logins and system actions can still be recorded.
