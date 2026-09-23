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
| 2 | Document upload, validation, parsing, preprocessing | ⏳ Next |
| 3 | TF-IDF, NER, SBERT, BERTopic, background jobs | — |
| 4 | Semantic overlap and recommendation engine | — |
| 5 | Remaining APIs, Vue dashboard, mapping, reports | — |
| 6 | Evaluation, security hardening, deployment | — |

## Stack

Python 3.11 · Flask · SQLAlchemy / Alembic · PostgreSQL · Vue.js + Bootstrap 5
(planned) · spaCy · Sentence-Transformers · BERTopic · Docker Compose · Nginx

## Local development

Requirements: Python 3.11 and PostgreSQL 16 (or Docker).

```bash
python3.11 -m venv .venv && source .venv/bin/activate
cd backend
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

Roles: **Admin** (full access), **Curriculum Planner** (upload, run, review,
map, report), **Viewer** (read-only). Roles are enforced on the server with
`app.utils.rbac.roles_required`.

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
