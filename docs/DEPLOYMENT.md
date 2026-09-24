# Deployment and operations (spec §18)

## Architecture

```
Browser ──HTTPS──> frontend (Nginx: Vue app, TLS, /api proxy)
                        │
                        └──> backend (Flask + gunicorn) ──> postgres
                                   │                         ▲
                                   └──> redis ──> worker (Celery: NLP pipeline) ──┘
                                              └── scheduler (Celery beat: stale-run sweeper)
Volumes: postgres_data, uploads (/data/raw), reports (/data/reports)
```

## Server requirements

- Linux with Docker Engine 24+ and the Docker Compose plugin.
- 4 CPU cores and 8 GB RAM are recommended. SBERT and BERTopic run on the CPU;
  the worker uses about 2–3 GB at peak.
- 20 GB of disk for images, the database, uploads and reports, plus space for
  backups.
- A DNS name for the server, and a TLS certificate and key (for example from
  the university IT unit or Let's Encrypt).
- Outbound internet access is needed only while building the images: the
  Hugging Face model is baked into the backend image, and the running system
  works offline.

## First installation

```bash
git clone <repository> /opt/nlp-rs && cd /opt/nlp-rs
cp .env.production.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # paste as SECRET_KEY
# Edit .env: SECRET_KEY, POSTGRES_PASSWORD, TLS_CERT_DIR (folder with fullchain.pem + privkey.pem)

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend flask db upgrade
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend flask create-user --role Admin
```

Then open `https://<server>/`, sign in as the Admin, and:

1. Upload the **NUC CCMAS core curriculum** as a *NUC Core Reference*
   document. Analyses can't run without it.
2. Create the planner and viewer accounts under **Users**.

To save typing, set
`alias dc='docker compose -f docker-compose.yml -f docker-compose.prod.yml'`.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `APP_CONFIG` | `development` | `production` enables secure cookies and refuses to start with unsafe settings |
| `SECRET_KEY` | — | At least 32 random characters. Signs session cookies. |
| `DATABASE_URL` | — | `postgresql+psycopg2://user:pass@host:5432/db` |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker |
| `EMBEDDING_BACKEND` | `sbert` | Must be `sbert` in production. `hashing` is for tests and offline development only. |
| `SBERT_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Changing it needs an image rebuild (the model is baked in) |
| `SPACY_MODEL` | `en_core_web_sm` | |
| `UPLOAD_FOLDER` / `REPORT_FOLDER` | `/data/raw`, `/data/reports` | Docker volumes |
| `STALE_RUN_MINUTES` | `30` | A run with no progress for this long is marked Failed |
| `TRUSTED_ORIGINS` | — | Extra `host[:port]` values allowed to send changes, for example a second DNS name |
| `INSTITUTION_NAME` | University of Uyo, Computer Science | Shown on reports |
| `BEHIND_PROXY` | — | Set to `1` (done in the production override) to trust Nginx's forwarded headers |

## Upgrades

```bash
cd /opt/nlp-rs && scripts/backup.sh /var/backups/nlp-rs     # always back up first
git pull
dc up -d --build
dc exec backend flask db upgrade
```

Migrations are applied as an explicit step (§18: "run migrations during
controlled deployment"). Analyses that are processing during a restart are
marked Failed by the sweeper and can be retried.

## Backups and restore

- `scripts/backup.sh [dir]` writes a `pg_dump` of the database and an archive
  of uploads and reports, keeping the last 14 of each. Schedule it nightly:

  ```
  30 1 * * * cd /opt/nlp-rs && scripts/backup.sh /var/backups/nlp-rs >> /var/log/nlp-rs-backup.log 2>&1
  ```

  Copy the backup folder off the server, for example to university storage.
- `scripts/restore.sh <db.dump> <files.tar.gz>` asks for confirmation, then
  replaces the database and files and runs migrations.
- Test a restore on a spare machine at least once a semester.

## Monitoring and troubleshooting

| Check | How |
|---|---|
| Health | `curl -s https://<server>/api/health` returns `{"status": "ok", "database": "ok"}` |
| Logs | `dc logs -f backend worker scheduler frontend` |
| Queue and worker alive | `dc exec worker celery -A celery_worker.celery inspect ping` |
| Stuck analysis | The scheduler marks runs Failed after `STALE_RUN_MINUTES`; to do it by hand, run `dc exec backend flask fail-stale-runs` |
| Locked account | Wait 15 minutes, or an Admin resets the password under **Users** |
| "No NUC Core Reference" | An Admin uploads the CCMAS core document |
| Performance check | `dc exec backend flask eval performance` (target: ≤ 60 s for 20 × 3,000 words) |

## Security checklist

- [ ] `.env` has a unique `SECRET_KEY` and database password, and is readable
      only by the deploy user (`chmod 600 .env`).
- [ ] HTTPS certificate installed and renewal scheduled. HTTP redirects to
      HTTPS, and HSTS is enabled.
- [ ] Only ports 80 and 443 are open. PostgreSQL and Redis aren't published
      on the host.
- [ ] The default Admin password was changed after first sign-in, and there
      are no shared accounts.
- [ ] Nightly backups run and are copied off the server.
- [ ] Dependencies are audited in CI (`pip-audit`, `npm audit`); rebuild the
      images when advisories appear.
- [ ] The audit log (**Audit log** page) is reviewed periodically, especially
      `LOGIN_FAILED` and `LOGIN_BLOCKED` entries.
