# NLP-RS â€” NLP-Driven Curriculum Recommendation System

A web application that helps curriculum planners at the University of Uyo design the
institution-owned **30%** of the Computer Science curriculum under the NUC CCMAS framework.
Planners upload job adverts, policy, institutional and academic documents; an NLP pipeline
(TF-IDF, spaCy NER, SBERT, BERTopic) proposes candidate course topics, checks them against the
national **70%** core for overlap, and ranks them with the supporting evidence. Planners accept,
reject or flag each recommendation, map accepted topics to proposed courses, and export a report.

> B.Sc. Computer Science final-year project, Department of Computer Science,
> Faculty of Computing, University of Uyo.

**Status:** Phase 3 (analysis pipeline) complete. See `CLAUDE.md` for the phase plan.

## Quick start

```bash
cp .env.example .env        # then set SECRET_KEY and POSTGRES_PASSWORD
docker compose up --build   # open http://localhost:8080
```

Full instructions, including running without Docker: [docs/SETUP.md](docs/SETUP.md).

## Documentation

- [docs/SETUP.md](docs/SETUP.md) â€” installation and development workflow
- [docs/API.md](docs/API.md) â€” REST API reference
- [docs/DECISIONS.md](docs/DECISIONS.md) â€” design decisions and rationale

## Stack

React + TypeScript (Vite, Tailwind, shadcn/ui, TanStack Query) Â· Flask + SQLAlchemy +
PostgreSQL 16 (pgvector) Â· RQ + Redis Â· spaCy, sentence-transformers, BERTopic, scikit-learn Â·
Docker Compose + Nginx.
