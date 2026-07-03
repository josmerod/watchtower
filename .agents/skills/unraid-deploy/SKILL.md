---
name: unraid-deploy
description: Build, ship, restart, and debug the Watchtower container on the Unraid server. Use whenever the user wants to deploy, redeploy, push an update, restart the remote container, check remote logs, verify the deployment, or troubleshoot why the dashboard/ETLs are stale or down on Unraid. Trigger on phrases like "deploy to unraid", "ship it", "redeploy", "restart watchtower", "check remote logs", "is the deploy working", "force restart".
---

# Unraid Deploy

Standard workflow for getting Watchtower onto the Unraid server and keeping it
healthy. The repo has two ways to ship code: a Python deployer (`deploy.py`) and
a PowerShell alternative (`deploy.ps1`). **Prefer `deploy.py`** unless the user is
on PowerShell and `paramiko` isn't available — the Python path reads secrets from
`.env` and is the maintained one.

## Hard prerequisites — check these FIRST

1. **`.env` must exist** with at least `UNRAID_HOST`, and either
   `UNRAID_PASSWORD` or an SSH key at `~/.ssh/id_ed25519`.
   ```bash
   grep -E '^UNRAID_(HOST|USER|PASSWORD)=' .env   # .env is gitignored — never print the whole file
   ```
   If missing, tell the user exactly which vars to set. Do **not** invent values.
2. **Working tree should be clean-ish.** `deploy.py` archives `src`, `deployment`,
   `config`, `utils`, `Tests`, `pyproject.toml`, `uv.lock`, `run_all_etl.sh`,
   `run_watchtower_dashboard.py`, `run_all_etl_orchestrator.py`. Uncommitted
   changes in those paths ship too — warn the user before deploying if there are
   surprises in `git status`.
3. **Never deploy with a broken lockfile.** Run `uv lock --check` first.

## What the deployment actually does

`deployment/deploy.py` (read it before changing deploy behavior) — on each run:

1. Tars the include-list above into `$TEMP/watchtower_src.tar.gz` (excludes
   `.git`, `.venv`, `__pycache__`, `.env`, `*.pyc`).
2. SSHes to `UNRAID_HOST` (paramiko), uploads the tarball to `/tmp/`.
3. On the remote host: extracts to `/tmp/watchtower_deploy`, seeds
   `/mnt/user/appdata/watchtower/data/` from any bundled `data/` with
   `cp -rn` (no-clobber — historical data is preserved), runs
   `docker build -t watchtower -f deployment/Dockerfile .`, then
   `docker rm -f watchtower` and re-`docker run`.
4. Container is started with these mounts/ports — match them if you ever edit the
   run command:
   - `-p 7777:7780` (host dashboard **7777** → container Dash app **7780**)
   - `-p 45714:45714` (API / Hermes cron)
   - `-v /mnt/user/appdata/watchtower/data:/app/data`
   - `-v /mnt/user/appdata/watchtower/logs:/app/logs`
   - `-e TZ=Europe/Madrid -e BROWSERLESS_ENDPOINT=ws://REDACTED_LAN_IP:3000`
   - `--restart unless-stopped`
5. Cleans up `/tmp/watchtower_deploy` and the tarball.

> **Two Dockerfiles exist.** `deployment/Dockerfile` (used by `deploy.py`'s
> `-f deployment/Dockerfile`) is the *remote* build that runs under supervisor and
> is the source of truth for production. The root `Dockerfile` + `docker-compose.yml`
> are a separate local/compose path. Don't conflate them.

## Commands

| Task | Command |
| :--- | :--- |
| **Deploy / redeploy** | `uv run --with paramiko python deployment/deploy.py` |
| **Force restart** (no rebuild) | `uv run --with paramiko python deployment/force_restart.py` |
| **Remote logs** | `uv run --with paramiko python scripts/debug_remote_logs.py` |

`paramiko` is a deploy-time extra — always invoke it with `uv run --with paramiko`
so you don't need to permanently add it to `pyproject.toml`.

## Decision tree: which command?

- "Deploy this", "ship the update", "publish to unraid" → `deploy.py` (full rebuild).
- "Just restart it", "it's hung", "bounce the container" → `force_restart.py`
  (rebuilds nothing, just `docker restart watchtower`).
- "Why are ETLs stale / what's the error" → `debug_remote_logs.py`, then read the
  scheduler/dashboard/api logs.

## After a deploy — verify before declaring success

A green `deploy.py` exit only means the container started. Confirm it's actually
serving:

1. Health endpoint: `curl -fsS http://<UNRAID_HOST>:45714/health` (must return 200).
   The Dockerfile's `HEALTHCHECK` hits this same path.
2. Container is up and not restarting:
   `docker ps --filter name=watchtower` (via SSH if needed).
3. Data freshness — pick a known ETL output and check its mtime, e.g.
   `stat -c '%y' /mnt/user/appdata/watchtower/data/news/techcrunch_latest.json`
   (this is exactly what `force_restart.py` checks).

If health is red after ~40s (the compose `start_period`), pull logs before
declaring failure — most post-deploy issues are a crashed supervisor program
(visible in `/mnt/user/appdata/watchtower/logs/*.log`) or a stale Playwright
browser binary.

## The running container's process model

Supervisor runs three programs (see `deployment/supervisord.conf`) — know these
when debugging, because "it's down" usually means *one* of them:

- `dashboard` → `uv run python run_watchtower_dashboard.py` (port 7780)
- `etl_scheduler` → `uv run python deployment/etl_scheduler.py` (runs ETLs every
  2h, then `supervisorctl restart api` to reload fresh data — does **not** restart
  the dashboard, by design, to avoid disrupting users)
- `api` → `uv run uvicorn src.api.main:app --host 0.0.0.0 --port 45714`

Remote status: `docker exec watchtower supervisorctl status`.

## Safety rules

- **Never print the full `.env`** or echo `UNRAID_PASSWORD`. Grep for keys, never `cat`.
- **Never add `UNRAID_PASSWORD` (or any credential) to a script, commit message,
  or file.** The `.env` is the only place for it. `detect-secrets` runs in
  pre-commit as a backstop.
- The `/mnt/user/appdata/watchtower/data` volume holds **historical data**.
  `deploy.py` uses `cp -rn` precisely to avoid overwriting it — don't "fix" that
  to a clobbering copy.
- If `deploy.py` exits non-zero, surface the remote STDERR verbatim; don't guess.
