# Job-advert corpus collector

Collects computing job adverts for the NLP-RS corpus so they do not have to be copied by hand.
It is a stand-alone tool (not part of the web app) with its own dependencies.

Collected texts are written **outside the repository** (default
`C:\Users\Owoabasi\Documents\nlp-rs-data`, change with `--out`) and are never committed; the
data folder and the HTTP cache are listed in `.gitignore`.

## Sources

| Source | How | Notes |
|--------|-----|-------|
| **MyJobMag** (primary) | Listing pages `https://www.myjobmag.com/jobs-by-field/<field>/<page>` for `information-technology`, `research-data-analysis`, `ux-design-architecture`, `product-management`, `engineering`; job pages `https://www.myjobmag.com/job/<slug>` | robots.txt obeyed before every request |
| **Remotive** (optional, `--include-remote`) | Public API `https://remotive.com/api/remote-jobs?category=<slug>` for `software-dev`, `data`, `devops`, `qa`, `design`, `product` | One call per category per run, at most 4 runs a day; source and job URL kept for attribution |
| **Jobberman, LinkedIn** | **Never scraped.** Copy the advert manually and use the `paste` helper | Jobberman's robots.txt disallows `/job/`; LinkedIn's user agreement forbids scraping |

## Ethics and politeness

- **robots.txt.** Checked before every request with `urllib.robotparser` *and* a matcher that
  understands the `*` and `$` wildcards (robotparser ignores them, so MyJobMag's
  `Disallow: /*?` would otherwise not be enforced). A URL is requested only if both allow it.
  Crawled URLs never contain a query string; the only exception is Remotive's documented API.
- **Rate limits.** One request at a time, a random 3–5 s pause before each request, at most
  150 requests per run (`--max-requests`). HTTP 429 or 403 stops the run immediately.
- **Identification.** User-Agent: `NLP-RS academic research (University of Uyo final-year
  project)`.
- **Caching.** Raw responses are cached under `<out>/.cache`, so a re-run (e.g. the real run
  after a dry run) does not fetch the same pages again.
- **Attribution.** The manifest keeps the source and the original URL of every advert
  (required by Remotive's terms, good practice for MyJobMag).
- **Personal data (NDPA 2023).** Email addresses, phone numbers and URLs are removed from the
  text; no source or URL header is written into the `.txt` files. Only the job content is kept.
- **Purpose.** Academic research on curriculum relevance; the corpus is not republished.

## What is kept

Title, summary, responsibilities and requirements/skills. Removed: "Method of Application" and
everything after it, application instructions, benefits and salary, "About us" boilerplate,
navigation, buttons, related jobs and footers. Each heading, paragraph and bullet item is one
line; headings end with ":" and all other lines with a full stop (matching the app's
ingestion cleaning).

Filters:

- **Role families** (allow-list): `software_dev`, `data_ai`, `cybersecurity`, `cloud_devops`,
  `networking_systems`, `it_support`, `database`, `qa`, `ui_ux`, `product_agile`. A deny-list
  rejects non-computing roles (drivers, accountants, civil engineers, ...); academic posts
  (lecturer, professor, reader) and sales roles are rejected even when their title names a
  computing field ("Lecturer II - Cyber Security"): they do not describe practitioner demand.
- At least **150 words** after cleaning.
- At most `--per-family` adverts per family (default 8, counting adverts already in the
  manifest), `--target` in total (default 50).
- **De-duplication** against everything in the manifest: same normalised title + company, same
  SHA-256 of the normalised text, or a MyJobMag slug that differs only by a `-N` suffix.

## Output

- `<out>/job_market/myjobmag_<family>_<title-slug>_<date_posted>.txt` (UTF-8; Remotive adverts
  start with `remotive_`, pasted ones with their `--source`).
- `<out>/manifest.csv` with `file, source, url, title, company, location, date_posted,
  date_collected, role_family, word_count, sha256`.

## Running it

```powershell
cd tools\corpus_collector
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

python -m corpus_collector --dry-run          # list what would be collected; saves nothing
python -m corpus_collector                    # collect and save (reuses the dry run's cache)
python -m corpus_collector --include-remote --target 60 --per-family 10
python -m corpus_collector --pages 6 --cap product_agile=4   # a different cap for one family

# Fill one thin family: MyJobMag job-title pages first (from sitemap-jobtitle.xml, titles in
# that family only, newest first, at most --max-title-pages), then deeper field listings
# (information-technology and engineering for cybersecurity), until the family has
# --family-goal adverts in total (default 6). The overall --target is ignored.
python -m corpus_collector --only-family cybersecurity --pages 15 --dry-run
python -m corpus_collector --help             # all options (--out, --pages, --fields, ...)

# A manually copied advert (text on the clipboard):
python -m corpus_collector.paste --source jobberman --url https://www.jobberman.com/listings/... `
    --title "Backend Developer" --company "Example Ltd" --date 2026-09-20

# A document that is already in the data folder (nothing is downloaded):
python -m corpus_collector.register --file policy/<file>.pdf --source NITDA --url <url> --title "..."

pytest                                        # unit tests (synthetic fixtures)
```

HTTPS is verified against the Windows certificate store (truststore), so it works behind
antivirus software that re-signs HTTPS connections.
