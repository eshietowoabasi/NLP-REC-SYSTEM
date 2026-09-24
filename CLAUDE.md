# CLAUDE.md — NLP-RS project context

NLP-Driven Curriculum Recommendation System: a B.Sc. Computer Science final-year project
(University of Uyo, Dept. of Computer Science). Planners upload job adverts, policy,
institutional and academic documents; an NLP pipeline proposes candidate course topics for the
university-designed **30%** of the NUC CCMAS curriculum, scored against the fixed NUC **70%** core.
Humans accept/reject/flag; the system never changes the curriculum itself.

Scope: CS, Software Engineering, Cybersecurity, IT. English only. PDF/DOCX/TXT. Corpus 2020–2026.
Web only (Chrome, Firefox, Edge). Pre-trained models only.

## Working rules

- Work in phases (0–6, listed below). One `feature/<phase-name>` branch per phase, merged into
  `develop`; `main` holds releases. At the end of each phase: lint + tests pass, commit (one
  logical change per commit), give a short summary, **wait for go-ahead** before the next phase.
- Ask before deviating from the stack or the decisions below; record agreed changes in
  `docs/DECISIONS.md`.
- No placeholder code, TODO stubs or fake data in production paths. Deferred work is listed in
  the phase summary. Test fixtures are synthetic and labelled as such.
- Readable for an examiner: docstrings on services, type hints throughout the backend.
- Keep `docs/API.md` updated as endpoints are added, and this file as conventions change.

## Stack (fixed)

- **Frontend** (`frontend/`): React 19 + TypeScript (strict) + Vite 8, React Router 8,
  Tailwind CSS 4 + shadcn/ui (Radix base, "nova" preset), TanStack Query 5 + Axios,
  React Hook Form + Zod, Recharts, lucide-react. Vitest + Testing Library, ESLint, Prettier.
- **Backend** (`backend/`): Python 3.11 (Docker image; code must stay 3.11-compatible),
  Flask app factory + blueprints, SQLAlchemy 2 via Flask-SQLAlchemy, Flask-Migrate (Alembic),
  PostgreSQL 16 + pgvector, Flask-Login cookie sessions + CSRF, bcrypt, **Pydantic v2** for
  request/response validation, RQ + Redis for background jobs. pytest/pytest-cov, ruff, black.
- **Parsing**: PyMuPDF, python-docx (paragraphs + tables), TXT with encoding fallback,
  python-magic for content-type checks.
- **NLP**: spaCy `en_core_web_sm` (+ EntityRuler), NLTK only where spaCy lacks something,
  scikit-learn (TF-IDF, cosine, metrics), sentence-transformers `all-MiniLM-L6-v2`,
  BERTopic (UMAP + HDBSCAN, fixed `random_state`), Gensim (LDA baseline + C_v, evaluation only).
- **Reports**: WeasyPrint (PDF, primary), python-docx (DOCX).
- **Deploy**: Docker Compose — `nginx`, `frontend`, `backend` (Gunicorn), `worker` (RQ),
  `postgres`, `redis`; named volumes for Postgres data and uploaded files.

## Key decisions (full list with rationale: `docs/DECISIONS.md`)

1. SBERT `all-MiniLM-L6-v2` by default; model name is a setting.
2. Cookie session auth + CSRF; same origin (Nginx in Docker, Vite proxy in local dev).
3. RQ + Redis jobs; UI polls `GET /api/sessions/{id}` every 2–3 s while processing.
4. **Branched preprocessing**: light-cleaned original-casing passages → NER, SBERT, BERTopic,
   evidence display. Heavily normalised text (lowercase, stop words out, lemmas) → TF-IDF only.
5. **Passages** (3–5 sentences, ~100–200 words, configurable) are the unit of analysis; store
   document, page number, position.
6. Parse once per document (ingestion job after upload); sessions reuse stored passages and
   embeddings.
7. Candidate topics = BERTopic topics over **non-NUC** passages only; outlier topic −1 dropped.
   The NUC core is only the comparison baseline.
8. Candidate embedding = L2-normalised mean of member passage embeddings.
9. Novelty = `1 − max cosine(candidate, NUC core passages)`, clipped to [0,1].
   `max_sim > threshold` (default 0.80, strictly greater) → "Potential Duplicate", else
   "No Significant Overlap". Store closest NUC passage id.
10. Skill (NER) score: per candidate, sum over its top skills of the number of distinct documents
    mentioning each skill → `log1p` → min-max across candidates (all equal → 1.0).
11. Theme (topic) score: `(topic_passages / total_non_outlier_passages) × mean_topic_probability`
    → min-max across candidates.
