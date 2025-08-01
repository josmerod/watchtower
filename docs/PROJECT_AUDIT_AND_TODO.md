### Watchtower Project Audit and Refactor Plan (Aug 2025)

This document is a comprehensive status review of the Watchtower platform and a prioritized, actionable refactor plan. It targets reliability of the periodic ETL set and quality of the Dash dashboard that consumes their outputs.

---

## Executive Summary

Overall, the project is rich in features and data sources, but it suffers from inconsistent data contracts, duplicated utilities, a mix of legacy and modern patterns, and several correctness bugs that surface as “No Title”, “No data”, and empty charts in the UI. The ETL layer is partly unified under `BaseETL`, but many modules still bypass it or emit heterogeneous schemas. Logging and configuration are present but inconsistently applied due to import path mistakes and ad‑hoc utilities.

The plan below focuses first on correctness and schema stability (P0), then on robustness and observability (P1), followed by performance and DX/cleanup (P2/P3).

---

## Observed Runtime Symptoms (from the current dashboard)

- Shortcuts tab: “No shortcut data loaded or available.”
- News tab:
  - “No Title” rows for Product Hunt and Git Trends sources.
  - Data present for some sources, but inconsistent labeling and dates.
- Games tab:
  - “Juegos Gratuitos: No giveaways data currently available or failed to load.”
  - Game bundles/deals load fine.
- Courses tab: Coursera/Udemy panes show empty content despite files existing.
- AI Platforms tab: Many cards show “No data”; only AI Model Monitoring displays a count.
- ArXiv Research tab: Top charts appear blank, despite many JSON files present.

These symptoms map to concrete bugs and contract mismatches detailed below.

---

## Priorities

- P0: Break/fix items that block correctness of the dashboard data or ETL runs.
- P1: Reliability/observability improvements that stop regressions and ease ops.
- P2: Performance/architecture cleanups that reduce tech debt and load time.
- P3: Nice-to-haves and UX/Docs polish.

---

## P0 – Critical Fixes (Correctness/Data Contracts/Crashes)

- [ ] Fix broken import in logging utilities so structured logging + settings apply globally
  - Cause: `src/utils/logging.py` does `from config.settings import get_settings` (missing `src.`) causing fallback basic logging.
  - Action: Change to `from src.config.settings import get_settings` and add a minimal import guard test.

- [ ] Unify dashboard data path utilities and remove per-file ad-hoc path hacks
  - Cause: `src/web/dashboard/components/videos_tab.py` redefines `get_data_path()` differently from `src/web/dashboard/utils.py` → inconsistent resolution.
  - Action: Use `src/web/dashboard/utils.py` across all components. Delete duplicates.

- [ ] Fix Videos tab crash
  - Cause: `create_initial_video_cards()` builds list but returns `video_cards` which is not defined; list comprehension result is unused.
  - Action: Assign the list to `video_cards` and return it.

- [ ] Normalize News tab schema mapping (title/url/date/source)
  - Cause: Product Hunt JSON uses `name` for title; GitHub Trends uses repo fields; News table only reads `title` → “No Title”.
  - Action: Add robust fallback mapping in `news_tab.py`:
    - Title: `title` | `name` | `full_name`
    - URL: `url` | `link` | `html_url` | `website`
    - Date: `published_at` | `published_date` | `created_at` | `updated_at` | `time` | `pubDate`
    - Source: default to configured source name if missing.

- [ ] Ensure every ETL writes stable “latest” artifacts used by the dashboard
  - Product Hunt: Dashboard expects `data/product_hunt/product_hunt_latest.json` (OK in newer ETL); verify it exists on disk after runs.
  - Git Trends: Dashboard expects `data/github_trends/github_trends_latest.json` (OK in ETL); verify.
  - ArXiv: Dashboard config mixes specific timestamped files and `arxiv_papers_latest.json`; standardize on `*_latest.json` + update config to use them.

- [ ] Games giveaways mismatch
  - Cause: Games tab loads `data/games/giveaways.json` while dedicated Giveaways tab uses `data/giveaways/free_games.json` + others.
  - Action: Pick one canonical contract (recommended: `data/giveaways/*_latest.json`) and change Games tab to read the canonical giveaways dataset; update ETL writers to emit the canonical file.

- [ ] AI Platforms tab broken config
  - Cause: In `ai_platforms_tab.py`, `github_copilot` entry is missing a `path` value; several platform paths don’t exist (e.g., google_gemini directory not found).
  - Actions:
    - Provide valid paths for each card and ensure corresponding ETLs write `*_latest.json`.
    - Temporarily hide cards without data until ETLs exist.

