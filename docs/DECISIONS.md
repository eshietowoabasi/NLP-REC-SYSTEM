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
