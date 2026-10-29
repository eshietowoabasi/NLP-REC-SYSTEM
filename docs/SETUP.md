# Setup

The recommended SkillBridge development setup is now **Docker-free**.

The application runs locally while PostgreSQL and Redis are provided by managed services:

- **PostgreSQL + pgvector:** Neon or another compatible PostgreSQL provider
- **Redis:** Upstash or another Redis-compatible provider
- **Flask API:** local
- **RQ worker:** local
- **React/Vite frontend:** local
- **NLP models:** local
- **Uploaded files / reports:** local `STORAGE_DIR`

Docker Compose remains available as an optional legacy/full-container setup, but Docker is not required for normal development.

## Requirements

- Windows, macOS or Linux
- Python 3.11+ (the recovered Windows environment has been verified on Python 3.13)
- Node.js 22+ (Node 24 is supported)
- npm
- Git
- PostgreSQL with the `vector` extension
- Redis reachable through a normal Redis/TLS connection URL

## 1. Environment file

Copy the example:

```bash
cp .env.example .env
```

On Windows Command Prompt:

```cmd
copy .env.example .env
```

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Set:

- `SECRET_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `ADMIN_USERNAME`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `ADMIN_FULL_NAME`

Never commit `.env`.

### PostgreSQL URL

For SQLAlchemy + psycopg v3, use:

```text
postgresql+psycopg://USER:PASSWORD@HOST/DATABASE?sslmode=require
```

For Neon, copy the provided PostgreSQL URL and change the scheme from:

```text
postgresql://
```

to:

```text
postgresql+psycopg://
```

Keep Neon SSL query parameters.

### Redis URL

Use a standard Redis/TLS URL:

```text
rediss://default:TOKEN@HOST:6379
```

For Upstash, use the TCP connection string, not the REST URL.

## 2. PostgreSQL / pgvector

The database must have pgvector enabled:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Verify:

```sql
SELECT extversion FROM pg_extension WHERE extname = 'vector';
```

## 3. Backend environment

From `backend/`:

```bash
python -m venv .venv
```

Windows:

```cmd
.venv\Scripts\pip install -r requirements-dev.txt
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## 4. Frontend packages

From `frontend/`:

```bash
npm ci
```

## 5. First database initialization

From `backend/`:

```bash
flask --app wsgi db upgrade
flask --app wsgi seed
```

`seed` creates the first admin only if no admin exists and also loads:

- application settings
- skill patterns
- domain stop words

Additional users are created by an administrator under **Administration â†’ Users**.

## 6. Recommended one-command startup

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-demo.ps1
```

The launcher:

1. checks `.env`
2. checks the backend virtual environment
3. checks frontend packages
4. verifies PostgreSQL
5. verifies Redis
6. applies migrations
7. opens Flask on port 5000
8. opens the RQ worker
9. opens Vite on port 5173
10. waits for the API and frontend
11. opens the browser

Open:

```text
http://localhost:5173
```

Backend health:

```text
http://localhost:5000/api/health
```

A healthy response reports both database and Redis as `ok`.

## 7. Manual startup

If you want to run each process yourself:

### Terminal 1 â€” Flask

```cmd
cd backend
.venv\Scripts\flask.exe --app wsgi run --port 5000
```

### Terminal 2 â€” RQ worker

```cmd
cd backend
.venv\Scripts\python.exe -m app.worker
```

The worker should show:

```text
Listening on default...
```

### Terminal 3 â€” Vite

```cmd
cd frontend
npm run dev
```

Open:

```text
http://localhost:5173
```

## 8. Core first-run workflow

Before analyses can run:

1. Sign in as administrator.
2. Go to **Administration â†’ NUC core curriculum**.
3. Upload the complete NUC CCMAS Computing curriculum.
4. Wait for it to become **Ready** and **Active**.
5. Upload job adverts, policy documents, university documents or academic papers.
6. Wait for source documents to become **Ready**.
7. Create an analysis session.
8. Review suggested topics.
9. Accept, reject or discuss topics later.
10. Design courses from accepted topics.
11. Generate and download the report.

## 9. NLP models

- spaCy `en_core_web_sm` is installed as a Python dependency.
- SBERT `all-MiniLM-L6-v2` is downloaded from Hugging Face when first needed and cached locally.
- The first ingestion or analysis after starting a fresh worker can be slower.
- The RQ worker keeps models loaded between jobs.

If HTTPS interception by antivirus causes model-download certificate failures, set:

```text
USE_SYSTEM_CERTS=true
```

and restart Flask and the worker.

## 10. Reports

DOCX reports work natively.

PDF reports use WeasyPrint and require Pango on Windows. If native PDF generation fails, install MSYS2/Pango and configure:

```text
WEASYPRINT_DLL_DIRECTORIES=C:\msys64\ucrt64\bin
```

Generated reports are stored below:

```text
STORAGE_DIR/reports/
```

## 11. Tests

Frontend:

```bash
cd frontend
npm test
npm run lint
npm run typecheck
npm run build
```

Backend tests require a separate test database whose database name ends in `_test`.

If using a managed PostgreSQL provider, create a dedicated test database and set:

```text
TEST_DATABASE_URL=postgresql+psycopg://...
```

Do not point automated tests at the normal development database.

## 12. Troubleshooting

### API unreachable

Make sure Flask is running on port 5000.

Check:

```cmd
curl http://localhost:5000/api/health
```

### API degraded

The API is running but PostgreSQL or Redis is unavailable. Check `DATABASE_URL`, `REDIS_URL`, internet access and provider status.

### Documents stay queued

The RQ worker is not running or cannot reach Redis/PostgreSQL.

Start:

```cmd
cd backend
.venv\Scripts\python.exe -m app.worker
```

### Cannot sign in after moving databases

User accounts live in PostgreSQL. A new empty database contains no old users until they are recreated or restored from a database backup. Running `flask seed` creates only the configured initial admin when no admin exists.

### pgvector errors

Run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Certificate errors

Set:

```text
USE_SYSTEM_CERTS=true
```

and restart the app processes.

### First analysis is slow

UMAP and NLP models may perform one-time initialization in a fresh worker. Later analyses are normally faster.

### Port already in use

The default local ports are:

- Flask: `5000`
- Vite: `5173`

Stop the existing process or change the relevant local configuration.

## Optional Docker setup

The repository still contains Docker Compose files for the older containerized setup. They may be useful for reproducible deployment or isolated testing, but they are no longer the recommended day-to-day development path.
