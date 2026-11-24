"""Deploy Watchtower to the Unraid server.

Archives the working tree (only what the container needs), uploads it over
SSH, builds the production image remotely and replaces the running container.
The image being replaced is kept as ``watchtower:previous``: if the new
container does not become healthy, the previous image is put back.

Settings come from ``.env`` (gitignored): ``UNRAID_HOST``, ``UNRAID_USER``
(default ``root``) and either ``UNRAID_PASSWORD`` or an SSH key at
``~/.ssh/id_ed25519``. Paramiko is a deploy-time dependency, so run it with
``uv run --with paramiko python deployment/deploy.py``.

The archive is built from the working tree, not from a commit: uncommitted
changes under ``INCLUDE_PATHS`` ship too.
"""

import os
import sys
import tarfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from dotenv import load_dotenv

# What travels to the server. The container only finds a helper if its file is
# on this list — the orchestrator skips a missing post-cycle script without an
# error, and the dashboard drops a feature whose data file is absent — so
# Tests/unit/test_deploy.py checks it against the runtime wiring.
INCLUDE_PATHS = [
    "src",
    "deployment",
    "config",
    "Tests",
    "pyproject.toml",
    "uv.lock",
    "run_all_etl.sh",
    "run_watchtower_dashboard.py",
    "run_all_etl_orchestrator.py",
    "README.md",  # readme = "README.md" is required to build the project
    "GEMINI.md",
    "changelog.json",  # the dashboard's 🆕 Novedades modal reads it at layout time
]
# Bytecode and tool caches are never shipped.
EXCLUDED_DIR_NAMES = frozenset({"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".venv"})
EXCLUDED_SUFFIXES = (".pyc", ".pyo")

REMOTE_DIR = "/tmp/watchtower_deploy"
TAR_FILENAME = "watchtower_src.tar.gz"
DOCKER_IMAGE = "watchtower"
LATEST_TAG = "latest"
PREVIOUS_TAG = "previous"
# Host port (Unraid) -> Container port (Dash app)
HOST_PORT = "7777"
CONTAINER_PORT = "7780"
API_PORT = 45714
DATA_VOLUME = "/mnt/user/appdata/watchtower/data"
LOGS_VOLUME = "/mnt/user/appdata/watchtower/logs"
HEALTH_TIMEOUT_SECONDS = 240
HEALTH_POLL_SECONDS = 5
# "none" means the image has no HEALTHCHECK; the Dockerfile is tested to declare one.
HEALTH_QUERY = f"docker inspect {DOCKER_IMAGE} --format '{{{{if .State.Health}}}}{{{{.State.Health.Status}}}}{{{{else}}}}none{{{{end}}}}'"


@dataclass(frozen=True)
class DeploySettings:
    """Connection settings read from the environment."""

    server_ip: str
    username: str
    password: str | None
    browserless_endpoint: str


def load_settings() -> DeploySettings:
    """Read the ``UNRAID_*`` variables and ``BROWSERLESS_ENDPOINT`` from the environment / ``.env``."""
    load_dotenv()
    server_ip = os.getenv("UNRAID_HOST")
    if not server_ip:
        print("Error: UNRAID_HOST must be set in .env file")
        sys.exit(1)

    # Remote browserless / Chromium endpoint for the Playwright ETLs (LiveBench,
    # BridgeBench...). Read from .env so the LAN address isn't baked into the
    # repo; falls back to the Unraid host on browserless' standard port.
    browserless_endpoint = os.getenv("BROWSERLESS_ENDPOINT") or f"ws://{server_ip}:3000"
    return DeploySettings(
        server_ip=server_ip,
        username=os.getenv("UNRAID_USER", "root"),
        password=os.getenv("UNRAID_PASSWORD"),
        browserless_endpoint=browserless_endpoint,
    )


def archive_filter(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
    """Drop bytecode and tool caches from the deploy archive."""
    if set(info.name.replace("\\", "/").split("/")) & EXCLUDED_DIR_NAMES:
        return None
    return None if info.name.endswith(EXCLUDED_SUFFIXES) else info


def create_archive(output_filename: str, root: str = ".", include_paths: list[str] | None = None) -> None:
    """Write the deploy archive of ``include_paths`` (default: ``INCLUDE_PATHS``) under ``root``."""
    print(f"[{datetime.now()}] Creating source archive: {output_filename}")
    with tarfile.open(output_filename, "w:gz") as tar:
        for path in include_paths if include_paths is not None else INCLUDE_PATHS:
            full_path = os.path.join(root, path)
            if not os.path.exists(full_path):
                print(f"  Warning: {path} not found.")
                continue
            print(f"  Adding {path}...")
            tar.add(full_path, arcname=path, recursive=True, filter=archive_filter)


def docker_run_command(image: str, browserless_endpoint: str) -> str:
    """``docker run`` for the given image tag: both published ports, the ``data`` and ``logs`` volumes and ``TZ``."""
    return (
        f"docker run -d --name {DOCKER_IMAGE} --restart unless-stopped "
        f"-p {HOST_PORT}:{CONTAINER_PORT} -p {API_PORT}:{API_PORT} "
        f"-v {DATA_VOLUME}:/app/data -v {LOGS_VOLUME}:/app/logs "
        f"-e TZ=Europe/Madrid -e BROWSERLESS_ENDPOINT={browserless_endpoint} {image}"
    )


def build_command() -> str:
    """Stage the archive, tag the running image as rollback and build the new one.

    Joined with ``&&``: the first failure ends it there, so no later step can
    mask it. The best-effort tag is braced for the same reason — a bare
    ``|| true`` would also swallow every failure before it.
    """
    return " && ".join(
        [
            f"rm -rf {REMOTE_DIR}",
            f"mkdir -p {REMOTE_DIR}",
            f"tar -xzf /tmp/{TAR_FILENAME} -C {REMOTE_DIR}",
            # Populate data volume if needed (no-clobber to preserve existing data)
            f"mkdir -p {DATA_VOLUME}",
            f"if [ -d {REMOTE_DIR}/data ]; then echo 'Seeding data volume...'; cp -rn {REMOTE_DIR}/data/* {DATA_VOLUME}/ || true; fi",
            f"cd {REMOTE_DIR}",
            f"{{ docker tag {DOCKER_IMAGE}:{LATEST_TAG} {DOCKER_IMAGE}:{PREVIOUS_TAG} || true; }}",
            f"docker build -t {DOCKER_IMAGE} -f deployment/Dockerfile .",
        ]
    )


def swap_command(image: str, browserless_endpoint: str) -> str:
    """Replace the container with ``image``; the exit status is ``docker run``'s.

    The removal is best-effort (a clean host has nothing to remove), so it is
    braced: it must neither skip nor mask the ``docker run`` after it.
    """
    return f"{{ docker rm -f {DOCKER_IMAGE} || true; }} && {docker_run_command(image, browserless_endpoint)}"


def wait_until_healthy(
    probe: Callable[[], str],
    timeout: float | None = None,
    poll: float | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> str:
    """Poll the container health until it settles or ``timeout`` passes; return the last status seen."""
    deadline = clock() + (HEALTH_TIMEOUT_SECONDS if timeout is None else timeout)
    while True:
        status = probe()
        if status != "starting":
            return status
        if clock() >= deadline:
            return status
        sleep(HEALTH_POLL_SECONDS if poll is None else poll)


def connect(settings: DeploySettings) -> Any:
    """Open the SSH session (password, or the default key when no password is set)."""
    import paramiko  # deploy-time dependency: uv run --with paramiko

    print(f"[{datetime.now()}] Connecting to {settings.server_ip}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs: dict[str, Any] = {"username": settings.username, "timeout": 30}
    if settings.password:
        connect_kwargs["password"] = settings.password
    else:
        connect_kwargs["key_filename"] = os.path.expanduser("~/.ssh/id_ed25519")
    ssh.connect(settings.server_ip, **connect_kwargs)
    # The remote build runs for minutes; keep the channel alive through NAT timeouts.
    ssh.get_transport().set_keepalive(30)
    return ssh


def remote(ssh: Any, command: str) -> tuple[int, str]:
    """Run ``command`` on the server, streaming its output as it arrives."""
    channel = ssh.get_transport().open_session()
    channel.set_combine_stderr(True)  # errors arrive interleaved with output, as they happened
    channel.exec_command(command)
    lines: list[str] = []
    # The channel itself has no readline(); its file object has.
    with channel.makefile("rb") as output:
        for line in output:
            lines.append(line.decode(errors="replace"))
            print(lines[-1].rstrip())
    return channel.recv_exit_status(), "".join(lines)


def print_diagnostics(ssh: Any) -> None:
    """Show the state of the container before giving up."""
    for label, command in (
        ("container", f"docker ps -a --filter name={DOCKER_IMAGE} --format '{{{{.Names}}}} | {{{{.Image}}}} | {{{{.Status}}}}'"),
        ("supervisor", f"docker exec {DOCKER_IMAGE} supervisorctl status"),
        ("logs", f"docker logs --tail 40 {DOCKER_IMAGE}"),
    ):
        _code, output = remote(ssh, f"{command} 2>&1 || true")
        print(f"--- {label} ---\n{output.rstrip()}")


def restore_previous(ssh: Any, browserless_endpoint: str, had_previous: bool) -> bool:
    """Put ``watchtower:previous`` back behind the container after a swap that did not get healthy."""
    if not had_previous:
        print("No previous image to roll back to.")
        return False
    print(f"[{datetime.now()}] Rolling back to {DOCKER_IMAGE}:{PREVIOUS_TAG}...")
    rolled_back = remote(ssh, swap_command(f"{DOCKER_IMAGE}:{PREVIOUS_TAG}", browserless_endpoint))[0] == 0
    print(f"[{datetime.now()}] Rollback {'done' if rolled_back else 'FAILED — start the container by hand'}.")
    return rolled_back


def deploy() -> int:
    """Archive, upload, build and swap the container; exit code 0 only when it is healthy."""
    settings = load_settings()
    local_tar_path = os.path.join(os.environ.get("TEMP", "/tmp"), TAR_FILENAME)
    ssh = None
    try:
        create_archive(local_tar_path)
        ssh = connect(settings)
        had_previous = remote(ssh, f"docker image inspect {DOCKER_IMAGE}:{LATEST_TAG} --format ok")[0] == 0

        print(f"[{datetime.now()}] Uploading archive...")
        sftp = ssh.open_sftp()
        sftp.put(local_tar_path, f"/tmp/{TAR_FILENAME}")
        sftp.close()

        print(f"[{datetime.now()}] Building image...")
        if remote(ssh, build_command())[0] != 0:
            print(f"[{datetime.now()}] Build FAILED — the running container was not touched.")
            print_diagnostics(ssh)
            return 1

        print(f"[{datetime.now()}] Swapping container...")
        swapped = remote(ssh, swap_command(DOCKER_IMAGE, settings.browserless_endpoint))[0] == 0
        status = wait_until_healthy(lambda: remote(ssh, HEALTH_QUERY)[1].strip()) if swapped else "not running"

        if swapped and status == "healthy":
            print(f"[{datetime.now()}] Deployment Successful! Container is {status}.")
            return 0

        print(f"[{datetime.now()}] Deployment FAILED (health={status}).")
        print_diagnostics(ssh)
        restore_previous(ssh, settings.browserless_endpoint, had_previous)
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        if ssh is not None:
            try:
                remote(ssh, f"rm -rf {REMOTE_DIR} /tmp/{TAR_FILENAME}")
            except Exception as e:  # cleanup must never mask the deploy result
                print(f"Warning: could not clean the remote staging dir: {e}")
            ssh.close()
        if os.path.exists(local_tar_path):
            os.remove(local_tar_path)


if __name__ == "__main__":
    sys.exit(deploy())
