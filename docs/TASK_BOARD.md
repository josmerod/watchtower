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
| T-005 | todo | P0 | Remove 49 MB of tracked binaries in `src/miners/asf-winonly/` | infra | 131 binary files (.exe/.dll) tracked in git, incl. `ArchiSteamFarm.exe` (~50 MB). Bloats every clone. `git rm -r --cached src/miners/asf-winonly/`, add to `.gitignore`, and if still needed at runtime fetch via release artifact / git-LFS. Pre-commit `check-added-large-files` only catches *new* files, so this must be done manually. |
| T-006 | todo | P0 | Fix 12 broken test modules (collection `ImportError`s) | quality | `uv run pytest` is interrupted by 12 collection errors. Root causes: stale imports referencing renamed/removed symbols — e.g. `TrendDirection`/`TrendIndicator` gone from `src/analytics/models.py`, `src.models.ai_platforms` module missing. Files: `Tests/{analytics,dashboard,e2e,etl,integration,models,performance,unit,web}/...`. Confirm on `main` (pre-existing). Either fix the imports or delete dead tests. |
| T-001 | todo | P1 | Clear 5 stale remote feature/fix branches | infra | `feat/api-pagination-offset-limit`, `fix/api-async-io-to-thread`, `fix/proxy-manager-session-cache`, `fix/shell-true-removal`, `perf/github-api-threadpool`. Merge or close each; delete the remote branch. |
| T-002 | todo | P1 | Wire CI (`.github/workflows/ci.yml`) to run `ruff check` + `ruff format --check` on PRs | quality | Currently CI only does `py_compile` on 2 files + `pytest` (continue-on-error). Add a lint gate so ruff failures fail PRs. |
| T-007 | todo | P1 | Extract hardcoded User-Agent strings into a shared constant | etl | 34 files in `src/` hardcode `Mozilla/...` UA strings (lifetimo, humblebundles, coursera, audible, bensbites, etc.). Centralize in one helper/constant (e.g. `src/utils/http.py`) so UA rotation/updates happen in one place. |
| T-008 | todo | P2 | Add `.github/dependabot.yml` for automated dependency updates | infra | No dependabot config exists. Add one for `uv` (pip ecosystem), github-actions, and docker base images. |
| T-009 | todo | P2 | Move ~20 root-level scripts into `scripts/` | infra | `audit_stale_sources.py`, `fetch_coda_tasks.py`, `finish_deployment*.py`, `get_logs.py`, `restart_*.py`, `sync_to_coda.py`, etc. clutter the repo root. Relocate to `scripts/` (keep the documented entry points: `run_watchtower_dashboard.py`, `run_all_etl_orchestrator.py`, `setup.py`, `watchtower.py`). |
| T-010 | todo | P2 | Reduce `except Exception` overuse (798 occurrences in `src/`) | quality | Broad exception swallowing hides bugs. Audit high-risk call sites (ETL `run()`, API handlers) and narrow to specific exceptions or re-raise. Many are `# noqa: BLE001` in dashboards — leave those, focus on `src/etl` + `src/api`. |
| T-011 | todo | P3 | Replace ad-hoc `print()` with logging (438 in `src/`) | quality | `src/` has 438 `print()` calls that bypass the structured logger (`src/utils/logging.py`). Migrate gradually, prioritizing ETLs and long-running jobs where log levels matter. |
| T-003 | todo | P2 | Work down mypy errors in `src/` (433 across 104 files) | quality | Hotspots: `src/data_quality/deduplication.py`, `src/etl/anime/mal_etl.py`, `src/utils/file_system.py`, `src/utils/logging.py`. Goal: get `uv run mypy src` green so the manual pre-commit hook can be promoted to blocking. |
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
