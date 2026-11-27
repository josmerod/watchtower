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
   API keys for the ETLs go in the same `.env`, under the names in the
   *Keys and variables the ETLs read* section of `.env.example`: the deploy
   forwards exactly those (see **Keys** below).
2. **Uncommitted work ships.** The archive is the working tree, not a commit:
   review `git status --short` and confirm surprises with the user first.
3. **Lockfile.** `uv lock --check` must pass: the image is built with
   `uv sync --frozen`, which does not notice a stale lock.

## What a deploy does (`deployment/deploy.py`)

1. **Archive.** Only `INCLUDE_PATHS`: `src`, `deployment`, `config`, `Tests`,
   `pyproject.toml`, `uv.lock`, `run_all_etl.sh`,
   `run_watchtower_dashboard.py`, `run_all_etl_orchestrator.py`,
   `run_backup.py`, `README.md`,
   `GEMINI.md`, `changelog.json` — minus `__pycache__`, `.pytest_cache`,
   `.ruff_cache`, `.mypy_cache`, `.venv`, `*.pyc` and `*.pyo`. Nothing else
   ships as a file: not `data/`, `.env`, `secrets/` or `scripts/`. Text files
   are normalized to LF as they are packed, so the deployed bytes match the
   commit even on a checkout with `core.autocrlf=true`.
2. **Keys.** The names in `CONTAINER_ENV_KEYS` that are set locally are
   written to `/mnt/user/appdata/watchtower/container.env` — owner-only,
   next to the `data` and `logs` volumes, outside the build context — and
   the container gets them with `--env-file`. With none set, that file is
   removed, so a key dropped or rotated locally does not linger on the
   server. The deploy prints the **names** it forwards, never the values.
   `UNRAID_*` are not on the list: the SSH credentials stay on this machine.
3. **Build**, on the server in `/tmp/watchtower_deploy`: tags
   `watchtower:latest` as `watchtower:previous`, then
   `docker build -t watchtower -f deployment/Dockerfile .`.
4. **Swap** (`swap_command()`): `docker rm -f watchtower`, then `docker run`
   with `-p 7777:7780` (dashboard) and `-p 45714:45714` (API), binding `data`,
   `logs` and `backups` under `/mnt/user/appdata/watchtower/` and, when
   variables are forwarded, `--env-file`.
5. **Health gate.** Waits up to 4 minutes for the container's Docker health
   status. The `HEALTHCHECK` in `deployment/Dockerfile` curls
   `http://localhost:45714/health`, so the **API** is what is gated — not the
   dashboard or the ETL scheduler.
6. **Rollback.** If `docker run` fails or the container is not `healthy` when
   the wait ends: prints diagnostics, starts `watchtower:previous` again,
   exits 1. Should that rollback fail while variables were forwarded, it is
   retried once without `--env-file`: a container without API keys beats no
   container.

**A script the container runs has to be in `INCLUDE_PATHS`** (or under one of
its directories). The scheduler and the orchestrator skip a missing script
with a warning and exit 0 — the symptom is silence, not an error. So has a
repo-root file the code reads by name: without `changelog.json` the dashboard's
🆕 modal renders nothing and nothing fails. `Tests/unit/test_deploy.py` fails
on a missing entry point and on a named root file that does not ship; run the
file after touching `INCLUDE_PATHS`, `deployment/supervisord.conf`, the
orchestrator's script list, or a root file name quoted in the code.

**A key an ETL reads has to be on `CONTAINER_ENV_KEYS`.** The list is an
allowlist, so a new `os.getenv("NEW_KEY")` in an ETL changes nothing in
production until its name is added there and to `.env.example`.
`Tests/unit/test_deploy.py` fails on a variable the cycle reads that is not
forwarded; run it after adding a keyed source.

### Non-zero exit — what the operator must do

Read the last lines before acting:

| Printed | Meaning → action |
| :--- | :--- |
| `Build FAILED — the running container was not touched.` | Fix the build error in the streamed build output above this line. Production still runs the old image; the diagnostic blocks printed after it describe that old container. |
| `Deployment FAILED (health=...)` | The `--- container ---`, `--- supervisor ---` and `--- logs ---` blocks that follow hold the reason. The script then starts `watchtower:previous` — the image tagged `latest` before the build. Check for `Rollback done`: it only means the old container was started — the health gate is not repeated. `Rollback FAILED — start the container by hand` means nothing is running. |
| `No previous image to roll back to.` | Nothing was tagged `latest` before the build (first deploy). No rollback: the new container stays as it is — fix and redeploy. |
| `Error: could not create /mnt/user/appdata/watchtower/container.env on the server` | The owner-only file for the forwarded variables could not be created. Nothing was built or swapped: the running container was not touched. Check the appdata path and permissions. |
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
`deployment/etl_scheduler.py` runs `./run_all_etl.sh` on start (102 scripts,
4 workers), again 2 hours after each cycle, and restarts `api` after each. So
a restart kills a cycle in flight, hits every live source again and takes the
dashboard and API down meanwhile. Avoid it while a cycle is running or a
source is rate-limiting; when only one program is hung, restart just that
program. A restart never loads new code — it is baked into the image.

A cycle took 47 minutes in production (2026-11-24), and the 2 hours start
counting when it ends. The window for a deploy opens when
`/app/logs/scheduler.out.log` shows `ETL Workflow finished` and closes two
hours later:

```bash
ssh <user>@<host> docker exec watchtower tail -n 5 /app/logs/scheduler.out.log
```

## After a green deploy

Exit 0 means the API answered `/health` — nothing more. Supervisor runs
`dashboard`, `etl_scheduler` and `api` (`deployment/supervisord.conf`); their
logs and the per-ETL logs are under `/mnt/user/appdata/watchtower/logs/`.
Confirm before declaring success:

```bash
ssh <user>@<host> docker exec watchtower supervisorctl status   # all three RUNNING
curl -fsS -o /dev/null http://<host>:7777/                      # dashboard answers
```

Then, before closing anything on the board:

- `docker image ls watchtower`: `latest` is the new image, `previous` the one
  before it.
- The first ETL cycle, at the end of `scheduler.out.log`: `ETL Workflow
  finished in …` followed by `Successful: N | Failed: N` (102 scripts since
  the 2026-11-27 cleanup of low-quality sources; 108 before it, and 109
  before the mock shoppy entry left the list). The
  line `Running data freshness watcher (after the pool)` sits between the
  last ETL and that summary, and the scheduler's own start line reads
  `ETL Scheduler started. Interval: 7200 s.`
- The variable **names** the container holds, when keys were forwarded —
  every one of them is there, and no `UNRAID_*` is:
  ```bash
  ssh <user>@<host> docker exec watchtower sh -c 'env | cut -d= -f1 | sort'
  ```
- In the browser, the feature the deploy was for. The health gate opens the
  API only; it never loads the dashboard.

Read the JSON, not the status code. The public dashboard hostname answers
every path — `/api/v1/*` included — with the dashboard page and status 200.
Check the API against the container or its own hostname:

```bash
ssh <user>@<host> curl -fsS http://localhost:45714/api/v1/freshness | head -c 300
```

## Rehearsing a risky change

`.github/workflows/docker-build.yml` builds the image from the same archive on
every pull request and boots only the API until `/health` answers. That runs
on GitHub's runner: it never opens the dashboard (Chromium at runtime), runs
no ETL, ignores the image size and does not see the base tags the server has
cached. On 2026-11-24 three image defects only appeared building on the
server (T-099).

When `deployment/Dockerfile`, `pyproject.toml` or `uv.lock` change, rehearse
on the server before `deploy.py`, without touching the running container or
the `latest` / `previous` tags:

1. Upload the archive `deploy.create_archive()` produces, and a shell script,
   over `deploy.connect()`. Send the script with LF line endings: bash on the
   server chokes on CRLF.
2. In a staging directory under `/tmp`, run
   `docker build -t watchtower:candidate -f deployment/Dockerfile .`
3. Boot a throwaway container — its own name, its own host port,
   `--entrypoint uv … run uvicorn src.api.main:app` — with the `data` volume
   mounted read-only. Wait for `/health`, then request a few `/api/v1` routes.
4. Inside the container, check what the image really holds: `python
   --version`, `uv --version`, `uv run playwright --version`, an import of
   `deployment.etl_scheduler`, `run_watchtower_dashboard`, `src.api.main` and
   `src.web.dashboard.app`, and `bash -n run_all_etl.sh`. `docker images
   watchtower:candidate` gives the size.
5. Run two or three real ETLs — a plain script, a `BaseETL`, one that uses
   Playwright — in a second throwaway container with an **empty temporary
   directory** at `/app/data`. Never give a rehearsal write access to
   production data.
6. Remove the throwaway containers and staging files. Keep the
   `watchtower:candidate` tag until the real deploy (it warms the build
   cache), then remove it.

