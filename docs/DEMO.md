# Demo guide

How to start NLP-RS on the development laptop and a step-by-step script for demonstrating it
(e.g. at the project defence).

## Starting the app (one click)

From the repository root, in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-demo.ps1
```

or right-click `start-demo.ps1` → **Run with PowerShell**. The script:

1. checks the prerequisites (`.env`, `backend\.venv`, `frontend\node_modules`, Docker Desktop
   running);
2. starts PostgreSQL and Redis in Docker (`docker-compose.services.yml`);
3. applies database migrations;
4. opens three windows — **NLP-RS API** (Flask, port 5000), **NLP-RS worker** (RQ) and
   **NLP-RS frontend** (Vite, port 5173);
5. waits until the app answers and opens **http://localhost:5173** in the browser
   (`-NoBrowser` skips this).

Sign in with `ADMIN_USERNAME` and `ADMIN_PASSWORD` from `.env`.

To stop: close the three NLP-RS windows. PostgreSQL and Redis keep running in Docker; stop them
with `docker compose -f docker-compose.services.yml stop` (data is kept).

This is the lightweight mode (see `docs/SETUP.md`): the app runs natively, which is much faster
than the Docker stack on this laptop (Docker is limited to 2 CPUs and 3 GB by `.wslconfig`).
PDF reports need the Docker image (WeasyPrint's Pango libraries); natively, generate Word
(DOCX) reports, or produce the PDF you want to show beforehand with the Docker stack.

### Before the audience arrives

- Start the app and **run one analysis session** (or re-run the demo session): the first
  session in a new worker takes about a minute (UMAP compiles its code once); later ones take
  about 10 seconds.
- Create a **planner** and a **viewer** account in Admin → Users if you want to show the roles.
- Check the dashboard shows "API connected".

## Demo script (about 15 minutes)

The database already holds the real corpus: the NUC CCMAS computing core, the National Digital
Economy Policy and Strategy, and 55 job adverts, with a completed session.

1. **Sign in and dashboard** (1 min). Headline counts (documents, sessions, recommendations
   awaiting review, courses mapped), recent sessions, quick actions.
2. **Documents** (2 min). The library with category counts, search and filters. Open a job
   advert: pages, words, extracted passages. Mention that upload validates type and content,
   files are stored under random names and downloaded only through the API.
3. **NUC Core Reference** (1 min, admin). The active CCMAS version and its history; sessions
   compare every theme with it.
4. **New session** (2 min). Name → choose ready documents (category filter, "x of 60") →
   advanced settings: the three weights with the live sum check, duplicate threshold, maximum
   recommendations. *Create & run* and watch the stage tracker (Validating → … → Scoring).
5. **Evidence** (2 min). Keywords (TF-IDF, by category), skills (NER, document counts), themes
   (BERTopic, sample passages), overlap with the NUC core (threshold line, closest NUC passage).
6. **Recommendations** (3 min) — the core of the system. Ranked candidate topics; the composite
   score as three coloured parts (skill demand, theme strength, novelty) with the formula above
   the list; "New" / "Potential Duplicate" badges; filters and "x of N reviewed". Accept one
   topic, flag another.
7. **Recommendation detail** (2 min). "Why it ranks #1": the formula with the actual numbers;
   overlap panel with the closest NUC passage side by side; evidence passages grouped by
   document with page numbers; skills and keywords; decision with notes. Edit the title.
8. **Curriculum mapping and proposed curriculum** (1 min). *Map to course*: code, title, credit
   units, prerequisites, learning outcomes. The proposed curriculum totals the units against
   the 30% allowance.
9. **Reports** (1 min). Generate a report (sections, Word format) and download it.
10. **Administration** (optional). Settings (defaults, skill patterns, stop words) and the
    audit log with its CSV export. Sign in as the viewer to show that edit controls disappear
    and the API refuses changes.

## Sharing the demo online (ngrok)

The app can be opened from anywhere through an https link while it runs on this laptop. The
script builds the frontend and serves it with `vite preview` on port 4173 (the dev server's
many small files are too slow through a tunnel); preview proxies /api to Flask, so sign-in,
uploads, analyses and downloads all work through the one link.

One-time setup:

1. Create a free account at https://ngrok.com and install ngrok:
   `winget install --id Ngrok.Ngrok -e` (then reopen PowerShell).
2. Copy your authtoken from dashboard.ngrok.com and run
   `ngrok config add-authtoken <token>`.
3. In the dashboard, open **Domains** and claim your free static domain.

Then start everything with:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-online-demo.ps1
```

The first run asks for the static domain and remembers it in `.ngrok-domain`. The link works
while the laptop is on, online and the ngrok window is open. Visitors see ngrok's one-time
"You are about to visit" page; they click **Visit Site**. Give supervisors planner or viewer
accounts rather than the admin login, and close the ngrok window after the defence.

## Troubleshooting

- **"Docker Desktop is not running"**: start Docker Desktop, wait for "Engine running", re-run.
- **A window closes or shows an error**: read the message in that window; the most common cause
  is a port already in use (another Flask or Vite still running) — close it and re-run.
- **Uploads stay "Queued"**: the worker window is not running.
- **The first session is slow**: expected (one-off compilation); run a warm-up session first.
