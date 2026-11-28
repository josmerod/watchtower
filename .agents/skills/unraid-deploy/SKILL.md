---
name: unraid-deploy
description: Ship Watchtower to the Unraid server with deployment/deploy.py and prove that the deploy worked, or debug production — find out whether the ETL cycle leaves a deploy window, compare the container's files with the commit, read the server logs, roll back, rehearse a risky image change, check or restore the backups. Use whenever the user wants to deploy, redeploy, push an update to production, restart the remote container, check remote logs, verify a deployment, confirm the site is up, or find out why the dashboard or the ETLs are stale or down. Trigger on "deploy to unraid", "despliega", "ship it", "redeploy", "restart watchtower", "check remote logs", "is the deploy working", "is it up", "is prod ok", "prod está caído", "roll back the deploy".
---

# Unraid Deploy

One maintained path ships Watchtower to the Unraid server:
`deployment/deploy.py`. It archives the working tree, builds the image on the
server, swaps the container and reports success only when the new container
is healthy. Success is the start of the check, not the end of the work: exit
0 means the API answered `/health`, nothing more.

`deployment/deploy.ps1` is **deprecated** (its header says so) — do not use
or update it.

## Before deploying — the gate

All six, or you stop and say which one fails:

1. **The user asked for this deploy**, here or in a standing instruction that
   covers it.
2. **The right tree.** The deploy runs from the main checkout, on `main`,
   clean (`git status --short` prints nothing), at the commit meant for
   production — merged through its PR, CI green. The archive is the working
   tree, not a commit: uncommitted work ships, and a worktree has no `.env`.
3. **Settings.** `.env` (gitignored) defines `UNRAID_HOST`. Optional:
   `UNRAID_USER` (default `root`), `BROWSERLESS_ENDPOINT` (defaults to the
   Unraid host on port 3000), and either `UNRAID_PASSWORD` or an SSH key at
   `~/.ssh/id_ed25519`. Check key **names** only — never print a value:
   ```bash
   grep -oE '^[A-Z_][A-Z0-9_]*=' .env
   ```
   If a name is missing, tell the user which one. Do not invent values.
4. **Lockfile.** `uv lock --check` passes: the image is built with
   `uv sync --frozen`, which does not notice a stale lock.
5. **Between ETL cycles** — see "Timing" below.
6. **Keys.** API keys for the ETLs live in the same `.env`, under the names
   in the *Keys and variables the ETLs read* section of `.env.example`, and
   travel only when listed in `CONTAINER_ENV_KEYS` (see "What a deploy does").

## What a deploy does (`deployment/deploy.py`)

1. **Archive.** Only `INCLUDE_PATHS`: `src`, `deployment`, `config`, `Tests`,
   `pyproject.toml`, `uv.lock`, `run_all_etl.sh`,
   `run_watchtower_dashboard.py`, `run_all_etl_orchestrator.py`,
   `run_backup.py`, `README.md`, `GEMINI.md`, `changelog.json` — minus
   `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `.venv`,
   `*.pyc` and `*.pyo`. Nothing else ships as a file: not `data/`, `.env`,
   `secrets/` or `scripts/`. Text files are normalized to LF as they are
   packed, so the deployed bytes match the commit even on a checkout with
   `core.autocrlf=true`.
2. **Keys.** The names in `CONTAINER_ENV_KEYS` that are set locally are
   written to `/mnt/user/appdata/watchtower/container.env` — owner-only,
   next to the `data` and `logs` volumes, outside the build context — and
   the container gets them with `--env-file`. With none set, that file is
   removed, so a key dropped or rotated locally does not linger on the
   server. The deploy prints the **names** it forwards, never the values.
   `UNRAID_*` are not on the list: the SSH credentials stay on this machine.
3. **Build**, on the server in `/tmp/watchtower_deploy`: tags
   `watchtower:latest` as `watchtower:previous`, then
   `docker build -t watchtower -f deployment/Dockerfile .`
4. **Swap** (`swap_command()`): `docker rm -f watchtower`, then `docker run`
   with `-p 7777:7780` (dashboard) and `-p 45714:45714` (API), binding `data`,
   `logs` and `backups` under `/mnt/user/appdata/watchtower/` and, when
   variables are forwarded, `--env-file`.
5. **Health gate.** Waits up to 4 minutes (polling every 5 s) for the
   container's Docker health status. The `HEALTHCHECK` in
   `deployment/Dockerfile` curls `http://localhost:45714/health`, so the
   **API** is what is gated — not the dashboard or the ETL scheduler.
