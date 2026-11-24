---
name: unraid-deploy
description: Build, ship, restart, and debug the Watchtower container on the Unraid server. Use whenever the user wants to deploy, redeploy, push an update, restart the remote container, check remote logs, verify the deployment, confirm the deploy is healthy, or troubleshoot why the dashboard/ETLs are stale or down on Unraid. Trigger on phrases like "deploy to unraid", "ship it", "redeploy", "restart watchtower", "check remote logs", "is the deploy working", "is it up", "force restart", "bounce the container", "roll back the deploy".
---

# Unraid Deploy

One maintained path ships Watchtower to the Unraid server:
`deployment/deploy.py`. It archives the working tree, builds the image on the
server, swaps the container and reports success only when the new container is
healthy. `deployment/deploy.ps1` is **deprecated** (its header says so) — do
not use or update it.

## Before deploying

1. **Settings.** `.env` (gitignored) must define `UNRAID_HOST`. Optional:
   `UNRAID_USER` (default `root`), `BROWSERLESS_ENDPOINT` (defaults to the
   Unraid host on port 3000), and either `UNRAID_PASSWORD` or an SSH key at
   `~/.ssh/id_ed25519`. Check key **names** only — never print a value:
   ```bash
   grep -oE '^[A-Z_][A-Z0-9_]*=' .env
   ```
   If a name is missing, tell the user which one. Do not invent values.
2. **Uncommitted work ships.** The archive is the working tree, not a commit:
   review `git status --short` and confirm surprises with the user first.
3. **Lockfile.** `uv lock --check` must pass: the image is built with
   `uv sync --frozen`, which does not notice a stale lock.

## What a deploy does (`deployment/deploy.py`)

1. **Archive.** Only `INCLUDE_PATHS`: `src`, `deployment`, `config`, `Tests`,
   `pyproject.toml`, `uv.lock`, `run_all_etl.sh`,
   `run_watchtower_dashboard.py`, `run_all_etl_orchestrator.py`, `README.md`,
   `GEMINI.md` — minus `__pycache__`, `.pytest_cache`, `.ruff_cache`,
   `.mypy_cache`, `.venv`, `*.pyc` and `*.pyo`. Nothing else ships: not `data/`,
   `.env`, `secrets/` or `scripts/`.
2. **Build**, on the server in `/tmp/watchtower_deploy`: tags
   `watchtower:latest` as `watchtower:previous`, then
   `docker build -t watchtower -f deployment/Dockerfile .`.
3. **Swap** (`swap_command()`): `docker rm -f watchtower`, then `docker run`
   with `-p 7777:7780` (dashboard) and `-p 45714:45714` (API), binding `data`
   and `logs` under `/mnt/user/appdata/watchtower/`.
4. **Health gate.** Waits up to 4 minutes for the container's Docker health
   status. The `HEALTHCHECK` in `deployment/Dockerfile` curls
   `http://localhost:45714/health`, so the **API** is what is gated — not the
   dashboard or the ETL scheduler.
5. **Rollback.** If `docker run` fails or the container is not `healthy` when
   the wait ends: prints diagnostics, starts `watchtower:previous` again,
   exits 1.

**A script the container runs has to be in `INCLUDE_PATHS`** (or under one of
its directories). The scheduler and the orchestrator skip a missing script
with a warning and exit 0 — the symptom is silence, not an error.
`test_include_list_covers_every_boot_file` in `Tests/unit/test_deploy.py`
fails on a missing entry point; run the file after touching `INCLUDE_PATHS`,
`deployment/supervisord.conf` or the orchestrator's script list.

### Non-zero exit — what the operator must do

Read the last lines before acting:

| Printed | Meaning → action |
| :--- | :--- |
| `Build FAILED — the running container was not touched.` | Fix the build error in the streamed build output above this line. Production still runs the old image; the diagnostic blocks printed after it describe that old container. |
| `Deployment FAILED (health=...)` | The `--- container ---`, `--- supervisor ---` and `--- logs ---` blocks that follow hold the reason. The script then starts `watchtower:previous` — the image tagged `latest` before the build. Check for `Rollback done`: it only means the old container was started — the health gate is not repeated. `Rollback FAILED — start the container by hand` means nothing is running. |
| `No previous image to roll back to.` | Nothing was tagged `latest` before the build (first deploy). No rollback: the new container stays as it is — fix and redeploy. |
| `Error: ...` | The script itself failed (SSH, archive). Check the container's state. |

Every build re-points `watchtower:previous`, and a rolled-back deploy leaves
the bad image tagged `latest`. After a rollback, deploy the fix promptly: a
second failed deploy in a row rolls back to the first failure's image.

## Commands

