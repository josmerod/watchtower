# Rehearsing a risky change

`.github/workflows/docker-build.yml` builds the image from the same archive on
every pull request and boots only the API until `/health` answers. That runs
on GitHub's runner: it never opens the dashboard (Chromium at runtime), runs
no ETL, ignores the image size and does not see the base tags the server has
cached. On 2026-11-24 three image defects only appeared building on the
server: a missing `libatomic1` for Playwright, a `uv` base tag that was stale
in the registry, and a 700 MB `uv` cache left inside the dependency layer.
"CI built it" is not evidence that the server can.

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
   `src.web.dashboard.app`, and `bash -n run_all_etl.sh`. Print the image's
   `/etc/os-release` and `python --version` next to production's:
   `deploy.py` builds with plain `docker build`, which never asks the registry
   for a newer base tag than the one the server caches. `docker images
   watchtower:candidate` gives the size, and
   `docker history watchtower:candidate --format '{{.Size}}\t{{.CreatedBy}}'`
   shows which layer grew.
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

The rehearsal has no script in the repository yet (T-117 tracks adding one);
until there is one, write the steps as a one-off script outside the
repository. Then run the real deploy.
