# Implementation Decisions

The developer guide (§21) lists details the source specification leaves open.
This log records how each one is resolved. **Status** is one of:

- **Decided**: implemented in the codebase.
- **Proposed**: the default the team will build towards unless someone objects before that sprint starts.
- **Open**: needs input from the project owner or supervisor.

| # | Gap (guide §21) | Resolution | Status |
|---|-----------------|------------|--------|
| D1 | SBERT checkpoint and embedding dimension | `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions), set with `SBERT_MODEL` and baked into the Docker image. The embedding backend can be swapped (`EMBEDDING_BACKEND=sbert\|hashing`). `hashing` is a deterministic lexical stand-in for tests and offline development, and every run that uses it carries a warning. `all-mpnet-base-v2` (768 dimensions) is the fallback if the §17.3 evaluation shows too little separation. Embeddings are stored as JSON float arrays. | Decided |
| D2 | Authentication mechanism | Server-side cookie session using Flask-Login. The cookie is `HttpOnly` and `SameSite=Lax`, and `Secure` in production. The Vue app and API share one origin behind Nginx, so no tokens are held in browser storage. Passwords are hashed with bcrypt. | Decided |
| D3 | Background jobs and progress transport | Celery with Redis (`worker` service). `POST /run` claims the session with a conditional update, so it can't be started twice, and returns 202. The frontend polls `GET /api/sessions/{id}` for `progress.stage`. If Redis is down, the session is put back to its previous status and the request returns 503 `QUEUE_UNAVAILABLE`. | Decided |
| D4 | 0–1 normalisation of the NER and topic scores | NER score: `log(1 + freq) / log(1 + max_freq)` across the candidates in a session, which keeps very frequent skills from swamping the rest. Topic score: the candidate's BERTopic probability divided by the session maximum (min–max scaling). Both are clipped to [0, 1]. The database enforces the 0–1 range on every score column. | Proposed |
| D5 | Human-readable topic titles | The top 3 non-overlapping c-TF-IDF terms, spelled as they most often appear in the source text (e.g. "CISSP, PyTorch, Cloud"). KeyBERTInspired was dropped because it needs BERTopic to hold its own embedding model, while we pass embeddings in. Planners will be able to rename topics during review (Sprint 5). | Decided |
| D6 | Dedicated Evidence table | Not in v1. Passages are stored in `nlp_results.topics` and `ner_entities` (JSON with `document_id` and character offsets). This will be revisited if the dashboard needs to query across passages. | Proposed |
| D7 | File storage | Files are stored on the local filesystem under `UPLOAD_FOLDER` (`data/raw` in development, a Docker volume at `/data/raw` in containers) and named with UUIDs rather than the uploaded filename. | Decided |
| D8 | Report formats | PDF as the primary format, with DOCX as an optional second format. | Open |
| D9 | Retention, deletion and backup | Deleting a document removes the file and its session links. Nightly `pg_dump` and a backup of the uploads volume. The retention period is still to be agreed with the department. | Open |
| D10 | When documents are parsed and where the text is stored | Documents are parsed as soon as they are uploaded, so a broken file is marked `Failed` with a reason straight away instead of failing mid-analysis. The extracted text is stored in `documents.extracted_text`, which list endpoints never load. Preprocessing (spaCy) runs as part of the analysis pipeline and its output is not stored. | Decided |

## Other decisions made during implementation

### NLP pipeline (Sprint 3)

- **Topic modelling works on passages (sentences of 6+ words), not whole documents.** A session has at most 50 documents, far too few to cluster, but typically thousands of passages. Topic modelling is skipped (with a warning) below 30 passages.
- **Topic model settings:** UMAP uses `random_state=42` so topics are reproducible. HDBSCAN's `min_cluster_size` is max(5, 1% of passages). c-TF-IDF uses BM25 weighting with `reduce_frequent_words`. When there are 3 or more topics, terms found in more than 80% of them are dropped, which removes boilerplate. The vectoriser's `min_df` must stay at 1, because BERTopic counts it per topic, not per passage.
- **Duplicate passages** (boilerplate repeated across job adverts) are fitted once, then every copy is mapped back to that topic. Sizes and per-document counts include the copies, while representative passages are always distinct. Exact duplicates also made UMAP's neighbour search very slow.
- **Performance (§17.5, ≤ 60 s for 20 documents × ~3,000 words):** measured at **32 s** on 60k words and 4,534 passages with warm models on a 4-core sandbox. The breakdown is 4 s preprocessing, 9 s NER and 19 s topics, using the hashing embedder. SBERT couldn't be measured here because Hugging Face is blocked; MiniLM on CPU is expected to add roughly 6–15 s. UMAP uses `n_epochs=200`, 7× faster than the default 500 with identical clusters in our benchmark (ARI 1.0). The seeded UMAP runs single-threaded, which is the price of reproducible topics. Workers warm the models at startup (about 20 s once per process).
- **Topic relevance** (§8.6) is the topic's size divided by the largest topic's size. Source-category counts are stored so Sprint 4 can weight market and policy evidence.
- **NUC Core Reference documents** in a session are processed per document, but kept out of corpus keywords, skill demand and topics. A session with only core references fails with a clear reason.
- **Completed sessions can't be re-run.** Their results, and later the planner decisions, are kept; re-analysing means creating a new session. Failed sessions can be retried.
- **Storage:** corpus-level output (keywords, skill demand, topics with centroid embeddings) is stored in `analysis_sessions.corpus_results`. Run metadata (models, stage timings, counts, warnings) goes in `analysis_sessions.pipeline_info`. Per-document output goes in `nlp_results`, with the mean passage embedding as the document embedding. API responses never include embeddings.
- **NER patterns** are in `services/ner/patterns.py`. Acronyms and product names that are also ordinary words (`AI`, `Spark`, `Swift`, `Node`) are matched case-sensitively. `Go`, `R` and `C` match only when followed by words like "programming" or "language". Bare "compliance" is not matched because it is too common in legal text.
- **Gensim LDA baseline** (§8.5/§17.2) is deferred to the evaluation work in Sprint 6.
- **Stuck sessions:** if a worker is killed mid-run, the session stays `Processing`. A stale-run sweeper, which would fail sessions stuck longer than N minutes, is noted for Sprint 6.

- **Recommendation.max_similarity**: stored in addition to `novelty_score` (which equals `1 − max_similarity`) so that overlap results can be audited and shown on the similarity endpoint.
- **Document diagnostics**: `original_filename`, `file_size` and `error_message` were added to `Document`, and `progress_stage` and `error_message` to `AnalysisSession`. These support the "failed documents are diagnosable" requirement (§7.2) and progress display (§15).
- **Document statuses**: `Uploaded`, `Parsed` and `Failed`. The specification lists statuses only for sessions.
- **Enums**: stored as their human-readable values in `VARCHAR` columns with `CHECK` constraints rather than native PostgreSQL enums. This makes migrations easier when values change.
- **Duplicate uploads**: a file identical to one already in the library (same SHA-256 hash, stored in `documents.content_hash`) is rejected with `409 DUPLICATE_DOCUMENT`. Counting the same job-advert dump twice would inflate TF-IDF and NER frequencies.
- **Document visibility**: every signed-in user can read every document and session, because the corpus is shared across the department. Planners can delete only their own uploads. Only Admins can upload or delete `NUC Core Reference` documents (§14).
- **Session inputs**: every document in a session must be `Parsed`. Duplicate IDs are removed, and the order given in the request becomes `processing_order`.
- **TF-IDF tokens**: only content-word parts of speech are kept (`NOUN`, `PROPN`, `VERB`, `ADJ` and `X`). spaCy's stop-word list misses modal verbs such as *shall*, which dominated the sample constitutions.
- **AuditLog.user_id**: nullable, so failed logins and system actions can still be recorded.