| Use when | Command |
| :--- | :--- |
| Shipping a code change | `uv run --with paramiko python deployment/deploy.py` |
| Several programs are down, no rebuild wanted | `uv run --with paramiko python deployment/force_restart.py` |
| One program is hung | `docker exec watchtower supervisorctl restart dashboard` (or `api`) |
| A source is stale and you need the server logs | `uv run --with paramiko python scripts/debug_remote_logs.py` |

`paramiko` is a deploy-time extra, hence `--with paramiko`; the command is the
same in Git Bash, PowerShell and cmd. The `docker exec` line runs on the
server: prefix it with `ssh <user>@<host>`. `force_restart.py` and
`debug_remote_logs.py` accept no SSH key (they need `UNRAID_PASSWORD`) and
run no health check.

## Restarts start a full ETL cycle

Every container start — `deploy.py`, `force_restart.py`, a manual
`docker restart` — launches a **full ETL cycle** immediately:
`deployment/etl_scheduler.py` runs `./run_all_etl.sh` on start (109 scripts,
4 workers), again 2 hours after each cycle, and restarts `api` after each. So
a restart kills a cycle in flight, hits every live source again and takes the
dashboard and API down meanwhile. Avoid it while a cycle is running or a
source is rate-limiting; when only one program is hung, restart just that
program. A restart never loads new code — it is baked into the image.

## After a green deploy

Exit 0 means the API answered `/health` — nothing more. Supervisor runs
`dashboard`, `etl_scheduler` and `api` (`deployment/supervisord.conf`); their
logs and the per-ETL logs are under `/mnt/user/appdata/watchtower/logs/`.
Confirm before declaring success:

```bash
ssh <user>@<host> docker exec watchtower supervisorctl status   # all three RUNNING
curl -fsS -o /dev/null http://<host>:7777/                      # dashboard answers
```

## Rehearsing a risky change

`.github/workflows/docker-build.yml` does this on every pull request: it
builds the image from the same archive and boots only the API until `/health`
answers. To do it by hand, on a machine with Docker, from the repo root:

```bash
uv run --no-project --python 3.11 --with python-dotenv python -c "from deployment import deploy; deploy.create_archive('watchtower_src.tar.gz')"
mkdir -p context && tar -xzf watchtower_src.tar.gz -C context
docker build -f context/deployment/Dockerfile -t watchtower:candidate context
docker run -d --name watchtower-smoke -p 45715:45714 --entrypoint uv watchtower:candidate run uvicorn src.api.main:app --host 0.0.0.0 --port 45714
for _ in $(seq 1 30); do curl -fsS http://localhost:45715/health && break; sleep 2; done
docker logs --tail 40 watchtower-smoke
docker rm -f watchtower-smoke; rm -rf context watchtower_src.tar.gz
```

The loop gives the API 60 s. Whatever happens, the `docker logs` line prints
the container's output before it is removed. `--entrypoint uv` replaces the
image's default start — supervisor, whose scheduler launches a full ETL cycle
on every start. Tag the image `watchtower:candidate`, never plain
`watchtower`: on the server that moves `latest`, and the next deploy would
tag that untested image as `previous`. Then run the real deploy.

## The compose recipe is different

`docker-compose.yml` and the root `Dockerfile` are a separate path. The
commands above assume the production container:

| | `deployment/deploy.py` | Compose |
| :--- | :--- | :--- |
| Container | `watchtower` | `watchtower-app` |
| Dashboard port | host **7777** → container **7780** | `7777:7777` (`WATCHTOWER_DASHBOARD_PORT=7777`) |
| Image contents | the deploy archive (`COPY . .`) | a hand-picked file list, **plus `secrets/`** |
| Settings | `UNRAID_*` stay on the dev machine | `env_file: .env` passes the whole file to the container |

## Backups do not run in production

`run_backup.py` is **deliberately not shipped** (`DELIBERATELY_NOT_SHIPPED` in
`Tests/unit/test_deploy.py`): it would zip `data/` into the container's own
layer, and the container has no backups volume. The orchestrator runs it after
each cycle only if the file exists, so production skips it silently. Do not
add it to `INCLUDE_PATHS`, and do not report backups as working.

## Safety rules

- Never print `.env` or a value from it; list key names only (command above).
  `deploy.py` itself echoes the host while connecting — keep its output out of
  commits and issues.
- Never put a credential in a script, commit message or file. `detect-secrets`
  runs in pre-commit as a backstop.
- The `data` volume holds **historical data**. A deploy never overwrites it:
  `data/` is not shipped, and the one copy step in `build_command()` is a
  no-clobber `cp -rn` that only runs for an archive carrying a top-level
  `data/` directory.
- If `deploy.py` exits non-zero, report its output verbatim; do not guess.
