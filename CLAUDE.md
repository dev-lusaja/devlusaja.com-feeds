# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

An automated RSS/scraping pipeline that collects AI-related news, papers, videos and forum posts, stores them in a local SQLite DB, and publishes them as chunked static JSON files under `assets/`. Those files are deployed straight to Netlify via `netlify-cli` (no build step, no git commit) and consumed as a public JSON API.

Pipeline: `feeds_config.yaml` (source list) → `src/feed_fetcher.py` (fetch + scrape) → SQLite (`data/feeds.db`) → JSON chunk files in `assets/` → `netlify deploy` (CLI, direct).

Generated JSON under `assets/` is **gitignored** (`assets/*.json`) — it's reproducible from the DB and would otherwise bloat repo history (a prior approach committed every run and grew `.git` to ~900MB). Only `assets/_headers` (hand-maintained Netlify headers config) is tracked. `data/feeds.db` itself is never committed either; it's backed up to/restored from Google Drive.

## Commands

Everything runs inside Docker via `run.sh` (interactive menu) — there is no local venv workflow documented; `docker/requirements.txt` lists the Python deps (feedparser, pandas, mysql-connector-python, playwright, beautifulsoup4, etc.) installed in the container.

```bash
./run.sh                 # interactive menu: fetch feeds, postprocess images, regenerate assets, Drive sync
./run.sh --auto          # non-interactive: force-fetch, then git add/commit/push assets/ if changed (used by CI)

# Individual operations, run inside the feed_collector container:
docker compose -f docker/docker-compose.yml build feed_collector
docker compose -f docker/docker-compose.yml run --rm feed_collector python src/feed_fetcher.py --force
docker compose -f docker/docker-compose.yml run --rm feed_collector python src/regenerate_assets.py
docker compose -f docker/docker-compose.yml run --rm feed_collector python src/feed_postprocess_images.py --source-type notice --all
```

There is no test suite, linter, or build step in this repo.

### Scheduling

GitHub Actions (`.github/workflows/daily-feeds.yml`) runs `./run.sh --auto` three times daily (8:00/14:00/20:00 UTC). It restores `data/feeds.db` from Google Drive (`rclone`, remote name `gdrive`, folder `feeds_backup/`) before running, and backs it up again after (`if: always()`, even on failure). `run.sh --auto` itself fetches, rebuilds all assets, then deploys `assets/` straight to Netlify with `netlify-cli` (`NETLIFY_AUTH_TOKEN`/`NETLIFY_SITE_ID`) — no git commit involved. Locally, use `run.sh` menu option 7 (or `download_db`/`upload_db`) to pull/push the same Drive-backed DB for development; both paths read `RCLONE_CONFIG_GDRIVE_*` from `.env`.

**Google Drive auth is env-var-only, no `rclone.conf` file:** `RCLONE_CONFIG_GDRIVE_TYPE=drive`, `_CLIENT_ID`, `_CLIENT_SECRET`, `_TOKEN` (a JSON blob), `_SCOPE=drive.file`. Critically, `_CLIENT_ID`/`_CLIENT_SECRET` must be **your own OAuth client** (Google Cloud Console → APIs & Services → Credentials → OAuth client ID → Desktop app, "User data" not "Application data" — a service account has no storage quota on a personal, non-Workspace Drive), not rclone's shared default — and the OAuth consent screen must be in **Production** publishing status, not Testing. Testing-status refresh tokens expire after 7 days, which is what breaks unattended CI silently; Production-status ones only die on explicit revocation or 6 months of inactivity. Scope is `drive.file` (non-sensitive, no extra Google verification step) rather than full `drive` — it only grants access to files/folders the app itself creates, so let rclone create the `feeds_backup` folder on first upload instead of pre-creating it by hand in the Drive UI. To generate `_TOKEN`, run `rclone authorize "drive"` locally once (it opens a browser, do the consent flow with your own client ID/secret set via `RCLONE_CONFIG_GDRIVE_CLIENT_ID`/`_CLIENT_SECRET` env vars first) and copy the resulting JSON token string into the secret/`.env` value.