6. **Rollback.** If `docker run` fails or the container is not `healthy` when
   the wait ends: prints diagnostics, starts `watchtower:previous` again,
   exits 1. Should that rollback fail while variables were forwarded, it is
   retried once without `--env-file`: a container without API keys beats no
   container.

Two lists decide what production can do, and both have a test:

- **A script the container runs has to be in `INCLUDE_PATHS`** (or under one
  of its directories). The scheduler and the orchestrator skip a missing
  script with a warning and exit 0 — the symptom is silence, not an error. So
  has a repo-root file the code reads by name: without `changelog.json` the
  dashboard's 🆕 modal renders nothing and nothing fails.
- **A key an ETL reads has to be on `CONTAINER_ENV_KEYS`.** The list is an
  allowlist, so a new `os.getenv("NEW_KEY")` in an ETL changes nothing in
  production until its name is added there and to `.env.example`.

`Tests/unit/test_deploy.py` fails on a missing entry point, on a named root
file that does not ship and on a variable the cycle reads that is not
forwarded. Run it after touching `INCLUDE_PATHS`,
`deployment/supervisord.conf`, the orchestrator's script list, a root file
name quoted in the code or a keyed source.

## Timing: every start launches a full ETL cycle

Every container start — `deploy.py`, `force_restart.py`, a manual
`docker restart` — launches a **full ETL cycle** immediately
(`deployment/etl_scheduler.py` runs `./run_all_etl.sh` on start), again 2
hours after each cycle ends, and restarts `api` after each cycle.

- A cycle takes **46–47 minutes** in production (2754 s and 2799 s on
  2026-11-27); `goldigging_youtube_posts.py` with its 45-minute budget sets
  the length. So one starts about every 2 h 47 min.
- A deploy inside a cycle kills it in flight, hits every live source again
  and leaves the dashboard and the API down meanwhile. A restart never loads
  new code — it is baked into the image.
- **The window** opens when `/app/logs/scheduler.out.log` shows
  `[<time>] ETL Execution Finished.` and closes when the scheduler's
  interval has passed — two hours after that timestamp. Ask the server
  instead of doing the arithmetic (read-only; exit 0 only with room for a
  deploy):
  ```bash
  uv run --with paramiko python .agents/skills/unraid-deploy/scripts/deploy_window.py
  ```
  ```
  Container time 00:41:10. No cycle is running: the last one ended at 00:08:10.
  The deploy window is open until 02:08:10 — 87 minutes left.
  ```
  By hand it is the scheduler's own lines, not the orchestrator's output it
  echoes below them: `Starting ETL execution...` at the start of a cycle,
  `ETL Execution Finished.` at its end.
- Leave room for the deploy itself (a few minutes) so the cycle does not
  start under it: the script refuses the last 15. No window for an hour:
  wait, or fix first. Do not restart to make one.

When only one program is hung, restart just that program
(`docker exec watchtower supervisorctl restart dashboard`).

## After a green deploy — the proof

Exit 0 means the API answered `/health`. Confirm the rest before declaring
success, and paste the real output into the report:

1. **Programs.** Supervisor runs `dashboard`, `etl_scheduler` and `api`
   (`deployment/supervisord.conf`); all three `RUNNING`:
   ```bash
   ssh <user>@<host> docker exec watchtower supervisorctl status
   ```
2. **The container holds the commit.** The files the release changed, by
   md5, inside the container against the commit (read-only on the server):
   ```bash
   uv run --with paramiko python .agents/skills/unraid-deploy/scripts/verify_deploy.py --since <commit production ran before>
   ```
   `ok` for every file; `DIFFERENT` means the tree that was packed was not
   the commit (uncommitted changes, a wrong branch).
3. **Images.** `docker image ls watchtower`: `latest` is the new image,
   `previous` the one before it.
4. **The first cycle**, at the end of `scheduler.out.log`: `ETL Workflow
   finished in …` then `Successful: N | Failed: M`, and after it
   `Snapshot retention …` and a `Backup …` line. `N + M` is the number of
   registered scripts plus one, the data-freshness watcher, which runs after
   the pool and counts in the summary (`Found <k> ETL scripts to run, plus
   the data-freshness watcher after the pool.` is printed at the start). The
   scheduler's own start line reads `ETL Scheduler started. Interval: 7200 s.`
   A cycle without the `Backup …` line means the backup did not run at all
   (`references/backups.md`).
