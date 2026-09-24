# Definition of Done (spec §22)

| Area | Done when (spec) | Evidence | Status |
|---|---|---|---|
| Database | All required entities, relationships, constraints and migrations work. | All 8 spec entities plus `reports` (`backend/app/models`); CHECK constraints on scores, credit units and enums; 6 Alembic migrations, checked for drift and round-tripped in CI (`flask db check`); `docs/DATABASE.md` | ✅ |
| Documents | PDF/DOCX/TXT upload, validation, parsing and status tracking work. | Extension and content sniffing, 25 MB limit, duplicate detection, parse-on-upload with `Failed` status and reason (`services/ingestion`); tests in `test_ingestion.py` and `test_documents_api.py`; checked on the two sample constitutions | ✅ |
| NLP | All eight pipeline stages execute and persist outputs. | Parse → preprocess → TF-IDF → NER → SBERT → BERTopic → overlap → scoring (`services/analysis.py`); stored in `nlp_results` and the session's corpus results; `test_analysis_api.py` | ✅ |
| Similarity | Core comparison and 0.80 threshold behaviour are implemented and tested. | `services/similarity`; strict `> threshold` at the precision the API reports; `test_recommendations.py` (threshold edge cases) | ✅ Implemented · ⏳ threshold to be calibrated with `flask eval similarity` on the 30 expert pairs using SBERT |
| Recommendations | Scores, ranking, overlap status and decisions are persisted. | `services/recommendations`; the `recommendations` table with rank and evidence; audited decision API; justification needed to accept a duplicate | ✅ |
| Frontend | Planner can complete the workflow from login through report. | Vue app (`frontend/`); the Playwright test `tests/e2e/workflow.spec.js` covers login → upload → run → review → map → PDF report, plus viewer and admin paths; runs in CI | ✅ |
| Security | RBAC, bcrypt, HTTPS deployment configuration and audit logging are functional. | Server-side role checks on every route; bcrypt; HTTPS Nginx config with HSTS (`docker/nginx-https.conf`, `docker-compose.prod.yml`); audit log on every change; plus: CSRF origin check, login lockout, security headers, production config checks, dependency audits (`test_security.py`) | ✅ |
| Testing | Unit, integration, NLP and UAT evidence meets project targets. | 230+ backend tests at 94–95% coverage (target ≥ 85%) on SQLite and PostgreSQL; frontend unit and end-to-end tests; evaluation toolkit `flask eval ner\|topics\|similarity\|sus\|performance`; performance measured at 31.6 s for 20 × 3,000 words (hashing backend) | ✅ Tooling · ⏳ **needs project data:** 50 annotated job adverts (§17.1), 30 expert topic pairs (§17.3), UAT questionnaires from 5–10 faculty (§17.4), and runs with SBERT enabled |
| Deployment | Docker Compose deployment works on the target Linux environment. | `docker-compose.yml` + `docker-compose.prod.yml` (postgres, redis, backend, worker, scheduler, frontend/Nginx); both files validate; `docs/DEPLOYMENT.md` | ⏳ Images not yet built and run in this environment (no Docker daemon); do this on the target server |
| Documentation | API, setup, configuration, database and operational procedures are documented. | `README.md`, `docs/API.md` (checked against the code by `test_docs.py`), `docs/DATABASE.md`, `docs/DEPLOYMENT.md`, `docs/DECISIONS.md`, `data/evaluation/README.md` | ✅ |

## Remaining actions for the project team

1. Collect the evaluation data (§17) and run each `flask eval` command with
   `EMBEDDING_BACKEND=sbert`. Put the JSON results in the project report.
2. Set `similarity_threshold` from the Youden-optimal value reported by
   `flask eval similarity`, if it differs meaningfully from 0.80.
3. Build and start the production stack on the target server
   (`docs/DEPLOYMENT.md`) and upload the official CCMAS core document.
4. Decide the document retention period (`docs/DECISIONS.md`, D9).
