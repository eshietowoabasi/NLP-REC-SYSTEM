# Design decisions

Decisions that the original specification left open, and choices made during the build.
Each has a one-line rationale. Changes agreed later are appended with the date.

## From the build brief

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | SBERT model `all-MiniLM-L6-v2` by default; the model name is a setting. | Fast on a laptop CPU with good semantic-similarity quality; can be swapped for `all-mpnet-base-v2` without code changes. |
| 2 | Cookie session auth (Flask-Login) + CSRF; same origin via Nginx (Docker) or the Vite proxy (local dev). | HttpOnly cookies keep credentials away from JavaScript; same origin avoids CORS and third-party-cookie problems. |
| 3 | Background jobs with RQ + Redis; progress by polling `GET /api/sessions/{id}` every 2–3 s. | Analysis takes tens of seconds and must not block HTTP workers; polling is simpler and more robust than websockets for this load. |
| 4 | Branched preprocessing: original-casing passages for NER, SBERT, BERTopic and evidence; a heavily normalised copy only for TF-IDF. | NER and transformer models rely on casing, punctuation and stop words; TF-IDF benefits from normalisation. A single linear pipeline would degrade one or the other. |
| 5 | Passages of 3–5 sentences (~100–200 words, configurable) are the unit of analysis, with document, page and position stored. | SBERT truncates long input; passages also give precise, citable evidence. |
| 6 | Parse and split each document once (ingestion job), store passages and embeddings, reuse across sessions. | Avoids repeating the slowest work and makes session runs fast and consistent. |
| 7 | Candidate topics are BERTopic topics over non-NUC passages only; topic −1 (outliers) is discarded. | The NUC core is the baseline being compared against, not a source of new topics. |
| 8 | Candidate embedding = L2-normalised mean of member passage embeddings. | A standard, cheap topic centroid in the same space as the passage embeddings. |
| 9 | Novelty = 1 − max cosine similarity to any NUC core passage (clipped to [0,1]); `max_sim > 0.80` → "Potential Duplicate". The closest NUC passage id is stored. | Max similarity catches a candidate duplicated by any single part of the core; storing the passage lets planners verify side by side. |
| 10 | Skill score = log1p(sum of document frequencies of the candidate's top skills), min-max normalised across candidates (all equal → 1.0). | Document frequency rewards skills demanded by many sources rather than one repetitive advert; log damps outliers. |
| 11 | Theme score = (topic passages / non-outlier passages) × mean topic probability, min-max normalised. | Combines how prevalent a theme is with how confidently passages belong to it. |
| 12 | Composite = 0.40·skill + 0.35·theme + 0.25·novelty (weights per session, sum 1.0 ± 0.001); top 20 kept; duplicates kept and badged. | Weights from the project specification; planners, not the system, decide on duplicates. |
| 13 | Titles auto-generated from top c-TF-IDF keywords; planners can edit (`auto_title` and `topic_title` stored separately). | Gives a readable default while preserving the machine output for audit. |
| 14 | `RecommendationEvidence` table with the top 8 representative passages per topic and a relevance score. | Makes every recommendation traceable to its sources. |
| 15 | Reports as PDF (primary, WeasyPrint) and DOCX (python-docx). | PDF for circulation; DOCX for committee editing. |
| 16 | Uploaded files stored on a Docker volume under UUID names; original filename kept in the DB. | Prevents path traversal and name collisions; files never served from a public path. |
| 17 | Documents used by a session cannot be hard-deleted (409), only archived; users are deactivated, never deleted. | Keeps past sessions and the audit trail reproducible. |
| 18 | Exactly one active NUC core version, uploaded by admins; each session records the version it used; sessions cannot run without one. | Results must be reproducible against a known baseline. |
| 19 | The 30% credit-unit allowance is an admin setting, null until set. | The figure varies by institution and programme; no number is assumed. |

## Made during the build

| Phase | Decision | Rationale |
|-------|----------|-----------|
| 0 | **Pydantic v2** (not Marshmallow) for request/response validation. | Type-hint based schemas match the typed backend and give clear validation errors for the 422 envelope. |
| 0 | Postgres image `pgvector/pgvector:pg16`; passage embeddings will use a pgvector `vector(dim)` column. | Official PostgreSQL 16 plus the pgvector extension; stores embeddings natively instead of float arrays. |
| 0 | Environment chosen by `APP_ENV` (`development`/`testing`/`production`); production refuses to start without a strong `SECRET_KEY`, `DATABASE_URL` and `REDIS_URL`. | `FLASK_ENV` is deprecated; failing fast prevents insecure deployments. |
| 0 | `GET /api/health` returns 200 when Postgres and Redis are reachable, otherwise 503 with per-service results. | Gives the UI, Docker and monitoring one reliable signal. |
| 0 | In Docker development, Nginx is the single entry point (`http://localhost:8080`): `/api` → Flask, everything else → Vite dev server (with HMR websocket). | Same origin as production, so cookie and CSRF behaviour is identical in development. |
| 0 | Frontend uses current majors: React 19, Vite 8, React Router 8, Tailwind 4, TypeScript 6, ESLint 10, Vitest 5; shadcn/ui on the Radix base. | Scaffolded with the official `create-vite` template so the versions are known to work together. |
| 0 | Branches: `main` (releases), `develop` (integration), `feature/<phase>`. | As specified in the brief. |
| 0 | Lightweight dev mode: `docker-compose.services.yml` runs only Postgres and Redis; the full `docker-compose.yml` `include`s it; both share the project name `nlprs`. | Lets the app run natively on slow machines, with one definition of each service and shared data volumes. |
| 0 | Backend tests use a separate `<db>_test` database on the same server, created automatically; the suite refuses any database not named `*_test`. SQLite is not used for tests. | The models need PostgreSQL features (JSONB, pgvector), and development data must never be touched. |
| 0 | Exact dependency pins everywhere: exact versions in `package.json` plus the committed npm lockfile; pip-tools lockfiles (`requirements*.txt`) compiled from `requirements*.in` for Python 3.11/Linux. | Reproducible builds for examiners and deployment. |
| 1 | The session cookie holds a per-user random `session_token`, not the user id. The token is rotated on password change, password reset and deactivation. | Those events then end every existing session of the user immediately, even though Flask's signed-cookie sessions are stored client-side. |
| 1 | Sessions last 8 hours. Logout clears the cookie; the token itself is not rotated at logout, so logging out on one device does not end the user's other sessions. | Standard behaviour for multi-device use; forced sign-out everywhere is available by resetting the password. |
| 1 | CSRF via Flask-WTF: the token lives for the whole session, is sent in `X-CSRFToken`, is rotated at login and logout (and returned in the response), and the frontend refreshes it and retries once on `CSRF_FAILED`. | Protects every state-changing request, including login, without making long-lived browser tabs fail. |
| 1 | Login accepts a username or an email, case-insensitively. Unknown users and wrong passwords get the same message, and bcrypt still runs for unknown users; "account deactivated" is only revealed after a correct password. | Prevents discovering which accounts exist by comparing messages or response times. |
| 1 | Passwords: at least 8 characters and at most 72 bytes (bcrypt's input limit; longer passwords are rejected, not silently truncated). bcrypt cost 12, and 4 in tests. | Meets the brief's minimum length and avoids bcrypt's silent truncation. |
| 1 | Admins cannot change their own role or deactivate themselves. | Guarantees at least one active admin always remains. |
| 1 | Enumerations are stored as VARCHAR with CHECK constraints, not native PostgreSQL enum types. | Adding a value later is a one-line migration. |
| 1 | `Passage.embedding` is a dimension-less pgvector `vector`, plus an `embedding_model` column. | The SBERT model is a setting; different models produce different dimensions, and mixed embeddings are detectable. Similarity is computed in Python over small sets, so no vector index (which needs a fixed dimension) is required. |
| 1 | Columns added beyond the brief: `users.session_token`, `passages.embedding_model`, `recommendations.topic_id` and `created_at`, `reports.error_message` and `completed_at`. | Needed for session invalidation, embedding provenance, traceability to BERTopic topics and report-job failures. |
| 1 | `skill_patterns.pattern` is JSONB holding either a phrase string (matched case-insensitively) or a spaCy token pattern list. Short, ambiguous names (Go, R, C) use token patterns that require a confirming next word, e.g. "Go developer". | One column supports both EntityRuler pattern styles, and avoids false matches such as "go to the office". |
| 1 | The seed data has 172 canonical skills (302 patterns including aliases) and 81 domain stop words; `flask seed` is idempotent. | Exceeds the ~150 skills asked for; re-running the seed is safe. |
| 1 | Rate limiting of login is left to Phase 6. | Follows the phase plan in the brief. |
| 1 | Tests build the `_test` database with the real Alembic migrations, and empty the tables after each test with DELETE. | The migrations themselves get tested; DELETE is much faster than TRUNCATE for small tables. |
| 1 | In Docker development, Nginx re-resolves container names through Docker's DNS, and the frontend container reinstalls `node_modules` automatically when `package-lock.json` changes. | Recreated containers and newly added packages then work without manual restarts or volume resets. |