5. **A clean dashboard log.** The logs are under
   `/mnt/user/appdata/watchtower/logs/` on the server (`dashboard.out.log`,
   `dashboard.err.log`, `scheduler.out.log`, one file per ETL). One line is
   expected after a deploy and is not a defect: `Dash refused a callback
   request` — a tab left open across the deploy asks for the callbacks it
   was loaded with (the user reloads; T-191 tracks the automatic reload).
6. **In the browser**, on the public dashboard that the app's own `/docs`
   page publishes (`https://watchtower.josmerod.es/`): reload, then open
   every tab the release touched and what it changed in them. The health
   gate never opens the dashboard. Data written by the first cycle shows at
   the next request once its ETL has run: the tab repositories cache for up
   to an hour, and since T-197 that cache ends when the file changes.
7. **Variable names**, when keys were forwarded — every one is there and no
   `UNRAID_*` is:
   ```bash
   ssh <user>@<host> docker exec watchtower sh -c 'env | cut -d= -f1 | sort'
   ```

**Read the JSON, not the status code.** The public dashboard hostname answers
every path — `/api/v1/*` included — with the dashboard page and status 200.
Check the API against the container or its own hostname:

```bash
ssh <user>@<host> curl -fsS http://localhost:45714/api/v1/freshness | head -c 300
```

Only then close the task on the board, with this evidence in its row
(`task-board` skill).

## Non-zero exit — what the operator must do

Read the last lines before acting, and report them verbatim (host masked):

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
| Is this the moment to deploy | `uv run --with paramiko python .agents/skills/unraid-deploy/scripts/deploy_window.py` |
| Shipping a code change | `uv run --with paramiko python deployment/deploy.py` |
| Proving the container holds the commit | `uv run --with paramiko python .agents/skills/unraid-deploy/scripts/verify_deploy.py --since <commit>` |
| Several programs are down, no rebuild wanted | `uv run --with paramiko python deployment/force_restart.py` |
| One program is hung | `docker exec watchtower supervisorctl restart dashboard` (or `api`) |
| A source is stale and you need the server logs | `uv run --with paramiko python scripts/debug_remote_logs.py` |

`paramiko` is a deploy-time extra, hence `--with paramiko`; the command is the
same in Git Bash, PowerShell and cmd. The `docker exec` line runs on the
server: prefix it with `ssh <user>@<host>`. `force_restart.py` and
`debug_remote_logs.py` accept no SSH key (they need `UNRAID_PASSWORD`) and
run no health check. Both also start a full cycle, so the same window rule
applies.

## Risky changes and backups

- When `deployment/Dockerfile`, `pyproject.toml` or `uv.lock` change,
  rehearse on the server first: `references/rehearsal.md`. CI builds the
  image on its own runner and boots only the API; three image defects showed
  up only on the server (2026-11-24).
- After each cycle the orchestrator makes a verified archive of `data/` and
  `logs/`: how to read the result, and how to restore, in
  `references/backups.md`.

## The compose recipe is different

`docker-compose.yml` and the root `Dockerfile` are a separate path. The
commands above assume the production container:

| | `deployment/deploy.py` | Compose |
| :--- | :--- | :--- |
| Container | `watchtower` | `watchtower-app` |
| Dashboard port | host **7777** → container **7780** | `7777:7777` (`WATCHTOWER_DASHBOARD_PORT=7777`) |
| Image contents | the deploy archive (`COPY . .`) | a hand-picked file list, **plus `secrets/`** |
| Settings | only the names in `CONTAINER_ENV_KEYS` travel, through `--env-file`; `UNRAID_*` stay on the dev machine | `env_file: .env` passes the whole file to the container |

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
- Do not bypass the pre-push hook and do not push straight to `main`: the
  pre-push hook runs the full test suite (about 8 minutes) when the push
  touches code; over SSH GitHub closes the idle session before it ends, and
  the push then fails after a green run — set it once per clone with
  `git config --local core.sshCommand "ssh -o ServerAliveInterval=30"`, or
  push over HTTPS.