12. `composite = w_ner·ner + w_topic·topic + w_novelty·novelty`, defaults 0.40/0.35/0.25, weights
    must sum to 1.0 ± 0.001. Rank descending, keep top `max_recommendations` (default 20).
    Duplicates stay in the list, badged.
13. Titles auto-generated from top c-TF-IDF keywords; planners can edit (`auto_title` vs
    `topic_title` stored separately).
14. `RecommendationEvidence` table: top N (default 8) representative passages per topic.
15. Reports: PDF (primary) + DOCX.
16. Files on a Docker volume under UUID names; original filename in DB; downloads only through
    authorised endpoints.
17. Documents used by a session cannot be hard-deleted (409) — archive instead. Users are
    deactivated, never deleted.
18. Exactly one active NUC core version (admin-only upload). Sessions record the version used and
    cannot run without one.
19. 30% credit-unit allowance: admin setting, null until set.

## Roles

`admin` (everything incl. NUC core, users, settings, skill patterns, stop words, audit log),
`planner` (upload/archive, sessions, decisions, title edits, mapping, reports), `viewer`
(read-only). Enforced **server-side on every route** (`@role_required(...)`); frontend hiding is
cosmetic.

## API conventions

- All routes under `/api`. Success `{"success": true, "data": ...}`; error
  `{"success": false, "error": {"code", "message", "details"}}` (built by
  `app/utils/responses.py`; raise `app.utils.errors.ApiError` for expected errors).
- Status codes 400/401/403/404/409/413/422/500/503. Lists paginate with `?page=&per_page=`.
- Clients get generic messages for unexpected errors; details go to server logs.
- Shared frontend API types live in `frontend/src/types/api.ts`.

## Code layout

- `backend/app/__init__.py` — `create_app(config_name)`; `config.py` (APP_ENV =
  development|testing|production); `extensions.py` (db, migrate, Redis client);
  `routes/` (one blueprint per area); `services/<stage>/` (pure, DB-free pipeline functions);
  `tasks/` (RQ jobs); `auth/`, `audit/`, `schemas/`, `models/`, `utils/`.
  `app/worker.py` runs the RQ worker inside an app context. `wsgi.py` for Gunicorn.
- NLP models (spaCy, SBERT) are loaded once per worker process (module-level cache).
- `frontend/src/` — `components/ui` (shadcn, generated), `components/layout` (shell, sidebar,
  nav config in `navigation.ts`), `features/<area>/` (pages, hooks, feature components),
  `routes/` (router, route `handle.title` drives the top-bar title), `lib/` (Axios client,
  query client, utils), `types/api.ts`, `test/` (setup + render helpers).
- Every data screen has loading, empty and error states. Accessible: labelled inputs,
  keyboard navigation, sufficient contrast. Responsive to tablet width.

## Commands

```bash
# Full stack (Docker): http://localhost:8080
cp .env.example .env && docker compose up --build
# Lightweight mode: only Postgres + Redis in Docker, app runs natively
docker compose -f docker-compose.services.yml up -d --wait

# Backend (from backend/)
python -m venv .venv && .venv/Scripts/activate      # Windows; source .venv/bin/activate on Linux
pip install -r requirements-dev.txt
pytest --cov=app          # tests + coverage (target ≥ 85%); uses nlprs_test, auto-created
ruff check . && black --check .
flask --app wsgi run --debug

# Frontend (from frontend/)
npm ci
npm run dev               # proxies /api to http://localhost:5000
npm test                  # vitest
npm run lint && npm run typecheck && npm run format:check
npm run build
```

Local dev on Windows uses Python 3.13 in `backend/.venv`; the Docker image uses 3.11.
Docker CLI on this machine: `C:\Users\Owoabasi\AppData\Local\Programs\DockerDesktop\resources\bin`
(add it to PATH in a shell if `docker` is not found).

**Dependencies are pinned exactly.** Frontend: exact versions in `package.json`, `.npmrc`
`save-exact=true`, committed `package-lock.json`, install with `npm ci`. Backend: edit
`requirements.in` / `requirements-dev.in`, then regenerate the pip-tools lockfiles
(`requirements.txt`, `requirements-dev.txt`) in a python:3.11 container; the command is in
docs/SETUP.md. Never hand-edit the lockfiles.

**Tests** use a separate `<db>_test` database on the same Postgres, created automatically by
`tests/conftest.py`, which refuses any database not named `*_test`.

## Phases

- [x] **0 Scaffold** — repo layout, compose, app factory + `/api/health`, frontend shell.
- [ ] **1 Data model, auth, roles, audit**
- [ ] **2 Documents and ingestion**
- [ ] **3 Analysis pipeline**
- [ ] **4 Evidence, recommendations, decisions, mapping**
- [ ] **5 Reports, dashboard, admin settings**
- [ ] **6 Evaluation, hardening, deployment, docs**
