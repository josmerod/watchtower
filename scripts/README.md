# scripts/

Operational and one-off helper scripts. The documented application entry
points stay at the repository root:

- `run_watchtower_dashboard.py` — launch the Dash dashboard (primary).
- `run_all_etl_orchestrator.py` — run all ETL pipelines.

The launcher with subcommands (`dev`, `prod`, `etl`, `dashboard`, `service`…)
is `src/launcher/cli.py`. Dependencies come from `uv sync`.

Scripts here are organized loosely by purpose:

- **Deployment / remote ops**: `deploy_watchtower_direct.py`,
  `finish_deployment*.py`, `restart_container.py`,
  `restart_unraid_docker.py`, `start_unraid_docker.py`, `get_logs.py`,
  `debug_remote_logs.py`.
- **Install / validation**: `install_dev.py`, `install_watchtower.py`
  (`validate_project.py` removed 2026-11-25: it validated a requirements.txt
  that no longer exists — deps come from `uv sync`).
- **ETL runners (subset / specialty)**: `run_new_watchtower_etls.py`,
  `run_valencia_etls.py`, `run_remote_audible.py`.
- **Coda integration**: `fetch_coda_tasks.py`, `sync_to_coda.py`,
  `upload_new_tasks.py`.
- **Maintenance / utilities**: `audit_stale_sources.py`, `parse_cc.py`,
  `update_shortcuts.py`.

Run any of them from the repo root, e.g.:

```bash
uv run python scripts/install_dev.py
```
