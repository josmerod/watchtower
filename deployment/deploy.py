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
changes under ``INCLUDE_PATHS`` ship too. Text files are normalized to LF on
the way in, so the server gets the committed bytes even when the working tree
holds CRLF copies (``core.autocrlf=true``); binary files pass through as-is.

The API keys the ETLs read do not travel as a file: ``.env`` holds the Unraid
credentials too. The variables in ``CONTAINER_ENV_KEYS`` that are set here are
written to an owner-only file on the server and handed to ``docker run
--env-file``; nothing else from the environment reaches the container.
"""

import io
import os
import sys
import tarfile
import tempfile
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
# Variables allowed to travel from this machine's environment / ``.env`` into
# the container — an allowlist on purpose, because the same ``.env`` holds the
# Unraid credentials, which must never reach the container. These are the keys
# the ETL cycle reads: directly from the environment, or through
# pydantic-settings (``WATCHTOWER_<SECTION>__<FIELD>``). The last group holds
# no secrets, but the cycle reads them from the environment just the same.
# ``.env.example`` documents the same names, and Tests/unit/test_deploy.py
# checks both lists against what the code reads.
CONTAINER_ENV_KEYS = (
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "PRODUCTHUNT_API_TOKEN",
    "NVD_API_KEY",
    "ARTIFICIAL_ANALYSIS_API_KEY",
    "REPLICATE_API_TOKEN",
    "API_ITAD_KEY",
    "IPT_USER_ID",
    "IPT_PASSKEY",
    "WATCHTOWER_API__NEWS_API_KEY",
    "WATCHTOWER_API__STACKEXCHANGE_KEY",
    "WATCHTOWER_API__RAPIDAPI_KEY",
    "OPENALEX_MAILTO",
    "CROSSREF_MAILTO",
    "WATCHTOWER_ETL_INTERVAL",
)
# Where the forwarded variables live on the server: next to the ``data`` and
# ``logs`` volumes, outside the build context, readable by the owner only.
CONTAINER_ENV_VOLUME = "/mnt/user/appdata/watchtower/container.env"


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


def normalize_for_archive(data: bytes) -> bytes:
    """Normalize text to LF line endings, leaving binary data untouched.

    A NUL byte marks the content as binary (git's heuristic), and then nothing
    is rewritten. Text files are collapsed from CRLF to LF so the archive is
    byte-identical to the commit even when the working tree was checked out
    with ``core.autocrlf=true``.
    """
    if b"\x00" in data:
        return data
    return data.replace(b"\r\n", b"\n")


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
            _add_path(tar, full_path, path)


def _add_path(tar: tarfile.TarFile, full_path: str, arcname: str) -> None:
    """Add one entry (and, for directories, its children) exactly like ``TarFile.add``.

    The only difference is the payload of regular files, which goes through
    ``normalize_for_archive``; metadata, the exclusion filter, symlink and
    hardlink handling and the sorted recursion order stay tarfile's own.
    """
    tarinfo = archive_filter(tar.gettarinfo(full_path, arcname))
    if tarinfo is None:
        return  # unsupported type or excluded; a dropped directory skips its subtree too
    if tarinfo.isreg():
        with open(full_path, "rb") as source:
            data = normalize_for_archive(source.read())
        tarinfo.size = len(data)
        tar.addfile(tarinfo, io.BytesIO(data))
    else:
        tar.addfile(tarinfo)
    if tarinfo.isdir():
        for child in sorted(os.listdir(full_path)):
            _add_path(tar, os.path.join(full_path, child), os.path.join(arcname, child))


def collect_container_env() -> dict[str, str]:
    """Return the allowlisted variables that are set, as name -> value.

    Call it after ``load_settings()``: that is what reads ``.env`` into the
    environment. Blank values are skipped — an empty key is no key.
    """
    forwarded: dict[str, str] = {}
    for name in CONTAINER_ENV_KEYS:
        value = (os.getenv(name) or "").strip()
        if value:
            forwarded[name] = value
    return forwarded


def write_env_file(variables: dict[str, str]) -> str:
    """Write ``variables`` to a private temporary file in the format ``docker run --env-file`` reads.

    That format is one ``NAME=value`` per line with the value taken verbatim:
    no quotes, no escapes, and no way to carry a line break. A value with one
    is refused here, before anything on the server is touched.
    """
    for name, value in variables.items():
        if "\n" in value or "\r" in value:
            raise ValueError(f"{name} contains a line break: docker --env-file cannot carry it")
    # mkstemp creates the file owner-only, so the values are never on disk with
    # wider permissions.
    descriptor, path = tempfile.mkstemp(prefix="watchtower_container_", suffix=".env")
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as target:
        target.write("".join(f"{name}={value}\n" for name, value in variables.items()))
    return path


def upload_env_file(ssh: Any, variables: dict[str, str]) -> None:
    """Put the forwarded variables on the server, readable by the owner only."""
    local_path = write_env_file(variables)
    env_dir = CONTAINER_ENV_VOLUME.rsplit("/", 1)[0]
    try:
        # Created under umask 077, so the values never exist on the server with
        # wider permissions, not even between the upload and a chmod.
        created = remote(ssh, f"umask 077 && mkdir -p {env_dir} && touch {CONTAINER_ENV_VOLUME} && chmod 600 {CONTAINER_ENV_VOLUME}")[0] == 0
        if not created:
            raise RuntimeError(f"could not create {CONTAINER_ENV_VOLUME} on the server")
        sftp = ssh.open_sftp()
        sftp.put(local_path, CONTAINER_ENV_VOLUME)
        sftp.close()
    finally:
        os.remove(local_path)


def docker_run_command(image: str, browserless_endpoint: str, env_file: str | None = None) -> str:
    """``docker run`` for the given image tag: both published ports, the ``data`` and ``logs`` volumes, ``TZ`` and, with ``env_file``, the forwarded variables."""
    forwarded = f"--env-file {env_file} " if env_file else ""
    return (
        f"docker run -d --name {DOCKER_IMAGE} --restart unless-stopped "
        f"{forwarded}"
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


def swap_command(image: str, browserless_endpoint: str, env_file: str | None = None) -> str:
    """Replace the container with ``image``; the exit status is ``docker run``'s.

    The removal is best-effort (a clean host has nothing to remove), so it is
    braced: it must neither skip nor mask the ``docker run`` after it.
    """
    return f"{{ docker rm -f {DOCKER_IMAGE} || true; }} && {docker_run_command(image, browserless_endpoint, env_file)}"


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


def restore_previous(ssh: Any, browserless_endpoint: str, had_previous: bool, env_file: str | None = None) -> bool:
    """Put ``watchtower:previous`` back behind the container after a swap that did not get healthy."""
    if not had_previous:
        print("No previous image to roll back to.")
        return False
    previous = f"{DOCKER_IMAGE}:{PREVIOUS_TAG}"
    print(f"[{datetime.now()}] Rolling back to {previous}...")
    rolled_back = remote(ssh, swap_command(previous, browserless_endpoint, env_file))[0] == 0
    if not rolled_back and env_file:
        # The forwarded variables are the optional part of that command line.
        # If they are what docker refused, the rollback must not fail with
        # them: a container without API keys beats no container.
        print(f"[{datetime.now()}] Retrying the rollback without the forwarded variables...")
        rolled_back = remote(ssh, swap_command(previous, browserless_endpoint))[0] == 0
    print(f"[{datetime.now()}] Rollback {'done' if rolled_back else 'FAILED — start the container by hand'}.")
    return rolled_back


def deploy() -> int:
    """Archive, upload, build and swap the container; exit code 0 only when it is healthy."""
    settings = load_settings()
    container_env = collect_container_env()  # after load_settings(): that is what reads .env
    local_tar_path = os.path.join(os.environ.get("TEMP", "/tmp"), TAR_FILENAME)
    ssh = None
    try:
        create_archive(local_tar_path)
        ssh = connect(settings)
        had_previous = remote(ssh, f"docker image inspect {DOCKER_IMAGE}:{LATEST_TAG} --format ok")[0] == 0

        # The file on the server mirrors what this deploy forwards: written
        # when variables are set, removed when none is, so a key that was
        # rotated or dropped here does not linger there.
        env_file: str | None = None
        if container_env:
            print(f"[{datetime.now()}] Forwarding {len(container_env)} variable(s) to the container: {', '.join(container_env)}")
            upload_env_file(ssh, container_env)
            env_file = CONTAINER_ENV_VOLUME
        else:
            remote(ssh, f"rm -f {CONTAINER_ENV_VOLUME}")

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
        swapped = remote(ssh, swap_command(DOCKER_IMAGE, settings.browserless_endpoint, env_file))[0] == 0
        status = wait_until_healthy(lambda: remote(ssh, HEALTH_QUERY)[1].strip()) if swapped else "not running"

        if swapped and status == "healthy":
            print(f"[{datetime.now()}] Deployment Successful! Container is {status}.")
            return 0

        print(f"[{datetime.now()}] Deployment FAILED (health={status}).")
        print_diagnostics(ssh)
        restore_previous(ssh, settings.browserless_endpoint, had_previous, env_file)
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
