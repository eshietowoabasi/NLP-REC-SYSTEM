# Database

PostgreSQL 16 through SQLAlchemy 2, with schema changes managed by Alembic
(`backend/migrations`). Apply migrations with `flask db upgrade`. CI checks
that the models and migrations match (`flask db check`).

```mermaid
erDiagram
    users ||--o{ documents : uploads
    users ||--o{ analysis_sessions : owns
    users ||--o{ audit_logs : "performs"
    users ||--o{ reports : generates
    documents ||--o{ document_sessions : "included in"
    analysis_sessions ||--o{ document_sessions : includes
    document_sessions ||--o{ nlp_results : produces
    analysis_sessions ||--o{ recommendations : yields
    analysis_sessions ||--o{ reports : "reported in"
    recommendations ||--o{ curriculum_maps : "mapped to"
```

| Table | Purpose | Notable columns and constraints |
|---|---|---|
| `users` | Accounts (spec §11) | `username` and `email` unique; `role` ∈ {Admin, Curriculum Planner, Viewer}; bcrypt `password_hash`; `is_active` |
| `documents` | Source documents | `source_category` (5 values), `file_type` ∈ {pdf, docx, txt}, `processing_status` ∈ {Uploaded, Parsed, Failed}, `error_message`, unique `content_hash` (SHA-256), `extracted_text` (loaded only when needed), `word_count`, `page_count` |
| `analysis_sessions` | One analysis run | `status` ∈ {Pending, Processing, Completed, Failed}; `parameter_config` (JSON: threshold, weights, max recommendations); `progress_stage`; `heartbeat_at`; `corpus_results` (JSON: corpus keywords, skill demand, topics with centroid embeddings); `pipeline_info` (JSON: models, stage timings, counts, warnings) |
| `document_sessions` | Document ↔ session link (many-to-many) | Unique (`document_id`, `session_id`); `processing_order` |
| `nlp_results` | Output for each document in a session | `tfidf_keywords`, `ner_entities`, `topics` (JSON); `embedding` (JSON array, the mean of the document's passage vectors) |
| `recommendations` | Ranked candidate topics | Every score column has CHECK 0 ≤ score ≤ 1 (`ner_score`, `topic_score`, `novelty_score`, `composite_score`, `max_similarity`); `overlap_status`; `planner_decision` ∈ {Accepted, Rejected, Flagged, null}; `rank`; `evidence` (JSON) |
| `curriculum_maps` | Proposed courses | CHECK `credit_units` IN (1, 2, 3); `prerequisites` and `learning_outcomes` (JSON lists) |
| `reports` | Generated reports | `report_format` ∈ {pdf, docx}; `file_path`; `file_size` |
| `audit_logs` | Security and review trail (§14) | `action_type` (for example LOGIN, LOGIN_FAILED, DOCUMENT_UPLOAD, SESSION_RUN, RECOMMENDATION_DECISION, MAPPING_CREATE, REPORT_GENERATE, USER_UPDATE); `entity_type`/`entity_id`; `detail` (JSON) |

Enumerations are stored as readable strings with CHECK constraints (see
`docs/DECISIONS.md`). Deleting a session cascades to its links, NLP results,
recommendations, mappings and reports. Deleting a document removes its file
and session links, and is refused while a processing session uses it.

## Migrations

| Revision | Change |
|---|---|
| `30fcec4b01cf` | Initial schema: all spec §11 entities |
| `26c538cfb329` | Document parsing fields (hash, text, word and page counts) |
| `5dc5d3148a7f` | Session corpus results and pipeline info |
| `e8b8d83ca9d0` | Recommendation rank and evidence |
| `12420769c5a4` | Reports table |
| `49eb1962fdba` | Session heartbeat (stale-run detection) |
