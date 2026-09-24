# Setup

Three ways to run NLP-RS in development:

1. **Full Docker stack**: every service in containers, the same layout as production.
2. **Lightweight mode**: only PostgreSQL and Redis in Docker; Flask, the worker and Vite run
   natively. Faster on slower laptops, especially on Windows.
3. **Everything native**: no Docker; you provide PostgreSQL 16 + pgvector and Redis 7.

All modes read settings from `.env` at the repository root:

```bash
cp .env.example .env
# Edit .env: set SECRET_KEY and POSTGRES_PASSWORD (and the password inside DATABASE_URL).
python -c "import secrets; print(secrets.token_hex(32))"   # a value for SECRET_KEY
```

## 1. Full Docker stack

Prerequisites: Docker Engine 24+ with Compose v2.20+ (`docker compose version`). On Windows or
macOS, use Docker Desktop. Free host ports: 8080 (Nginx), 5000 (backend), 5432 (Postgres),
6379 (Redis). All of them can be changed in `.env`.

```bash
docker compose up --build
```

Open **http://localhost:8080**. The dashboard's *System status* card and the dot in the top bar
should both show the API as connected, with PostgreSQL and Redis available.

| Service | Purpose | Reachable at |
|---|---|---|
| `nginx` | Single entry point: `/api` → backend, everything else → frontend | http://localhost:8080 |
| `frontend` | Vite dev server with hot reload | via Nginx |
| `backend` | Flask API (debug server with auto-reload) | http://localhost:5000/api/health |
| `worker` | RQ worker for background jobs | — |
| `postgres` | PostgreSQL 16 + pgvector (volume `nlprs_postgres-data`) | localhost:5432 |
| `redis` | Job queue | localhost:6379 |

Source folders are bind-mounted, so code changes reload automatically. The worker does not
reload itself: after changing job code, run `docker compose restart worker`.

```bash
docker compose ps                          # service state
docker compose logs -f backend worker      # follow logs
docker compose exec backend pytest         # backend tests inside the container
docker compose down                        # stop (data volumes are kept)
docker compose down -v                     # stop and DELETE the database and uploaded files
```

## 2. Lightweight mode (services in Docker, app native)

`docker-compose.services.yml` defines only PostgreSQL (pgvector) and Redis. The full stack
includes the same file, so both modes use the same containers and the same data volume.

Requires Python 3.11+ and Node.js 22+ (24 recommended) on the host.

```bash
docker compose -f docker-compose.services.yml up -d --wait   # Postgres + Redis

# Backend (terminal 1)
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
flask --app wsgi run --debug         # http://localhost:5000

# Worker (terminal 2, same virtualenv)
cd backend && python -m app.worker

# Frontend (terminal 3)
cd frontend
npm ci
npm run dev                          # http://localhost:5173 (proxies /api to :5000)
```

In this mode, open **http://localhost:5173**. The `DATABASE_URL` and `REDIS_URL` values in
`.env` already point at `localhost`, which is where the services are published.

Stop the services with `docker compose -f docker-compose.services.yml down`.

## 3. Everything native

Follow section 2, but provide PostgreSQL 16 with the pgvector extension and Redis 7 yourself,
and set `DATABASE_URL` and `REDIS_URL` in `.env` to match.

## Tests and the test database

Backend tests run against a **separate database** on the same PostgreSQL server: the
development database name with `_test` appended (`nlprs_test` by default). The test suite
creates it automatically on first run and never touches the development database. As a
safeguard, it refuses to run against any database whose name does not end in `_test`. To use a
different database, set `TEST_DATABASE_URL`. Tests that need Redis use logical database 15.

```bash
# Backend (from backend/, with Postgres running)
pytest --cov=app
ruff check . && black --check .

# Frontend (from frontend/)
npm test
npm run lint && npm run typecheck && npm run format:check
npm run build
```

On Windows, run the backend tests natively (lightweight mode). They also work with
`docker compose exec backend pytest`, but Docker Desktop's file sharing makes them about ten
times slower.

## Dependencies and lockfiles

Every dependency is pinned to an exact version, and the lockfiles are committed.

- **Frontend:** `package.json` lists exact versions (no `^`/`~`), `package-lock.json` is
  committed, and `.npmrc` sets `save-exact=true` so that `npm install <pkg>` adds exact versions.
  Always install with `npm ci`.
- **Backend:** direct dependencies are listed in `requirements.in` (runtime) and
  `requirements-dev.in` (tools). The lockfiles `requirements.txt` and `requirements-dev.txt` are
  generated from them by pip-tools and pin every transitive package. They are compiled for
  Python 3.11 on Linux, the Docker target.

### Updating Python dependencies

1. Edit `requirements.in` or `requirements-dev.in`.
2. Regenerate both lockfiles inside a Python 3.11 container (run from `backend/`):

   ```bash
   docker run --rm -v "$PWD:/work" -w /work python:3.11-slim sh -c \
     "pip install -q pip-tools==7.6.1 && \
      pip-compile -q --strip-extras --no-emit-index-url -o requirements.txt requirements.in && \
      pip-compile -q --strip-extras --no-emit-index-url -o requirements-dev.txt requirements-dev.in"
   ```

3. Reinstall: `pip install -r requirements-dev.txt` (native) or `docker compose build backend worker`.

## Troubleshooting

- **Top bar shows "API unreachable"**: the backend is not running, or Nginx cannot reach it.
  Check `docker compose logs backend`.
- **"API degraded"**: the API is up but Postgres or Redis is not. The System status card shows
  which one; check `docker compose ps`.
- **Tests stop with "Cannot connect to PostgreSQL"**: start the services with
  `docker compose -f docker-compose.services.yml up -d --wait`.
- **Port already in use**: change `HTTP_PORT`, `BACKEND_HOST_PORT`, `POSTGRES_HOST_PORT` or
  `REDIS_HOST_PORT` in `.env`.
- **Hot reload misses changes on Windows or macOS**: polling is already enabled in compose
  (`VITE_USE_POLLING=true`). Make sure the repository is on a local disk.