The Netlify site was originally connected to this GitHub repo for git-triggered auto-deploy; that's now disabled (`build_settings.stop_builds: true`, set via `netlify api updateSite`) since `assets/*.json` is no longer committed — an unrelated push to `main` would otherwise trigger a build from the repo's (now near-empty) `assets/` and wipe out what the CLI just deployed. `netlify.toml` and `.netlifyignore` were removed entirely: both only mattered for git-triggered builds off the full repo checkout, which no longer happens — `netlify deploy --dir=assets` only ever sees the `assets/` directory, and `assets/_headers` is the sole source of truth for response headers (there's no `_redirects` file; the old `/api/*` redirect in `netlify.toml` was unused dead config, confirmed via repo-wide grep before removal).

## Architecture

### Fetch → store → publish

- `src/feed_fetcher.py` is the entry point. It skips re-running the same day unless `--force` is passed (checked via `was_executed_today` in the DB), downloads each feed listed in `feeds_config.yaml`, builds a combined pandas DataFrame, upserts it into SQLite, then regenerates every JSON asset from the DB.
- `src/regenerate_assets.py` re-runs just the DB → JSON asset generation step (metadata + all chunk types), without re-fetching. Use this after manually editing DB rows (e.g. after image postprocessing).
- `src/feed_postprocess_images.py` finds DB rows with no `image` and scrapes one from the article URL (`src/feeds/image_postprocessor.py`).

### Fetching feeds (`src/feeds/fetcher.py`, `src/utils/*`)

Most sources are standard RSS parsed with `feedparser`. A handful of sites don't expose usable RSS and instead have a dedicated Playwright/BeautifulSoup scraper in `src/utils/` (`wired.py`, `elpais.py`, `euronews.py`, `elcomercio.py`, `lanacion.py`, `cnnespanol.py`, `tiktok_scraper.py`) that returns a feedparser-shaped object. `fetch_feed()` dispatches to the right scraper based on `category`/URL via each module's `is_*_feed()` predicate — add new custom-scraped sources by writing a new `utils/<site>.py` with `scrape_*` + `is_*_feed` and wiring it into `fetch_feed`.

Raw fetched feeds are cached as `feeds_data/<category>_feed_<YYYY-MM-DD>.json` for the day (`src/feeds/saver.py`); a feed already fetched today is skipped unless `--force`.

### DataFrame building (`src/feeds/dataframe_builder.py`)

Normalizes every feed entry (regardless of source) into a common row shape: `id` (deterministic UUID5 from stable fields), `title`, `link`, `pubDate` (standardized to ISO 8601 via `dateutil`), `description`, `author`, `sourceTitle/Url/Category/Type/Country`, `content`, `image`, `isShortVideo`. Per-source-type enrichment happens here too, e.g. `utils/arxiv.py` (abstract extraction), `utils/youtube.py` (thumbnail + Shorts detection), `utils/tiktok.py` (thumbnail), `utils/xataka.py` (first-image extraction).

### Database (`src/database/`)

`connection.py` wraps **SQLite** (`data/feeds.db`, hardcoded, WAL mode) as a context manager. The `feeds` table has a generated `pubDate_parsed` column (indexed) used for the "months back" filtering. `operations.py` (~900 lines) holds all queries: insert-with-dedup-by-`id`, `get_metadata_from_db`, execution-log tracking (`was_executed_today`/`register_execution`), and the chunk-query helpers used below. `src/database/backup.py` is dead code from the MySQL era (never imported anywhere) — the real DB backup path is the Google Drive `rclone` sync described in Scheduling.

### Asset generation (`src/feeds/*_generator.py`)

All three generators query the DB filtered by `feeds_months_back` (from `feeds_config.yaml` `config:`) and write paginated JSON files (`ITEMS_PER_CHUNK = 30`, capped by `config.max_chunks_per_category`) into `assets/`:
- `chunk_generator.py` — one `-all` sequence per `sourceType` (e.g. `notice-all-chunk-0.json`), respecting `exclusions.chunks_all` in `feeds_config.yaml`.
- `category_chunk_generator.py` — one sequence per `sourceType` + `category` pair (e.g. `notice-Xataka-chunk-0.json`).
- `shorts_chunk_generator.py` — cross-source `shorts-all-chunk-*.json` for rows where `isShortVideo=1`.
- `metadata_generator.py` — writes `assets/metadata.json`, an index describing available sources/categories/counts.

`utils/cleanup.py` deletes stale chunk files left over from a previous run (e.g. a category that now has fewer chunks than before).

### Config (`feeds_config.yaml`)

Single source of truth for what gets fetched: a list of `{url, title, category, sourceType, country}` entries, plus top-level `config:` (`feeds_months_back`, `max_chunks_per_category`) and `exclusions.chunks_all` (categories left out of `-all` aggregate chunks/stats per `sourceType`). `src/config/loader.py` reads these. Adding a new feed source is usually just adding an entry here — a custom scraper is only needed if the site has no usable RSS feed.

## Known doc/code drift

- `README.md` (Spanish) describes an older automation layout (`auto_feeds.sh`, `setup_automation.sh`, `.auto_feeds.config`, `AUTOMATION.md`) that no longer exists, and still describes the old git-commit-then-push-triggers-Netlify flow — actual flow is the GitHub Actions workflow calling `run.sh --auto`, which deploys via `netlify-cli` directly (see Scheduling above). README not yet updated to match.
- `docker-compose.yml`/README/`docker/requirements.txt` (`mysql-connector-python`, `default-mysql-client` in the Dockerfile) still reference MySQL/RSSHub, but `docker-compose.yml` only defines `feed_collector` and `connection.py` only implements SQLite. The dead `DB_*`/`MYSQL_*`/`RSSHUB_*` vars were removed from `.env`; if you see the Dockerfile still installing a MySQL client or `docker/requirements.txt` still listing `mysql-connector-python`, that's leftover too, just not yet cleaned up.
- `.env` is gitignored now (it previously was tracked with placeholder values only — no real secrets were exposed, but don't assume that's still true going forward; treat it as local-only).
- `README.md` still links to `netlify.toml` as deploy config — that file was removed (see Scheduling above); README not yet updated.
