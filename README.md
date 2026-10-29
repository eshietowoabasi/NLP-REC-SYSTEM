# SkillBridge â€” NLP-Driven Curriculum Recommendation System

SkillBridge is a web application that helps curriculum planners at the University of Uyo design the institution-owned **30%** of the Computer Science curriculum under the NUC CCMAS framework.

Planners upload job adverts, policy, institutional and academic documents. The NLP pipeline (TF-IDF, spaCy NER, SBERT and BERTopic) proposes candidate course topics, checks them against the national **70%** core for overlap, ranks them with supporting evidence, and supports a human review workflow from recommendation to proposed course and report.

> B.Sc. Computer Science final-year project, Department of Computer Science, Faculty of Computing, University of Uyo.

## Recommended development setup

Normal local development is now **Docker-free**:

- Flask API runs locally.
- RQ worker runs locally.
- React/Vite frontend runs locally.
- PostgreSQL + pgvector is provided by Neon (or another compatible PostgreSQL service).
- Redis is provided by Upstash (or another Redis-compatible service).
- Uploaded files and generated reports are stored locally in `STORAGE_DIR`.

Once `.env`, the Python virtual environment and frontend packages are configured, start everything with:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-demo.ps1
```

The launcher verifies PostgreSQL and Redis, applies migrations, opens the Flask API, RQ worker and Vite frontend, waits for the health checks, then opens **http://localhost:5173**.

Full installation and recovery instructions: [docs/SETUP.md](docs/SETUP.md).

## Documentation

- [docs/SETUP.md](docs/SETUP.md) â€” installation, Docker-free development and troubleshooting
- [docs/API.md](docs/API.md) â€” REST API reference
- [docs/DECISIONS.md](docs/DECISIONS.md) â€” design decisions and rationale
- [docs/DEMO.md](docs/DEMO.md) â€” demo and presentation workflow

## Stack

React + TypeScript (Vite, Tailwind, shadcn/ui, TanStack Query) Â· Flask + SQLAlchemy Â· PostgreSQL + pgvector Â· RQ + Redis Â· spaCy Â· sentence-transformers Â· BERTopic Â· scikit-learn.

Docker Compose files remain in the repository as an optional legacy/full-container setup, but Docker is no longer required for normal local development.
