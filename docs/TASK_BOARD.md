# Task Board

Single source of truth for actionable work on Watchtower. Edited in place by
humans and by the `task-board` skill (which iterates one task at a time).

## Conventions

- **One task per row.** Rows are sorted: `in-progress` first, then `todo` (by
  priority, oldest first), then `blocked`, then `done` (newest first).
- **Status:** `todo` · `in-progress` · `blocked` · `done`.
- **Priority:** `P0` (blocker / production down) · `P1` (high) · `P2` (medium) ·
  `P3` (nice-to-have).
- **Area:** `etl` · `dashboard` · `api` · `infra` · `quality` · `docs` · `sec`.
- **One task `in-progress` at a time.** Mark it before starting, flip to `done`
  only after verification (run the command, cite the output).
- **ID scheme:** `T-NNN`, zero-padded, never reused.
- Keep `Notes` terse — long design goes in a linked `docs/` file or a commit.

## Board

| ID | Status | Priority | Title | Area | Notes |
| :-- | :-- | :-- | :-- | :-- | :-- |
| T-001 | todo | P1 | Clear 5 stale remote feature/fix branches | infra | `feat/api-pagination-offset-limit`, `fix/api-async-io-to-thread`, `fix/proxy-manager-session-cache`, `fix/shell-true-removal`, `perf/github-api-threadpool`. Merge or close each; delete the remote branch. |
| T-023 | todo | P1 | Fix pre-existing test-body failures surfaced after T-006 | quality | Once the 12 collection `ImportError`s were fixed (T-006), ~89 FAILED + ~56 ERROR in previously-uncollectable suites became visible. Concentrated in: `Tests/etl/test_base_etl.py` (27), `Tests/etl/test_adhd_publications_etl.py` (16), `Tests/etl/test_mal_etl.py` (9), `Tests/web/test_dashboard_managers.py` (22 — `CourseDataManagerConfig`/`date_parser` API drift), `Tests/integration/test_search_integration.py` (7 — `highlight_matches` lowercases), `Tests/recommendations/*` (7), plus Playwright E2E errors (`test_recommendations_e2e`, `test_filter_presets_e2e`, `test_customize_tabs_functionality`, `test_shortcuts_dragdrop`) that need a running dashboard. All are stale test bodies (API drift) or integration/E2E needing a server — not regressions. Triaged per-suite; fix or delete each. |
| T-024 | done | P1 | Fix latent `AlertRulesRepository.save_rule`/`delete_rule` bug | api | Done 2026-08-10: both methods called `self.load_rules()` (undefined on the repo) → swallowed `False`. Fixed by adding `_read_rules()` (uses `self.get()`, treats `RepositoryError`/missing file as empty), and `clear_cache()` after writes. Regression tests: `test_repo_save_rule_roundtrip`, `test_repo_save_rule_updates_existing`, `test_repo_delete_rule`. 14/14 notification tests pass; ruff + pre-commit green. |
| T-002 | todo | P1 | Wire CI (`.github/workflows/ci.yml`) to run `ruff check` + `ruff format --check` on PRs | quality | Currently CI only does `py_compile` on 2 files + `pytest` (continue-on-error). Add a lint gate so ruff failures fail PRs. |
| T-007 | todo | P1 | Extract hardcoded User-Agent strings into a shared constant | etl | 34 files in `src/` hardcode `Mozilla/...` UA strings (lifetimo, humblebundles, coursera, audible, bensbites, etc.). Centralize in one helper/constant (e.g. `src/utils/http.py`) so UA rotation/updates happen in one place. |
| T-008 | todo | P2 | Add `.github/dependabot.yml` for automated dependency updates | infra | No dependabot config exists. Add one for `uv` (pip ecosystem), github-actions, and docker base images. |
| T-009 | todo | P2 | Move ~20 root-level scripts into `scripts/` | infra | `audit_stale_sources.py`, `fetch_coda_tasks.py`, `finish_deployment*.py`, `get_logs.py`, `restart_*.py`, `sync_to_coda.py`, etc. clutter the repo root. Relocate to `scripts/` (keep the documented entry points: `run_watchtower_dashboard.py`, `run_all_etl_orchestrator.py`, `setup.py`, `watchtower.py`). |
| T-010 | todo | P2 | Reduce `except Exception` overuse (798 occurrences in `src/`) | quality | Broad exception swallowing hides bugs. Audit high-risk call sites (ETL `run()`, API handlers) and narrow to specific exceptions or re-raise. Many are `# noqa: BLE001` in dashboards — leave those, focus on `src/etl` + `src/api`. |
| T-011 | todo | P3 | Replace ad-hoc `print()` with logging (438 in `src/`) | quality | `src/` has 438 `print()` calls that bypass the structured logger (`src/utils/logging.py`). Migrate gradually, prioritizing ETLs and long-running jobs where log levels matter. |
| T-003 | todo | P2 | Work down mypy errors in `src/` (433 across 104 files) | quality | Hotspots: `src/data_quality/deduplication.py`, `src/etl/anime/mal_etl.py`, `src/utils/file_system.py`, `src/utils/logging.py`. Goal: get `uv run mypy src` green so the manual pre-commit hook can be promoted to blocking. |
| T-005 | done | P0 | Remove 49 MB of tracked binaries in `src/miners/asf-winonly/` | infra | Done 2026-08-04: `git rm -r src/miners/asf-winonly/` (218 files / 52 MB, incl. `ArchiSteamFarm.exe`), replaced subdir gitignore entries with `src/miners/asf-winonly/`. Confirmed unreferenced in `src/` + `Tests/`. `ruff`/`pre-commit` green; pytest 424 passed (pre-existing failures untouched). |
| T-006 | done | P0 | Fix 12 broken test modules (collection `ImportError`s) | quality | Done 2026-08-10: 0 collection errors; 644 tests collect. Deleted 6 dead modules (`test_base_etl_refactored.py` — module deleted dd455a0; `test_comprehensive_models.py` + `test_models_comprehensive.py` — fantasy models; 3 orphaned selenium E2E tests — project uses Playwright). Fixed imports: `test_search_integration.py`/`test_search_performance.py` (`utils.search_utils` → `search_utils`). Rewrote `test_trends.py` against the live `TrendAnalyzer.analyze_trends` API and `test_notifications_tab.py` against the live `NotificationsManager`/`AlertRulesRepository` (re-added `_get_rule_id` helper; removed `sys.modules` poisoning that cascaded into `test_backup_utils`/`test_dashboard_managers` failures). Surfaced ~145 pre-existing test-body failures → T-023; latent repo bug → T-024. `uv run pytest --collect-only` clean; `ruff`/`pre-commit` green. |
| T-004 | done | P1 | Consolidate lint tooling to Ruff-only + make mypy advisory | quality | Removed flake8 + black from dev deps, deleted `.flake8`, moved mypy to `manual` stage in `.pre-commit-config.yaml`. |
| T-012 | todo | P3 | Change courses tab name to Learning. Add freecodecamp to there and all applicable sources. Identify and add more tools if you think it will improve the finding of learning resources. Think about your own learning experience and what tools you would find useful. |
| T-013 | todo | P3 | Remove the Anime tab and all related stuff |
| T-014 | todo | P3 | Review on Arxiv Research the bugs on Arxiv, fix them and visually inspect the tab to see everything is working fine. Identify via research the relevant tags that should be added to accomplish the overall target of the watchtower platform there |
| T-015 | todo | P3 | Add a new Technology Radar tab. In this tab, move Google AI Blog, KDNuggets, Cloud Updates and whatever you see fit to there. Feel free to add other tools you might find relevant, i would like to keep track of the latest trends and updates in the technology space, specially on cloud, generative ai and artificial intellgence. Also add relevant sources on Self-hosting apps and tools, research properly to find the good sources. |
| T-016 | todo | P3 | On the scavenging tab, remove the Anime subtab. |
| T-017 | todo | P3 | Redesign the Ayudas Publicas tab in order to serve the purpose of helping the users identify personal or ngo related stuff. Focus locally on Burjassot, Valencia, Comunidad Valenciana and Spain, in that order of locality to global. Redesign the ETL properly to this end. |
| T-018 | todo | P2 | Redesign the Futuretools ETL scrapper to work again with relevant information |
| T-019 | todo | P1 | Review the sources, add new sources and ensure no data staleness on the Benchmarks tab |
| T-020 | todo | P4 | Review all the sources, and add proposals of new ones for each category. Add them to this task board. |
| T-021 | todo | P3 | Change the name from MS Applied Skills to MS Credentials. Review AWS Skill boost |
| T-022 | todo | P2 | Review the UI for the Videos tab. Remove duplicate channels (channels in two or more sections at the same time), Improve UI based on good UX experiences (eg ref. material design). |

