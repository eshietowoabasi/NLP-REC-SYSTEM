# NLP-RS — NLP-Driven Curriculum Recommendation System

A web application that helps curriculum planners at the University of Uyo design the
institution-owned **30%** of the Computer Science curriculum under the NUC CCMAS framework.
Planners upload job adverts, policy, institutional and academic documents; an NLP pipeline
(TF-IDF, spaCy NER, SBERT, BERTopic) proposes candidate course topics, checks them against the
national **70%** core for overlap, and ranks them with the supporting evidence. Planners accept,
reject or flag each recommendation, map accepted topics to proposed courses, and export a report.

> B.Sc. Computer Science final-year project, Department of Computer Science,
> Faculty of Computing, University of Uyo.

**Status:** Phase 4 (evidence, recommendations, decisions and mapping) complete. See `CLAUDE.md` for the phase plan.

## Quick start

```bash
cp .env.example .env        # then set SECRET_KEY and POSTGRES_PASSWORD
docker compose up --build   # open http://localhost:8080
```

Full instructions, including running without Docker: [docs/SETUP.md](docs/SETUP.md).

## Documentation

- [docs/SETUP.md](docs/SETUP.md) — installation and development workflow
- [docs/API.md](docs/API.md) — REST API reference
- [docs/DECISIONS.md](docs/DECISIONS.md) — design decisions and rationale

## Stack

React + TypeScript (Vite, Tailwind, shadcn/ui, TanStack Query) · Flask + SQLAlchemy +
PostgreSQL 16 (pgvector) · RQ + Redis · spaCy, sentence-transformers, BERTopic, scikit-learn ·
Docker Compose + Nginx.
