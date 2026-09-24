# Implementation Decisions

The developer guide (§21) lists details the source specification leaves open.
This log records how each one is resolved. **Status** is one of:

- **Decided**: implemented in the codebase.
- **Proposed**: the default the team will build towards unless someone objects before that sprint starts.
- **Open**: needs input from the project owner or supervisor.

| # | Gap (guide §21) | Resolution | Status |
|---|-----------------|------------|--------|
| D1 | SBERT checkpoint and embedding dimension | `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions), set with `SBERT_MODEL` and baked into the Docker image. The embedding backend can be swapped (`EMBEDDING_BACKEND=sbert\|hashing`). `hashing` is a deterministic lexical stand-in for tests and offline development, and every run that uses it carries a warning. `all-mpnet-base-v2` (768 dimensions) is the fallback if the §17.3 evaluation shows too little separation. Embeddings are stored as JSON float arrays. | Decided |
| D2 | Authentication mechanism | Server-side cookie session using Flask-Login. The cookie is `HttpOnly` and `SameSite=Lax`, and `Secure` in production. The Vue app and API share one origin behind Nginx, so no tokens are held in browser storage. Passwords are hashed with bcrypt. | Decided |
| D3 | Background jobs and progress transport | Celery with Redis (`worker` service). `POST /run` claims the session with a conditional update, so it can't be started twice, and returns 202. The frontend polls `GET /api/sessions/{id}` for `progress.stage`. If Redis is down, the session is put back to its previous status and the request returns 503 `QUEUE_UNAVAILABLE`. | Decided |
| D4 | 0–1 normalisation of the NER and topic scores | **NER score:** `log(1 + m) / log(1 + max m)`, where *m* is the number of SKILL/TOOL/CERT mentions in the candidate topic's passages, counting repeats. The log keeps one very large theme from flattening every other score. **Topic score:** `0.5 · passages / max passages + 0.5 · documents / max documents`, so a theme found across many sources outranks one repeated at length in a single document. BERTopic probabilities aren't used: they are per passage, and computing them costs HDBSCAN time. Both scores are relative to the session's candidates, and the database enforces 0–1 on every score column. | Decided |
| D5 | Human-readable topic titles | The top 3 non-overlapping c-TF-IDF terms, spelled as they most often appear in the source text (e.g. "CISSP, PyTorch, Cloud"). KeyBERTInspired was dropped because it needs BERTopic to hold its own embedding model, while we pass embeddings in. Planners will be able to rename topics during review (Sprint 5). | Decided |
| D6 | Dedicated Evidence table | Not in v1. Passages are stored in `nlp_results.topics` and `ner_entities` (JSON with `document_id` and character offsets). This will be revisited if the dashboard needs to query across passages. | Proposed |
| D7 | File storage | Files are stored on the local filesystem under `UPLOAD_FOLDER` (`data/raw` in development, a Docker volume at `/data/raw` in containers) and named with UUIDs rather than the uploaded filename. | Decided |
| D8 | Report formats | **Both PDF (reportlab) and DOCX (python-docx)**, generated from one format-neutral builder so the two always match. The report covers the §16 sections plus pipeline warnings. Reports are generated on request (they take about a second), stored under `REPORT_FOLDER`, and listed on the Reports page. If only one format is wanted, remove it from `RENDERERS`. | Decided (pending confirmation) |
| D9 | Retention, deletion and backup | Deleting a document removes the file and its session links. Nightly `pg_dump` and a backup of the uploads volume. The retention period is still to be agreed with the department. | Open |
| D10 | When documents are parsed and where the text is stored | Documents are parsed as soon as they are uploaded, so a broken file is marked `Failed` with a reason straight away instead of failing mid-analysis. The extracted text is stored in `documents.extracted_text`, which list endpoints never load. Preprocessing (spaCy) runs as part of the analysis pipeline and its output is not stored. | Decided |

## Other decisions made during implementation

### Evaluation, security and operations (Sprint 6)

- **Evaluation** is a CLI toolkit (`flask eval …`, `backend/app/evaluation/`) rather than part of the web app. It is run by the project team on collected data, and results are saved as JSON for the write-up.
  - NER is scored strictly (exact span and label) by default, with lenient (overlapping span) and document-level (entity names) modes for annotations without offsets.
  - Agreement between the two annotators is reported as pairwise F1 and token-level Cohen's kappa.
  - Targets are checked as "above" the spec values (P > 0.80, R > 0.75, F1 > 0.75).
  - The similarity evaluation reports AUC-ROC and the Youden-optimal threshold for calibrating the 0.80 default.
  - Topic evaluation compares C_v coherence and topic diversity against an LDA with the same number of topics.
  - The performance benchmark runs the real pipeline against a private in-memory database; it must never touch the configured one.
- **Cross-site request forgery** protection: requests that change data (POST/PUT/PATCH/DELETE) and carry an `Origin` or `Referer` header must come from the same host (or from `TRUSTED_ORIGINS`), combined with SameSite=Lax cookies. Scripts that send neither header are unaffected, and CSRF tokens aren't needed because the API only accepts JSON or multipart from the app itself.
- **Brute-force protection** counts `LOGIN_FAILED` audit entries per account since its last successful login. The limit is 5 per 15 minutes (`429 ACCOUNT_LOCKED`), and it holds across all API worker processes. Unknown usernames aren't counted: there is no account to protect, and counting them would reveal which usernames exist. Blocked attempts are logged as `LOGIN_BLOCKED` and don't extend the lockout.
- **Sessions** last 8 hours (`PERMANENT_SESSION_LIFETIME`). Flask-Login's `session_protection = "strong"` invalidates a session if the client's identity (IP or user agent) changes.
- **Production refuses to start** if `SECRET_KEY` is shorter than 32 characters or a known default, if `DATABASE_URL` is missing, or if `EMBEDDING_BACKEND` isn't `sbert`.
- **HTTPS** is terminated at Nginx (`docker/nginx-https.conf`: TLS 1.2/1.3, HSTS, CSP). Flask trusts the forwarded headers only when `BEHIND_PROXY=1`.
- **Backups:** nightly `pg_dump` plus an archive of uploads and reports (`scripts/backup.sh`, keeping 14 of each), with a confirmed restore script. D9 (the retention period) is still open.

### Mapping, reports and frontend (Sprint 5)

- **Only Accepted recommendations** can be mapped (`409 NOT_ACCEPTED`). Once a recommendation is mapped, its decision can't move away from Accepted until the mapping is deleted (`409 MAPPING_EXISTS`), which keeps the course-to-evidence trace intact (§16).
- **Course codes** must match `AAA 999[A]`, are normalised to upper case with one space, and are unique within a session. Credit units are 1–3, enforced in both the API and the database. Each mapping needs 1–12 learning outcomes and up to 8 prerequisites (course codes, not including the course itself).
- **Planners can rename recommendations** (D5); the change is audited with the old and new title.
- **A new `Report` table** records the session, author, format, file path and size. Reports are snapshots: they aren't regenerated when decisions change later.
- **Admin safety:** an Admin cannot remove their own Admin role or deactivate themselves, so the system can't be left without one. New passwords need at least 8 characters.
- **`pool_pre_ping`** is enabled on the database engine. The end-to-end suite surfaced errors on the first requests after the database was recreated, and a PostgreSQL restart in production would cause the same.
- **Frontend:** Vue 3 + Vite + Pinia + Bootstrap 5, with no UI component library. Authentication uses the session cookie on the same origin (D2). A 401 response sends the user to `/login?next=…`. Session pages poll every 2.5 s while a run is processing (D3).
- **Deployment:** the `frontend` image builds the app and serves it from Nginx, which also proxies `/api` to the backend, handles SPA fallback routing and sets basic security headers. HTTPS termination still needs to be added with the institution's certificate (Sprint 6).

### Recommendations (Sprint 4)

- **Candidates** are the session's BERTopic topics (Appendix C: `build_topic_candidates`). Outlier passages don't produce candidates. If topic modelling was skipped (too little text), the session completes with no recommendations and a warning.
- **The core reference** is every parsed NUC Core Reference document in the library, not just those in the session. The run endpoint refuses to start without one (`409 NO_CORE_REFERENCE`), so compute isn't wasted on a run that cannot finish. Core segments are text blocks of 3–60 words (longer blocks become sentence windows), which keeps course titles such as "CSC 421: Cloud Computing" as their own segments.
- **The threshold test** is `max_similarity > threshold` on the value rounded to 4 decimals (the precision the API reports), so float32 noise can't flip the status at exactly 0.80.
- **Potential duplicates** stay visible but rank after every novel candidate, and they count towards `max_recommendations`. Accepting one requires planner notes (`422 JUSTIFICATION_REQUIRED`), which puts §9's "should not proceed without planner review" into practice.
- **Decisions** can be made by the session owner or an Admin. Everyone else can read them. `null` clears a decision, and every change is audited with its previous and new value.
- **Evidence** (`recommendations.evidence`, JSON) holds the source topic, keywords, representative passages, document IDs, source-category counts, top skills and the closest core segments with their document titles. It gives the traceability required in §16. A separate Evidence table (D6) is still not needed.

### NLP pipeline (Sprint 3)

- **Topic modelling works on passages (sentences of 6+ words), not whole documents.** A session has at most 50 documents, far too few to cluster, but typically thousands of passages. Topic modelling is skipped (with a warning) below 30 passages.
- **Topic model settings:** UMAP uses `random_state=42` so topics are reproducible. HDBSCAN's `min_cluster_size` is max(5, 1% of passages). c-TF-IDF uses BM25 weighting with `reduce_frequent_words`. When there are 3 or more topics, terms found in more than 80% of them are dropped, which removes boilerplate. The vectoriser's `min_df` must stay at 1, because BERTopic counts it per topic, not per passage.
- **Duplicate passages** (boilerplate repeated across job adverts) are fitted once, then every copy is mapped back to that topic. Sizes and per-document counts include the copies, while representative passages are always distinct. Exact duplicates also made UMAP's neighbour search very slow.
- **Performance (§17.5, ≤ 60 s for 20 documents × ~3,000 words):** measured at **32 s** on 60k words and 4,534 passages with warm models on a 4-core sandbox. The breakdown is 4 s preprocessing, 9 s NER and 19 s topics, using the hashing embedder. SBERT couldn't be measured here because Hugging Face is blocked; MiniLM on CPU is expected to add roughly 6–15 s. UMAP uses `n_epochs=200`, 7× faster than the default 500 with identical clusters in our benchmark (ARI 1.0). The seeded UMAP runs single-threaded, which is the price of reproducible topics. Workers warm the models at startup (about 20 s once per process).
- **Topic relevance** (§8.6) is the topic's size divided by the largest topic's size. Source-category counts are stored so Sprint 4 can weight market and policy evidence.
- **NUC Core Reference documents** in a session are processed per document, but kept out of corpus keywords, skill demand and topics. A session with only core references fails with a clear reason.
- **Completed sessions can't be re-run.** Their results, and later the planner decisions, are kept; re-analysing means creating a new session. Failed sessions can be retried.
- **Storage:** corpus-level output (keywords, skill demand, topics with centroid embeddings) is stored in `analysis_sessions.corpus_results`. Run metadata (models, stage timings, counts, warnings) goes in `analysis_sessions.pipeline_info`. Per-document output goes in `nlp_results`, with the mean passage embedding as the document embedding. API responses never include embeddings.
- **NER patterns** are in `services/ner/patterns.py`. Acronyms and product names that are also ordinary words (`AI`, `Spark`, `Swift`, `Node`) are matched case-sensitively. `Go`, `R` and `C` match only when followed by words like "programming" or "language". Bare "compliance" is not matched because it is too common in legal text.
- **Gensim LDA baseline** (§8.5/§17.2) is part of the evaluation toolkit (`flask eval topics`), not the live pipeline. Planners only need BERTopic's output; LDA exists for the comparison in the write-up.
- **Stuck sessions:** each stage updates `heartbeat_at`. The `scheduler` service (Celery beat) runs every 5 minutes and marks runs with no heartbeat for `STALE_RUN_MINUTES` (default 30) as Failed with an explanation, so they can be retried. The same check is available as `flask fail-stale-runs`.

### Data model and documents (Sprints 1–2)

- **Recommendation.max_similarity**: stored in addition to `novelty_score` (which equals `1 − max_similarity`) so that overlap results can be audited and shown on the similarity endpoint.
- **Document diagnostics**: `original_filename`, `file_size` and `error_message` were added to `Document`, and `progress_stage` and `error_message` to `AnalysisSession`. These support the "failed documents are diagnosable" requirement (§7.2) and progress display (§15).
- **Document statuses**: `Uploaded`, `Parsed` and `Failed`. The specification lists statuses only for sessions.
- **Enums**: stored as their human-readable values in `VARCHAR` columns with `CHECK` constraints rather than native PostgreSQL enums. This makes migrations easier when values change.
- **Duplicate uploads**: a file identical to one already in the library (same SHA-256 hash, stored in `documents.content_hash`) is rejected with `409 DUPLICATE_DOCUMENT`. Counting the same job-advert dump twice would inflate TF-IDF and NER frequencies.
- **Document visibility**: every signed-in user can read every document and session, because the corpus is shared across the department. Planners can delete only their own uploads. Only Admins can upload or delete `NUC Core Reference` documents (§14).
- **Session inputs**: every document in a session must be `Parsed`. Duplicate IDs are removed, and the order given in the request becomes `processing_order`.
- **TF-IDF tokens**: only content-word parts of speech are kept (`NOUN`, `PROPN`, `VERB`, `ADJ` and `X`). spaCy's stop-word list misses modal verbs such as *shall*, which dominated the sample constitutions.
- **AuditLog.user_id**: nullable, so failed logins and system actions can still be recorded.
