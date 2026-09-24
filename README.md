# NLP-Driven Curriculum Recommendation System (NLP-RS)

This web application analyses job adverts, policy documents, institutional
materials and academic literature, and recommends topics for the **NUC CCMAS
30% localised curriculum**. Each candidate topic is checked for semantic
overlap with the NUC-prescribed 70% core.

The case study is the Department of Computer Science, Faculty of Computing,
University of Uyo.

- Developer guide: [`docs/NLP_RS_Developer_Documentation.docx`](docs/NLP_RS_Developer_Documentation.docx)
- Implementation decisions for the gaps listed in guide §21: [`docs/DECISIONS.md`](docs/DECISIONS.md)

## Status

| Sprint | Scope | State |
|--------|-------|-------|
| 1 | Project setup, database foundation, auth, RBAC, audit, error model | ✅ Done |
| 2 | Document upload, validation, parsing, preprocessing, session creation | ✅ Done |
| 3 | TF-IDF, NER, SBERT, BERTopic, background jobs, results APIs | ✅ Done |
| 4 | Semantic overlap and recommendation engine | ⏳ Next |
| 5 | Remaining APIs, Vue dashboard, mapping, reports | — |
| 6 | Evaluation, security hardening, deployment | — |

## Stack

Python 3.11 · Flask · SQLAlchemy / Alembic · PostgreSQL · Celery + Redis ·
spaCy · scikit-learn · Sentence-Transformers · BERTopic · Vue.js + Bootstrap 5
(planned) · Docker Compose · Nginx

## Local development

Requirements: Python 3.11 and PostgreSQL 16 (or Docker).

```bash
python3.11 -m venv .venv && source .venv/bin/activate
cd backend
pip install torch --index-url https://download.pytorch.org/whl/cpu   # CPU-only torch
pip install -r requirements-dev.txt
cp .env.example .env            # then edit DATABASE_URL / SECRET_KEY

createdb nlprs                  # or use the postgres container below
flask db upgrade                # apply migrations
flask create-user --username admin --email admin@example.com --role Admin
flask run                       # http://127.0.0.1:5000/api/health
```

### Tests

```bash
cd backend
python -m pytest --cov=app                       # uses in-memory SQLite
TEST_DATABASE_URL=postgresql+psycopg2://... python -m pytest   # against PostgreSQL
```

CI (`.github/workflows/backend-tests.yml`) runs the migrations and the test
suite against PostgreSQL 16. It fails if coverage drops below 85%, the target
in guide §17.5.

### Background worker (local)

```bash
redis-server &                                   # or: docker run -p 6379:6379 redis:7
cd backend && celery -A celery_worker.celery worker --loglevel=info --concurrency=1
```

At startup each worker loads spaCy and SBERT and triggers UMAP's JIT
compilation. Without that warm-up, the first analysis in each worker takes
about 20 s longer.

Without internet access to Hugging Face, set `EMBEDDING_BACKEND=hashing` to
exercise the pipeline. The results are then lexical rather than semantic and
are flagged with a warning.

### Docker Compose

```bash
docker compose up --build
docker compose exec backend flask db upgrade
docker compose exec backend flask create-user
curl http://localhost:8080/api/health
```

## API (implemented so far)