- [ ] Remove/repair duplicate Product Hunt ETLs
  - There are two modules: a Playwright-based `news_get_product_hunt.py` (contains a syntax error) and a “GraphQL” `news_get_producthunt.py` used by run scripts.
  - Action: Keep one implementation, fix/validate it, and delete/rename the other to avoid confusion.

- [ ] Shortcuts tab shows empty
  - Action: Validate `data/shortcuts/predefined_shortcuts.json` format against loader (supports both legacy `{ categories: [...] }` and newer `{ "Category": [...] }`). Add schema validation and a small sample fallback if file is missing.

- [ ] `src/web/dashboard/app.py` has dead code in dynamic tab renderer
  - Action: Remove branches for non-existent tabs (`tab-crypto`, `tab-travel`, `tab-watchers`) to avoid confusion and potential callback mismatches.

---

## P1 – Reliability, Observability, and Data Contracts

### Data Contracts and Validation

- [ ] Define canonical dashboard contracts per domain in `src/models/` (Pydantic):
  - News: `NewsArticleModel` (already exists) → enforce at transform stage; add light adapter for each source in UI as backup.
  - Product Hunt: `ProductHuntModel` with `title`, `url`, `published_at`, `summary`, `votes`, `source` normalized.
  - Git Trends: repo mapping with `title` = `full_name`, `url` = `html_url`, `language`, `updated_at`.
  - Giveaways: unify `title`, `url`, `platform`, `category`, `availability`, `promotion_end`, `is_active`.
  - ArXiv: ensure `EnhancedArxivPaperModel` fields are consistently present in `*_latest.json`.

- [ ] Add “contract validators” per ETL in the transform/load stage
  - Use Pydantic validation to drop/repair invalid rows and record counts of fixes.

- [ ] Add an automated post-run sanity check
  - After each ETL run, verify `*_latest.json` exists, is non-empty, and conforms to model → produce a simple JSON summary.

### Orchestration and Scheduling

- [ ] Replace ad-hoc batch scripts with a single orchestrator (Prefect recommended in README)
  - Define flows per domain (news, games, arxiv, ai-platforms) with retries/backoff and concurrency caps.
  - Emit flow run metadata to `data/metrics/etl_runs_latest.json` for the dashboard.

- [ ] Implement retention policy (cleanup of timestamped files)
  - Use `ETLConfig.cleanup_old_data_days` to purge older artifacts per directory.

### Logging, Errors, and Metrics

- [ ] Standardize logger names: `ETL.<name>`, `Watcher.<name>`, `Web.<component>`
- [ ] Enable structured logging globally after fixing import
- [ ] Add per-run performance metrics via `get_performance_logger` across ETLs and watchers
- [ ] Ensure exception utilities attach context (`etl_name`, row counts, file paths)
- [ ] Add a compact log viewer in the dashboard (tail last N lines per ETL)

---

## P2 – Performance and Architecture Cleanups

- [ ] Single source of truth for paths
  - Replace manual `os.path` in dashboard components with `utils.get_data_path` or `get_settings().get_data_path`.
- [ ] Cache heavy UI loads (News, Videos) for N seconds
  - Add in-memory TTL cache per-tab to avoid re-reading dozens of files on each tab switch.
- [ ] Aggregate News
  - Add an ETL or service to pre-merge normalized news into `data/news/news_all_latest.json` for O(1) UI load.
- [ ] Remove duplicated or legacy modules
  - Delete stale Streamlit-only utilities from the Dash path; move truly shared code to `src/utils`.
- [ ] Consolidate giveaways
  - Merge Games giveaways and universal Giveaways into one canonical dataset with category tags (`games`, `education`, `software`).

---

## P3 – Developer Experience, Tests, and Docs

### Testing

- [ ] Add Dash component tests for: `news_tab.py`, `ai_platforms_tab.py`, `shortcuts_tab.py`, `giveaways_tab.py`, `courses_tab.py`
- [ ] Contract tests: each ETL must emit valid `*_latest.json` that loads into its Pydantic model
- [ ] Smoke test: start dashboard, hit health endpoint, assert tabs render without exceptions

### CI/CD & Quality Gates

- [ ] Pre-commit with ruff + mypy + pytest
- [ ] GitHub Actions (or local runner) to run unit tests and linting on PRs

### Documentation

- [ ] Update `docs/dashboard_guide.md` with the new data contracts and where the UI reads them
- [ ] Remove/replace references to deprecated scripts; keep one canonical launcher per OS using UV

---

## Root-Cause Notes and File Pointers

- Logging path bug prevents global logging policy
  - `src/utils/logging.py` imports `config.settings` instead of `src.config.settings`.

- Videos tab runtime bug
  - Undefined `video_cards` return variable; list build result unused.