`--entrypoint uv` replaces the image's default start — supervisor, whose
scheduler launches a full ETL cycle on every start. Tag the image
`watchtower:candidate`, never plain `watchtower`: on the server that moves
`latest`, and the next deploy would tag that untested image as `previous`.
Then run the real deploy. The scripts of the 2026-11-24 rehearsal are not in
the repository yet (task T-117); until they are, write the steps as a one-off
script.

## The compose recipe is different

`docker-compose.yml` and the root `Dockerfile` are a separate path. The
commands above assume the production container:

| | `deployment/deploy.py` | Compose |
| :--- | :--- | :--- |
| Container | `watchtower` | `watchtower-app` |
| Dashboard port | host **7777** → container **7780** | `7777:7777` (`WATCHTOWER_DASHBOARD_PORT=7777`) |
| Image contents | the deploy archive (`COPY . .`) | a hand-picked file list, **plus `secrets/`** |
| Settings | only the names in `CONTAINER_ENV_KEYS` travel, through `--env-file`; `UNRAID_*` stay on the dev machine | `env_file: .env` passes the whole file to the container |

## Backups in production

`run_backup.py` ships and the orchestrator runs it after every cycle with
`--max-age-hours 20`: an archive is made only when the newest verified one is
older than that — about one a day. It zips `data/` and `logs/` into the
`backups` volume (`BACKUP_VOLUME` in `deployment/deploy.py`, mounted at
`/app/backups`), verifies it — the zip opens, `*_latest.json` outputs are
present, JSON samples parse — and keeps the last 7. **Same disk as the
data:** a copy against a mistake, not against a disk failure. There is no
off-site copy (the Google Drive path needs a folder id and credentials the
user has not provided).

- **Read the result.** The scheduler log ends each cycle with a `Backup …`
  line: `created <archive> (<size> MiB, <n> files, verified)`, `skipped: the
  newest verified archive is N h old`, or `failed: …` — then read
  `logs/backup_process.log` in the container. A cycle without the line means
  the script did not run at all.
- **On the server,** `ls -la` the backups volume: the archives and
  `last_verification.json`. Every `backup_data_logs_*.zip` there verified
  when it was made. A `*.zip.failed` is one that did not (kept for
  inspection until the next run); a `*.part` is an interrupted run.
- **Restore.** The dashboard and the API stay down while it runs:

  1. Unzip with the image's Python into a staging folder on the array (not
     `/tmp`, which is a RAM disk, and not the volume itself):
     ```bash
     docker run --rm --name watchtower-restore \
       -v /mnt/user/appdata/watchtower/backups:/backup:ro \
       -v /mnt/user/appdata/watchtower-restore:/restore \
       --entrypoint python watchtower:latest \
       -m zipfile -e /backup/backup_data_logs_<timestamp>.zip /restore
     ```
     The archive holds `data/` and `logs/` at its root; `/restore` must show
     the two before going on.
  2. `docker stop watchtower`.
  3. Move the damaged folder aside, never delete it:
     `mv /mnt/user/appdata/watchtower/data /mnt/user/appdata/watchtower/data.broken-$(date +%F)`.
  4. `mv /mnt/user/appdata/watchtower-restore/data /mnt/user/appdata/watchtower/data`
     (same disk, so it is a rename). Restore `logs` the same way only when
     that folder is damaged too.
  5. `docker start watchtower`, wait for `healthy`, open one tab. The start
     launches a full cycle, which rewrites the `*_latest.json` outputs.
  6. Remove the staging folder once the tab shows data.

- Do not report backups as working from a green test alone: after a deploy
  that touches `run_backup.py`, the orchestrator's backup step or the
  volumes, read the `Backup …` line of the first cycle.

## Safety rules

- Never print `.env` or a value from it; list key names only (command above).
  `deploy.py` itself echoes the host while connecting — keep its output out of
  commits and issues.
- Never print the container's environment or `container.env` either:
  `docker inspect watchtower` shows the forwarded keys in clear text. List
  names only (`env | cut -d= -f1`).
- Never put a credential in a script, commit message or file. `detect-secrets`
  runs in pre-commit as a backstop.
- The `data` volume holds **historical data**. A deploy never overwrites it:
  `data/` is not shipped, and the one copy step in `build_command()` is a
  no-clobber `cp -rn` that only runs for an archive carrying a top-level
  `data/` directory.
- If `deploy.py` exits non-zero, report its output verbatim; do not guess.