## Changelog

- 2026-08-04 — Board created. T-001..T-003 seeded from repo scan; T-004 logged as done.
- 2026-08-04 — Project audit: added T-005 (49 MB tracked binaries — P0), T-006 (12 broken test modules — P0), T-007 (UA dedup), T-008 (dependabot), T-009 (root scripts cleanup), T-010 (broad except), T-011 (print→logging). Reprioritized so P0 repo-health issues surface first.
- 2026-08-04 — Closed T-005: removed 218 tracked files / 52 MB of vendored ArchiSteamFarm binaries from `src/miners/asf-winonly/` (unreferenced dead weight); gitignored the path.
- 2026-08-10 — Closed T-006: cleared all 12 collection `ImportError`s (644 tests now collect). Deleted 6 dead test modules, fixed 2 stale import paths, rewrote 2 stale test suites against live APIs. Surfaced T-023 (pre-existing test-body failures now visible) and T-024 (latent `AlertRulesRepository.save_rule` bug found via the rewritten notification tests).
- 2026-08-10 — Closed T-024: fixed `AlertRulesRepository.save_rule`/`delete_rule` (both called undefined `self.load_rules()`, swallowed to `False`). Added `_read_rules()` over `self.get()` + `clear_cache()` after writes; 3 regression tests added.