- AI Platforms config missing paths
  - `src/web/dashboard/components/ai_platforms_tab.py`: incomplete `AI_PLATFORMS_CONFIG` (e.g., `github_copilot`).
  - Missing `data/google_gemini/` directory; hide or implement ETL.

- News title mapping
  - Product Hunt data uses `name`; GitHub Trends repos use `full_name`/`html_url`; UI expects `title`/`url`.

- Giveaways duplication
  - Games tab reads `data/games/giveaways.json` while Giveaways tab reads `data/giveaways/*.json`.

- Dead code in `app.py`
  - Dynamic tab callback references non-existent tabs; keep only actual tabs.

---

## Detailed Action Checklists

### A. Contracts and UI Adapters (P0/P1)

- [ ] Write a `news_normalize(article: dict) -> dict` in `news_tab.py` with fallbacks:
  - [ ] Map `name`→`title` (Product Hunt)
  - [ ] Map `full_name`→`title` and `html_url`→`url` (Git Trends)
  - [ ] Robust date parsing (already present) + add `updated_at` fallback
  - [ ] Ensure `source_display_name` is always set

- [ ] Switch ArXiv Research tab to only use `*_latest.json` and delete hard-coded dated filenames from config

- [ ] Canonicalize giveaways
  - [ ] Adopt `data/giveaways/*_latest.json` convention
  - [ ] Make Games tab read from the canonical giveaways dataset
  - [ ] Ensure Enhanced Free Games ETL writes the canonical file

### B. ETL Reliability (P1)

- [ ] Ensure every ETL inherits `BaseETL` (or clearly justify exceptions)
- [ ] Add checkpointing where long-running
- [ ] Add per-ETL summary JSON (`{records_extracted, transformed, loaded, errors}`)
- [ ] Add retention/purge step based on `cleanup_old_data_days`

### C. Logging/Monitoring (P1)

- [ ] Fix logging import path and verify structured logs in file and console
- [ ] Add correlation IDs per ETL run, propagate to child logs
- [ ] Add a simple `/health` and `/metrics` (Prometheus or JSON) for the dashboard

### D. Dashboard Quality (P0/P2)

- [ ] Remove dead `app.py` branches and unused callbacks
- [ ] Standardize on `utils.get_data_path` and remove any inline path guessing
- [ ] Add TTL caches (e.g., 60–300s) for heavy loaders (News, Videos)
- [ ] Add graceful empty-state cards showing last successful ETL time if available

### E. Cleanup & Consistency (P2/P3)

- [ ] Delete deprecated Product Hunt ETL duplicate and keep one maintained version
- [ ] Remove remnants of legacy Streamlit references from Dash codepaths (docs can keep a link to legacy app)
- [ ] Consolidate watchers to the enhanced watcher base or clearly separate legacy vs enhanced

---

## Security and Secrets

- [ ] Audit environment variable usage in ETLs (tokens/keys) and centralize through `Settings`
- [ ] Validate that no secrets are written to repository or logs

---

## Acceptance Criteria (Definition of Done for P0/P1)

- [ ] Dashboard tabs render without warnings/errors:
  - [ ] News (Product Hunt + Git Trends show proper titles and links)
  - [ ] Games (giveaways list populated if data exists)
  - [ ] Courses (Coursera/Udemy tables show rows from existing files)
  - [ ] AI Platforms (cards hide if data missing; those with data show counts)
  - [ ] ArXiv (charts show distributions once data present)
- [ ] `*_latest.json` exists and validates for each ETL the UI depends on
- [ ] Structured logs enabled globally (console + rotating file)
- [ ] Orchestrator can run the daily ETL set with retries and produce a run summary

---

## Suggested Milestones

1) Week 1 – P0 fixes: logging import, videos tab crash, news mapping, canonical latest files, app dead code removal, giveaways unification decision
2) Week 2 – P1 contracts + orchestrator + retention + dashboards caching
3) Week 3 – Tests, CI, docs, and cleanup of duplicates/legacy

---

## Notes on UV and Execution

The project’s migration to UV is solid. Keep using `uv run` for all scripts and ensure the orchestrator entry points also go via UV. Continue to avoid system Python leakage.

---

## Quick Wins (High ROI in < 1 day)

- [ ] Fix `src/utils/logging.py` import path
- [ ] Repair `videos_tab.py` return value bug
- [ ] Add `name`/`full_name` fallbacks in News tab
- [ ] Hide AI Platform cards without data; fill valid `path` for those with data
- [ ] Remove dead `app.py` branches
- [ ] Switch ArXiv tab to `*_latest.json` only

---

If any of the above observations are incorrect or out-of-date, we’ll update this plan accordingly after a short validation pass on your environment.