All errors use the same shape:
`{"success": false, "error": {"code", "message", "details"}}`

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/api/health` | – | Liveness and database check |
| POST | `/api/auth/login` | – | `{username, password, remember?}` → sets session cookie |
| POST | `/api/auth/logout` | any role | End the session |
| GET | `/api/auth/me` | any role | Current user |
| GET | `/api/documents` | any role | List documents. Filters: `source_category`, `status`, `q` (title search), `mine=1`. Paginated with `page` and `per_page`. |
| POST | `/api/documents` | Planner, Admin | Multipart upload with `file`, `source_category` and an optional `title`. The file is validated, stored and parsed immediately. |
| GET | `/api/documents/{id}` | any role | Document metadata, processing status and parse error |
| GET | `/api/documents/{id}/text` | any role | Extracted text. `?view=clean` applies the noise cleanup. |
| DELETE | `/api/documents/{id}` | owner or Admin | Delete a document and its file. Not allowed while a processing session uses it. |
| GET | `/api/sessions` | any role | List sessions. Filters: `status`, `mine=1`. |
| POST | `/api/sessions` | Planner, Admin | `{session_name, document_ids, parameter_config?}`: up to 50 documents, all of which must be parsed |
| GET | `/api/sessions/{id}` | any role | Session detail, including `document_ids` in processing order |
| DELETE | `/api/sessions/{id}` | owner or Admin | Delete a session. Not allowed while it is processing. |
| POST | `/api/sessions/{id}/run` | owner or Admin | Queue the NLP pipeline and return **202** at once. Allowed only from `Pending` or `Failed`. |
| GET | `/api/sessions/{id}/results` | any role | All NLP output: pipeline info, corpus results and per-document results |
| GET | `/api/sessions/{id}/keywords` | any role | TF-IDF keywords for the corpus and for each document |
| GET | `/api/sessions/{id}/entities` | any role | Skill demand and per-document entities. `?label=SKILL\|TOOL\|CERT\|ORG\|PRODUCT\|GPE` filters by type. |
| GET | `/api/sessions/{id}/topics` | any role | BERTopic topics (label, keywords, size, relevance, representative passages) and each document's topic shares |

While a run is in progress, `GET /api/sessions/{id}` returns
`progress: {stage, step, total_steps}`. The stages are queued → parsing →
preprocessing → keywords → entities → embeddings → topics → saving. Results
endpoints return `409 RESULTS_NOT_READY` until the session is `Completed`.

Uploads are checked for extension *and* file content (a renamed `.exe` is
rejected), a 25 MB limit, and exact duplicates (SHA-256). Only Admins can
upload or delete **NUC Core Reference** documents.

Roles: **Admin** (full access), **Curriculum Planner** (upload, run, review,
map, report), **Viewer** (read-only). Roles are enforced on the server with
`app.utils.rbac.roles_required`.

## Document processing

| Stage | Module | What it does |
|-------|--------|--------------|
| Parse | `services/ingestion/parsers.py` | PDF (PyMuPDF): extracts text page by page, drops running headers, footers and page numbers, and re-joins words hyphenated across line breaks. DOCX (python-docx): extracts body paragraphs and tables in reading order, skipping headers and footers. TXT: decodes UTF-8, falling back to cp1252. |
| Clean | `services/preprocessing/normalize.py` | NFKC normalisation, standardised quotes and dashes, and removal of invisible characters, URLs, emails, table-of-contents entries (with or without page numbers) and lines with no letters |
| Preprocess | `services/preprocessing/pipeline.py` | spaCy `en_core_web_sm` produces normalised sentences (used for SBERT and NER) and lowercased content-word lemmas with stop words removed (used for TF-IDF) |
| TF-IDF | `services/tfidf/` | scikit-learn keywords (unigrams and bigrams, sublinear TF) for each document and for the corpus. Terms found in more than 90% of documents are dropped when there are 5 or more documents. |
| NER | `services/ner/` | spaCy NER plus an EntityRuler with about 250 curated Computing patterns labelled `SKILL`, `TOOL` or `CERT` (`patterns.py`). Also keeps the standard `ORG`, `PRODUCT` and `GPE` labels. Skill demand counts total mentions and how many documents mention each skill. |
| Embeddings | `services/embeddings/` | SBERT `all-MiniLM-L6-v2`. `EMBEDDING_BACKEND=hashing` is a deterministic lexical stand-in for tests and offline development only. |
| Topics | `services/topics/` | BERTopic (UMAP → HDBSCAN → BM25 c-TF-IDF) over sentence-level passages, using our own embeddings. Each topic has a label, keywords, size, a 0–1 relevance score, the 3 passages closest to its centroid, document and source-category counts, and a centroid embedding. |
| Orchestration | `services/analysis.py`, `tasks/` | Celery task that runs the stages, records progress and timings, and saves the output. Any failure marks the session `Failed` with the error message and writes an audit entry. |

NUC Core Reference documents in a session are processed, but kept out of skill
demand, corpus keywords and topics. They are the baseline for overlap
detection in Sprint 4.

Scanned (image-only) PDFs are marked `Failed` with a clear reason. OCR is out
of scope.

## Project layout

```
backend/
  app/
    models/       # User, Document, AnalysisSession, DocumentSession, NLPResult,
                  # Recommendation, CurriculumMap, AuditLog
    routes/       # Flask blueprints (auth, health, …)
    schemas/      # request validation (session parameter_config, …)
    services/     # ingestion, preprocessing, tfidf, ner, embeddings, topics,
                  # similarity, recommendations, reports
    tasks/        # background jobs
    utils/        # error model, RBAC, audit logging
  migrations/     # Alembic
  tests/
data/{raw,processed,reference}/   # corpus (git-ignored)
docker/ · docker-compose.yml · docs/
```

## Branching

Work happens on `feature/*` branches, which merge into `develop` after review
and green CI. Tested releases are promoted to `main` (guide §19).
