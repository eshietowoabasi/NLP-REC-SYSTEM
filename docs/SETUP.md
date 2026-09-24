# Setup

Two ways to run NLP-RS in development:

- **Docker Compose** (recommended; the same services as production).
- **Local processes** (backend and frontend on the host; useful on machines without Docker).

## 1. Docker Compose

### Prerequisites

- Linux, macOS or Windows with Docker Engine 24+ and the Compose v2 plugin
  (`docker compose version`). On Windows/macOS, Docker Desktop.
- Free host ports: 8080 (Nginx), 5000 (backend), 5432 (Postgres), 6379 (Redis). All can be
  changed in `.env`.

### Steps

```bash
git clone <repository-url> nlp-rs && cd nlp-rs
cp .env.example .env
# Edit .env: set SECRET_KEY and POSTGRES_PASSWORD at minimum.
python3 -c "import secrets; print(secrets.token_hex(32))"   # a value for SECRET_KEY

docker compose up --build
```

Open **http://localhost:8080**. The dashboard's *System status* card and the dot in the top bar
should both show the API as connected, with PostgreSQL and Redis available.

| Service | Purpose | Reachable at |
|---|---|---|
| `nginx` | Single entry point: `/api` → backend, everything else → frontend | http://localhost:8080 |
| `frontend` | Vite dev server with hot reload | via Nginx |
| `backend` | Flask API (debug server with auto-reload in development) | http://localhost:5000/api/health |
| `worker` | RQ worker for background jobs | — |
| `postgres` | PostgreSQL 16 + pgvector (volume `postgres-data`) | localhost:5432 |
| `redis` | Job queue | localhost:6379 |

Source folders are bind-mounted, so code changes reload automatically (restart `worker` after
changing job code: `docker compose restart worker`).

### Useful commands

```bash
docker compose ps                          # service state
docker compose logs -f backend worker      # follow logs
docker compose exec backend pytest         # backend tests inside the container
docker compose down                        # stop (data volumes are kept)
docker compose down -v                     # stop and DELETE database and uploaded files
```

## 2. Local processes (without Docker)

Requires Python 3.11+ and Node.js 22+ (24 recommended). PostgreSQL 16 with pgvector and
Redis 7 must be reachable; set `DATABASE_URL` and `REDIS_URL` in `.env` at the repository
root (the Flask CLI loads it automatically).

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
flask --app wsgi run --debug         # http://localhost:5000
python -m app.worker                 # in a second terminal

# Frontend
cd frontend
npm ci
npm run dev                          # http://localhost:5173, proxies /api to :5000
```

## 3. Checks

```bash
# Backend (from backend/)
pytest --cov=app
ruff check . && black --check .

# Frontend (from frontend/)
npm test
npm run lint && npm run typecheck && npm run format:check
npm run build
```

## Troubleshooting

- **Top bar shows "API unreachable"** — the backend is not running or Nginx cannot reach it:
  `docker compose logs backend`.
- **"API degraded"** — the API is up but Postgres or Redis is not; the System status card
  shows which. Check `docker compose ps`.
- **Port already in use** — change `HTTP_PORT`, `BACKEND_HOST_PORT`, `POSTGRES_HOST_PORT` or
  `REDIS_HOST_PORT` in `.env`.
- **Hot reload not picking up changes on Windows/macOS** — polling is enabled in compose
  (`VITE_USE_POLLING=true`); make sure the repository is on a local disk.
