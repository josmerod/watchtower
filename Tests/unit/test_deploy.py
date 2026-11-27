"""Hermetic tests for ``deployment/deploy.py``: no network, no SSH, no ``.env``.

The server is replaced by scripted fakes, so what goes into the archive, the
remote command sequence and the health gate / rollback flow are asserted
exactly. The remote commands are real shell, so they are also executed by bash
against a fake ``docker`` binary.
"""

import importlib
import inspect
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
# `deployment/` is a plain directory at the repo root, not an installed package.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from deployment import deploy

# Scripts the orchestrator looks for after each cycle that are deliberately kept
# out of the archive. Empty since T-106 (2026-11-27): run_backup.py ships, and
# writes to the backups volume that docker_run_command() mounts. Before that it
# would have zipped the ~3 GB of data/ into the container's own layer.
DELIBERATELY_NOT_SHIPPED: set[str] = set()

# Repo-root files the code names but the container must or need not have.
# .env: deploy.py loads it here for the Unraid credentials. The file never
# ships — only the names in CONTAINER_ENV_KEYS travel, through --env-file.
# docker-compose*.yml: src/launcher starts compose on a developer's
# machine; the production path is deploy.py.
NOT_SHIPPED_ROOT_FILES = {".env", "docker-compose.yml", "docker-compose.dev.yml"}

SETTINGS = deploy.DeploySettings(server_ip="unraid.invalid", username="root", password=None, browserless_endpoint="ws://unraid.invalid:3000")
ENV_FILE = deploy.CONTAINER_ENV_VOLUME
ENV_CREATE = "umask 077"  # the owner-only file that carries the forwarded variables
ENV_CLEAR = f"rm -f {ENV_FILE}"  # nothing to forward: drop what an older deploy left there

FAKE_DOCKER = """#!/usr/bin/env bash
# Record every invocation; fail only the subcommand named in $DOCKER_FAILS.
echo "docker $*" >> "$DOCKER_CALLS_LOG"
[ "$1" != "${DOCKER_FAILS:-}" ]
"""


# ---------------------------------------------------------------------------
# What travels to the server
# ---------------------------------------------------------------------------


def _touch(root: Path, rel_path: str) -> None:
    target = root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"x")


def _is_shipped(path: str) -> bool:
    return any(path == included or path.startswith(f"{included}/") for included in deploy.INCLUDE_PATHS)


def _entry_points(command: str) -> list[str]:
    """Repo files a command line cannot run without: script tokens and ``package.module:app`` targets."""
    needed = []
    for token in command.split():
        if token.endswith((".py", ".sh")):
            needed.append(token)
        elif re.fullmatch(r"[\w.]+:\w+", token):
            needed.append(token.split(":")[0].replace(".", "/") + ".py")
    return needed


def _wired_scripts(source: str) -> list[str]:
    """Script paths a Python file refers to by name: ``*_script = "x.py"`` and the ``ETL_SCRIPTS`` list."""
    assigned = re.findall(r'^\s*\w*script\w*\s*=\s*"([^"]+\.(?:py|sh))"', source, flags=re.MULTILINE)
    block = re.search(r"^ETL_SCRIPTS = \[\n(.*?)^\]", source, flags=re.MULTILINE | re.DOTALL)
    return assigned + (re.findall(r'"([^"]+\.(?:py|sh))"', block.group(1)) if block else [])


def _boot_files() -> list[str]:
    """Repo paths the container needs to boot and to get through its first ETL cycle."""
    needed = ["deployment/supervisord.conf", "deployment/Dockerfile", "pyproject.toml", "uv.lock", "README.md"]
    supervisor = (REPO_ROOT / "deployment" / "supervisord.conf").read_text(encoding="utf-8")
    for command in re.findall(r"^command=(.+)$", supervisor, flags=re.MULTILINE):
        needed += _entry_points(command)
    # etl_scheduler -> run_all_etl.sh -> orchestrator -> the helpers it runs after each cycle.
    needed += _wired_scripts((REPO_ROOT / "deployment" / "etl_scheduler.py").read_text(encoding="utf-8"))
    needed += re.findall(r"[\w./-]+\.py\b", (REPO_ROOT / "run_all_etl.sh").read_text(encoding="utf-8"))
    needed += _wired_scripts((REPO_ROOT / "run_all_etl_orchestrator.py").read_text(encoding="utf-8"))
    return sorted({path.removeprefix("./") for path in needed})


def _root_files_the_code_names() -> list[str]:
    """Repo-root files whose name the code quotes: the ones it reads by name at runtime."""
    # .git is a file inside a worktree (it points at the main checkout): git's, not the repo's.
    root_files = [path.name for path in REPO_ROOT.iterdir() if path.is_file() and path.name != ".git"]
    named: set[str] = set()
    for folder in ("src", "deployment"):
        for source in (REPO_ROOT / folder).rglob("*.py"):
            if "__pycache__" in source.parts:
                continue
            text = source.read_text(encoding="utf-8", errors="replace")
            named.update(name for name in root_files if f'"{name}"' in text or f"'{name}'" in text)
    return sorted(named)


def test_archive_skips_bytecode_and_caches(tmp_path: Path):
    """Only real sources travel: no __pycache__, .pyc or tool caches."""
    root = tmp_path / "tree"
    for rel_path in (
        "src/a.py",
        "src/__pycache__/a.cpython-313.pyc",
        "src/sub/__pycache__/b.cpython-311.pyc",
        "src/b.pyc",
        "src/.pytest_cache/v/a/nodeids",
        "src/.ruff_cache/0/x",
        "src/sub/c.py",
        "Tests/.mypy_cache/x.json",
    ):
        _touch(root, rel_path)
    archive = tmp_path / "src.tar.gz"

    deploy.create_archive(str(archive), root=str(root), include_paths=["src", "Tests"])

    with tarfile.open(archive) as tar:
        names = {member.name for member in tar.getmembers()}
    # Forward slashes: the server's tar must see directories, not literal backslashes.
    assert names == {"src", "src/a.py", "src/sub", "src/sub/c.py", "Tests"}


def test_boot_files_exist_in_the_repo():
    """Guards the guard: the boot wiring only names real files, so the next test cannot pass on typos."""
    absent = [path for path in _boot_files() if not (REPO_ROOT / path).is_file()]
    assert not absent, absent


def test_include_list_covers_every_boot_file():
    """What the container runs at boot and after each ETL cycle ships — or is waived explicitly.

    The scheduler and the orchestrator skip a missing script with a warning and
    exit 0, which is how the production backup silently stopped running.
    """
    boot_files = _boot_files()
    assert len(boot_files) > 20  # the parsing saw the ETL list, not a stray handful of files
    missing = [path for path in boot_files if not _is_shipped(path) and path not in DELIBERATELY_NOT_SHIPPED]
    assert not missing, f"add these to deploy.INCLUDE_PATHS (or waive them explicitly): {missing}"


def test_root_files_the_code_names_ship_or_are_waived():
    """A file the app reads by name from the repo root ships — or is waived with a reason.

    Not a script, so the boot wiring does not see it: the dashboard's Novedades
    modal renders nothing when changelog.json is absent, and nobody noticed in
    production between 2026-09-10 and 2026-11-24.
    """
    named = _root_files_the_code_names()
    assert "changelog.json" in named  # the scan really reads the dashboard code
    missing = [name for name in named if not _is_shipped(name) and name not in NOT_SHIPPED_ROOT_FILES]
    assert not missing, f"add these to deploy.INCLUDE_PATHS (or waive them explicitly): {missing}"


def test_real_archive_holds_the_boot_files_and_no_bytecode(tmp_path: Path):
    """The archive deploy.py actually builds: every boot file and named root file in, no bytecode."""
    archive = tmp_path / deploy.TAR_FILENAME

    deploy.create_archive(str(archive), root=str(REPO_ROOT))

    with tarfile.open(archive) as tar:
        files = {member.name for member in tar.getmembers() if member.isfile()}
    expected = {path for path in _boot_files() if path not in DELIBERATELY_NOT_SHIPPED}
    expected |= {name for name in _root_files_the_code_names() if _is_shipped(name)}
    assert expected <= files, sorted(expected - files)
    assert not [name for name in files if "__pycache__" in name or name.endswith((".pyc", ".pyo"))]


def test_production_image_declares_the_healthcheck_deploy_waits_on():
    """deploy.py gates on Docker's health status: the production image must define one."""
    dockerfile = (REPO_ROOT / "deployment" / "Dockerfile").read_text(encoding="utf-8").replace("\\\n", " ")
    assert re.search(rf"^HEALTHCHECK .*CMD curl -f http://localhost:{deploy.API_PORT}/health", dockerfile, flags=re.MULTILINE)
    assert f"-p {deploy.API_PORT}:{deploy.API_PORT}" in deploy.docker_run_command("watchtower", SETTINGS.browserless_endpoint)


# ---------------------------------------------------------------------------
# The remote commands, executed by bash against a fake `docker`
# ---------------------------------------------------------------------------


def _bash() -> str | None:
    """A bash that can see the repo, by full path: a bare "bash" resolves to the WSL launcher in System32."""
    exe = shutil.which("bash")
    if exe and "system32" not in exe.lower():
        return exe
    git_bash = Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Git" / "bin" / "bash.exe"
    return str(git_bash) if git_bash.is_file() else None


def _run_in_sandbox(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, command: Callable[[], str], failing: str = "", fake_tar: bool = True) -> tuple[int, list[str]]:
    """Run ``command()`` in bash with a fake ``docker`` on PATH; return (exit code, docker calls)."""
    bash = _bash()
    if bash is None:
        pytest.skip("needs bash to execute the remote commands")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    for name in ("docker", "tar"):
        if name == "tar" and not fake_tar:
            continue  # let the real tar fail on the archive that was never uploaded
        script = fake_bin / name
        script.write_text(FAKE_DOCKER if name == "docker" else "#!/usr/bin/env bash\n", encoding="utf-8", newline="\n")
        script.chmod(0o755)
    calls_log = tmp_path / "docker.log"
    # Point the commands at the sandbox: these four are read when they are built.
    monkeypatch.setattr(deploy, "REMOTE_DIR", (tmp_path / "remote").as_posix())
    monkeypatch.setattr(deploy, "DATA_VOLUME", (tmp_path / "data").as_posix())
    monkeypatch.setattr(deploy, "BACKUP_VOLUME", (tmp_path / "backups").as_posix())
    monkeypatch.setattr(deploy, "TAR_FILENAME", "watchtower-test-only.tar.gz")
    # The command goes in through a file: as a command-line argument MSYS would
    # rewrite the `host:/container` bits of the mounts.
    script_path = tmp_path / "command.sh"
    script_path.write_text(command() + "\n", encoding="utf-8", newline="\n")

    env = {**os.environ, "PATH": f"{fake_bin.as_posix()}{os.pathsep}{os.environ.get('PATH', '')}", "DOCKER_CALLS_LOG": calls_log.as_posix(), "DOCKER_FAILS": failing}
    result = subprocess.run([bash, script_path.as_posix()], env=env, capture_output=True, text=True, timeout=60)
    return result.returncode, calls_log.read_text(encoding="utf-8").splitlines() if calls_log.exists() else []


def _docker_run(image: str) -> str:
    return f"docker {deploy.docker_run_command(image, SETTINGS.browserless_endpoint).removeprefix('docker ')}"


def test_build_tags_the_running_image_then_builds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """The image being replaced is kept as rollback *before* the build moves the tag."""
    code, calls = _run_in_sandbox(monkeypatch, tmp_path, deploy.build_command)
    assert code == 0
    assert calls == ["docker tag watchtower:latest watchtower:previous", "docker build -t watchtower -f deployment/Dockerfile ."]


def test_build_tolerates_having_nothing_to_tag(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """A clean host has no image to tag; that must not stop the deploy."""
    code, calls = _run_in_sandbox(monkeypatch, tmp_path, deploy.build_command, failing="tag")
    assert code == 0
    assert calls == ["docker tag watchtower:latest watchtower:previous", "docker build -t watchtower -f deployment/Dockerfile ."]


def test_build_stops_at_its_first_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """A failed staging step runs no docker command at all.

    The old chain had a bare ``|| true`` in the middle, which let a failure
    before it continue into the build.
    """
    code, calls = _run_in_sandbox(monkeypatch, tmp_path, deploy.build_command, fake_tar=False)
    assert code != 0
    assert calls == []


def test_build_seeds_data_without_clobbering_it():
    text = deploy.build_command()
    assert f"cp -rn {deploy.REMOTE_DIR}/data/* {deploy.DATA_VOLUME}/ || true" in text
    assert "cp -r " not in text  # an unguarded copy would overwrite the historical data volume


def test_build_creates_the_backups_folder(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """The folder exists before the first container mounts it, created empty: nothing seeds it."""
    code, _calls = _run_in_sandbox(monkeypatch, tmp_path, deploy.build_command)
    assert code == 0
    assert (tmp_path / "backups").is_dir()
    assert list((tmp_path / "backups").iterdir()) == []
    # Only the data volume is ever seeded; the archives folder starts empty.
    seeding = [step for step in deploy.build_command().split(" && ") if step.startswith("if [ -d")]
    assert len(seeding) == 1 and deploy.BACKUP_VOLUME not in seeding[0]


def test_container_gets_a_backups_volume_for_the_backup_script():
    """T-106: run_backup.py ships, so its archives need a place a deploy never removes.

    Written to the container's own layer they would be lost at every deploy.
    The volume sits next to ``data`` and ``logs``, and is the folder the script writes to.
    """
    from run_backup import BACKUP_DIR_NAME  # under the project root, /app in the container

    assert "run_backup.py" in deploy.INCLUDE_PATHS
    assert Path(deploy.BACKUP_VOLUME).parent == Path(deploy.DATA_VOLUME).parent == Path(deploy.LOGS_VOLUME).parent
    run = deploy.docker_run_command("watchtower", SETTINGS.browserless_endpoint)
    assert f"-v {deploy.BACKUP_VOLUME}:/app/{BACKUP_DIR_NAME} " in run
    # A rollback is the same swap: the previous image gets the volume too.
    assert f"-v {deploy.BACKUP_VOLUME}:/app/{BACKUP_DIR_NAME} " in deploy.docker_run_command("watchtower:previous", SETTINGS.browserless_endpoint)
    # The compose path (a developer's machine) mounts the same folder.
    compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "- ./backups:/app/backups" in compose


def test_swap_replaces_the_container(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    code, calls = _run_in_sandbox(monkeypatch, tmp_path, lambda: deploy.swap_command("watchtower", SETTINGS.browserless_endpoint))
    assert code == 0
    assert calls == ["docker rm -f watchtower", _docker_run("watchtower")]


def test_swap_tolerates_having_nothing_to_remove(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """A clean host has no container to remove; the removal failing must not skip the run."""
    code, calls = _run_in_sandbox(monkeypatch, tmp_path, lambda: deploy.swap_command("watchtower", SETTINGS.browserless_endpoint), failing="rm")
    assert code == 0
    assert calls == ["docker rm -f watchtower", _docker_run("watchtower")]


def test_rollback_is_the_same_swap_on_the_previous_image(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    code, calls = _run_in_sandbox(monkeypatch, tmp_path, lambda: deploy.swap_command("watchtower:previous", SETTINGS.browserless_endpoint))
    assert code == 0
    assert calls == ["docker rm -f watchtower", _docker_run("watchtower:previous")]


# ---------------------------------------------------------------------------
# Health wait, output streaming, settings
# ---------------------------------------------------------------------------


def test_wait_until_healthy_polls_while_starting():
    sleeps = []
    ticks = iter([0.0, 1.0, 2.0])  # deadline computed at 0, then two checks below it
    statuses = iter(["starting", "starting", "healthy"])

    status = deploy.wait_until_healthy(lambda: next(statuses), sleep=sleeps.append, clock=lambda: next(ticks))

    assert status == "healthy"
    assert sleeps == [deploy.HEALTH_POLL_SECONDS] * 2


def test_wait_until_healthy_gives_up_after_the_timeout():
    ticks = iter([0.0, 1.0, 241.0, 242.0, 483.0])  # the second cycle passes the 240s deadline
    statuses = iter(["starting"] * 3)

    status = deploy.wait_until_healthy(lambda: next(statuses), sleep=lambda seconds: None, clock=lambda: next(ticks))

    assert status == "starting"


@pytest.mark.parametrize("terminal", ["unhealthy", "none", ""])
def test_wait_until_healthy_stops_on_a_settled_status(terminal: str):
    sleeps = []

    status = deploy.wait_until_healthy(lambda: terminal, sleep=sleeps.append, clock=lambda: 0.0)

    assert status == terminal
    assert sleeps == []


class ChannelFile:
    """Hands over the lines paramiko's ``Channel.makefile("rb")`` would, one per iteration step."""

    def __init__(self, lines: list[bytes], before_line: Callable[[int], None]):
        self.lines = lines
        self.before_line = before_line
        self.closed = False

    def __iter__(self) -> Iterator[bytes]:
        for index, line in enumerate(self.lines):
            self.before_line(index)
            yield line

    def __enter__(self) -> "ChannelFile":
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.closed = True


class Channel:
    """The part of ``paramiko.Channel`` that ``deploy.remote`` uses (see the contract test below)."""

    def __init__(self, output: ChannelFile, exit_status: int):
        self.output = output
        self.exit_status = exit_status
        self.command = None
        self.stderr_merged = False

    def set_combine_stderr(self, value: bool) -> None:
        self.stderr_merged = value

    def exec_command(self, command: str) -> None:
        self.command = command

    def makefile(self, mode: str) -> ChannelFile:
        assert mode == "rb"
        return self.output

    def recv_exit_status(self) -> int:
        assert self.output.closed  # read to the end before asking how it went
        return self.exit_status


def test_remote_streams_output_and_returns_the_exit_code(capsys: pytest.CaptureFixture[str]):
    """Output is printed as it arrives (a remote build runs for minutes), not at the end."""

    def before_line(index: int) -> None:
        if index == 1:  # about to hand over line 2: line 1 must already be out
            assert "Step 1/10" in capsys.readouterr().out

    channel = Channel(ChannelFile([b"Step 1/10\n", b"warning on stderr\n"], before_line), exit_status=17)
    ssh = SimpleNamespace(get_transport=lambda: SimpleNamespace(open_session=lambda: channel))

    code, output = deploy.remote(ssh, "docker build .")

    assert code == 17
    assert output == "Step 1/10\nwarning on stderr\n"
    assert channel.command == "docker build ."
    assert channel.stderr_merged


def test_remote_layer_matches_the_real_paramiko_interface():
    """The fakes above are hand-written; with paramiko installed this pins them to the library.

    Run ``uv run --with paramiko python -m pytest`` — a bare ``pytest`` entry point does
    not see uv's ephemeral environment, so the test skips instead of running.

    The first version of ``remote()`` called ``Channel.readline()``, which does
    not exist: the fake channel had it, the real one did not.
    """
    paramiko = pytest.importorskip("paramiko")
    source = inspect.getsource(deploy)

    def used_on(pattern: str) -> set[str]:
        methods = set(re.findall(pattern, source))
        assert methods, f"nothing matched {pattern}: this test drifted away from deploy.py"
        return methods

    for pattern, real in (
        (r"\bchannel\.(\w+)\(", paramiko.Channel),
        (r"\bget_transport\(\)\.(\w+)\(", paramiko.Transport),
        (r"\bssh\.(\w+)\(", paramiko.SSHClient),
        (r"\bsftp\.(\w+)\(", paramiko.SFTPClient),
    ):
        missing = sorted(method for method in used_on(pattern) if not hasattr(real, method))
        assert not missing, f"{real.__name__} has no {missing}: fix deploy.py and the fakes alike"
    assert hasattr(paramiko.file.BufferedFile, "__iter__")  # `for line in channel.makefile("rb")`

    connect_line = next(line for line in source.splitlines() if "connect_kwargs: dict" in line)
    kwargs = set(re.findall(r'"(\w+)":', connect_line)) | set(re.findall(r'connect_kwargs\["(\w+)"\]', source))
    assert kwargs <= set(inspect.signature(paramiko.SSHClient.connect).parameters)


def test_module_imports_without_an_env_file(monkeypatch: pytest.MonkeyPatch):
    """CI has no .env: importing the module must neither read it nor exit."""

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("load_dotenv() called at import time")

    monkeypatch.setattr("dotenv.load_dotenv", forbidden)
    monkeypatch.delenv("UNRAID_HOST", raising=False)

    importlib.reload(deploy)


def test_load_settings_refuses_to_run_without_a_host(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(deploy, "load_dotenv", lambda: None)  # never read the real .env
    for key in ("UNRAID_HOST", "UNRAID_USER", "UNRAID_PASSWORD", "BROWSERLESS_ENDPOINT"):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(SystemExit) as exit_info:
        deploy.load_settings()

    assert exit_info.value.code == 1


def test_load_settings_reads_the_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(deploy, "load_dotenv", lambda: None)
    for key in ("UNRAID_USER", "UNRAID_PASSWORD", "BROWSERLESS_ENDPOINT"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("UNRAID_HOST", "unraid.invalid")

    settings = deploy.load_settings()

    assert settings.username == "root"
    assert settings.password is None
    assert settings.browserless_endpoint == "ws://unraid.invalid:3000"
    monkeypatch.setenv("BROWSERLESS_ENDPOINT", "ws://browser.invalid:3000")
    assert deploy.load_settings().browserless_endpoint == "ws://browser.invalid:3000"


# ---------------------------------------------------------------------------
# The whole deploy() flow against a scripted server
# ---------------------------------------------------------------------------

INSPECT = "image inspect"  # is there an image to roll back to?
BUILD = "docker build"
HEALTH = "State.Health"
SWAP = deploy.swap_command("watchtower", SETTINGS.browserless_endpoint)
ROLLBACK = deploy.swap_command("watchtower:previous", SETTINGS.browserless_endpoint)
SWAP_WITH_ENV = deploy.swap_command("watchtower", SETTINGS.browserless_endpoint, ENV_FILE)
ROLLBACK_WITH_ENV = deploy.swap_command("watchtower:previous", SETTINGS.browserless_endpoint, ENV_FILE)
CLEANUP = f"rm -rf {deploy.REMOTE_DIR} /tmp/{deploy.TAR_FILENAME}"
QUIET = [(0, "")]  # a command whose answer does not matter
# The answers of a deploy that forwards variables and then fails after the swap.
UNHEALTHY_DIAGNOSTICS = {"docker ps -a": QUIET, "supervisorctl status": [(0, "api FATAL exited too quickly\n")], "docker logs": QUIET}


class FakeServer:
    """Stands in for both the SSH session and ``deploy.remote``: scripted answers, recorded commands."""

    def __init__(self, answers: dict[str, list[tuple[int, str]]]):
        self.answers = answers  # marker -> [(exit code, output), ...]; the last answer repeats
        self.commands: list[str] = []
        self.uploads: list[str] = []
        self.env_upload: bytes | None = None  # what went into the forwarded-variables file
        self.closed = False

    def _answer(self, command: str) -> tuple[int, str]:
        """An exact match wins, then a substring (BUILD, HEALTH...); the last answer of a list repeats."""
        markers = [marker for marker in self.answers if marker == command] or [marker for marker in self.answers if marker in command]
        assert markers, f"unexpected remote command: {command}"
        replies = self.answers[markers[0]]
        return replies.pop(0) if len(replies) > 1 else replies[0]

    def remote(self, _ssh: object, command: str) -> tuple[int, str]:
        self.commands.append(command)
        code, output = self._answer(command)
        print(output, end="")  # like the real remote(): streamed as it arrives
        return code, output

    def steps(self) -> list[str]:
        """One short label per remote command, in the order the server saw them."""
        labels = []
        for command in self.commands:
            if command in (SWAP, SWAP_WITH_ENV):
                labels.append("swap")
            elif command in (ROLLBACK, ROLLBACK_WITH_ENV):
                labels.append("rollback")
            elif command == CLEANUP:
                labels.append("cleanup")
            elif INSPECT in command:
                labels.append("inspect")
            elif ENV_CREATE in command:
                labels.append("env")
            elif command == ENV_CLEAR:
                labels.append("env-clear")
            elif BUILD in command:
                labels.append("build")
            elif HEALTH in command:
                labels.append("health")
            elif "supervisorctl status" in command or "docker logs" in command or "docker ps -a" in command:
                labels.append("diagnostics")
            else:
                labels.append(f"??? {command}")
        return labels

    def open_sftp(self) -> "FakeServer":
        return self

    def put(self, local_path: str, remote_path: str) -> None:
        self.uploads.append(remote_path)
        if remote_path == ENV_FILE:
            self.env_upload = Path(local_path).read_bytes()

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def run_deploy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Callable[..., tuple[int, FakeServer]]:
    """Run ``deploy.deploy()`` against a scripted server; returns (exit code, what the server saw)."""
    monkeypatch.setenv("TEMP", str(tmp_path))  # where deploy.py builds the local archive
    monkeypatch.setattr(deploy, "load_settings", lambda: SETTINGS)
    monkeypatch.setattr(deploy, "create_archive", lambda path: Path(path).write_bytes(b"tar"))
    monkeypatch.setattr(deploy, "HEALTH_POLL_SECONDS", 0)
    # What the developer's shell holds must not decide what a test forwards.
    for name in deploy.CONTAINER_ENV_KEYS:
        monkeypatch.delenv(name, raising=False)

    def run(answers: dict[str, list[tuple[int, str]]], server: FakeServer | None = None) -> tuple[int, FakeServer]:
        server = server or FakeServer({**answers, CLEANUP: QUIET, ENV_CLEAR: QUIET})
        monkeypatch.setattr(deploy, "connect", lambda settings: server)
        monkeypatch.setattr(deploy, "remote", server.remote)
        return deploy.deploy(), server

    return run


def test_deploy_succeeds_only_once_the_container_is_healthy(run_deploy: Callable[..., tuple[int, FakeServer]], tmp_path: Path):
    code, server = run_deploy(
        {
            INSPECT: [(1, "Error: No such image\n")],
            BUILD: [(0, "Successfully built abc\n")],
            SWAP: [(0, "0123456789abcdef\n")],
            HEALTH: [(0, "starting\n"), (0, "healthy\n")],
        }
    )

    assert code == 0
    assert server.steps() == ["inspect", "env-clear", "build", "swap", "health", "health", "cleanup"]
    assert server.uploads == [f"/tmp/{deploy.TAR_FILENAME}"]
    assert server.commands[2] == deploy.build_command()
    assert "docker tag watchtower:latest watchtower:previous || true" in server.commands[2]
    assert server.commands[4] == deploy.HEALTH_QUERY
    assert server.commands[1] == ENV_CLEAR  # no variable to forward: nothing an older deploy left may linger
    assert "--env-file" not in server.commands[3]
    assert server.closed
    assert not list(tmp_path.glob("*.tar.gz"))  # local archive removed too


def test_deploy_rolls_back_when_the_new_container_is_not_healthy(run_deploy: Callable[..., tuple[int, FakeServer]], capsys: pytest.CaptureFixture[str]):
    code, server = run_deploy(
        {
            INSPECT: [(0, "ok\n")],
            BUILD: [(0, "Successfully built abc\n")],
            SWAP: [(0, "0123456789abcdef\n")],
            HEALTH: [(0, "unhealthy\n")],
            **UNHEALTHY_DIAGNOSTICS,
            ROLLBACK: [(0, "fedcba9876543210\n")],
        }
    )

    assert code == 1
    assert server.steps() == ["inspect", "env-clear", "build", "swap", "health", "diagnostics", "diagnostics", "diagnostics", "rollback", "cleanup"]
    assert "api FATAL" in capsys.readouterr().out  # the reason is shown before rolling back
    assert server.commands[8] == f"{{ docker rm -f {deploy.DOCKER_IMAGE} || true; }} && {deploy.docker_run_command(f'{deploy.DOCKER_IMAGE}:previous', SETTINGS.browserless_endpoint)}"


def test_deploy_rolls_back_when_the_swap_itself_fails(run_deploy: Callable[..., tuple[int, FakeServer]], capsys: pytest.CaptureFixture[str]):
    """`docker run` refusing (port taken, bad mount) leaves no container: put the previous one back."""
    code, server = run_deploy(
        {
            INSPECT: [(0, "ok\n")],
            BUILD: [(0, "Successfully built abc\n")],
            SWAP: [(125, "docker: Error response from daemon: driver failed programming external connectivity\n")],
            **UNHEALTHY_DIAGNOSTICS,
            ROLLBACK: [(0, "fedcba9876543210\n")],
        }
    )

    assert code == 1
    assert server.steps() == ["inspect", "env-clear", "build", "swap", "diagnostics", "diagnostics", "diagnostics", "rollback", "cleanup"]
    assert "external connectivity" in capsys.readouterr().out


def test_deploy_does_not_roll_back_on_a_clean_host(run_deploy: Callable[..., tuple[int, FakeServer]], capsys: pytest.CaptureFixture[str]):
    code, server = run_deploy(
        {
            INSPECT: [(1, "Error: No such image\n")],
            BUILD: [(0, "Successfully built abc\n")],
            SWAP: [(0, "0123456789abcdef\n")],
            HEALTH: [(0, "unhealthy\n")],
            "docker ps -a": QUIET,
            "supervisorctl status": QUIET,
            "docker logs": QUIET,
        }
    )

    assert code == 1
    assert "rollback" not in server.steps()
    assert "No previous image to roll back to" in capsys.readouterr().out


def test_deploy_leaves_the_running_container_alone_when_the_build_fails(run_deploy: Callable[..., tuple[int, FakeServer]], capsys: pytest.CaptureFixture[str]):
    code, server = run_deploy(
        {
            INSPECT: [(0, "ok\n")],
            BUILD: [(1, "failed to solve\n")],
            "docker ps -a": QUIET,
            "supervisorctl status": QUIET,
            "docker logs": QUIET,
        }
    )

    assert code == 1
    assert server.steps() == ["inspect", "env-clear", "build", "diagnostics", "diagnostics", "diagnostics", "cleanup"]
    output = capsys.readouterr().out
    assert "failed to solve" in output
    assert "the running container was not touched" in output


def test_deploy_survives_a_dropped_connection(run_deploy: Callable[..., tuple[int, FakeServer]], capsys: pytest.CaptureFixture[str]):
    """An SSH error is reported and the session closed, instead of a traceback."""

    class DroppingServer(FakeServer):
        def remote(self, _ssh: object, command: str) -> tuple[int, str]:
            raise OSError("SSH session closed")

    code, server = run_deploy({}, server=DroppingServer({}))

    assert code == 1
    assert "SSH session closed" in capsys.readouterr().out
    assert server.closed


# ---------------------------------------------------------------------------
# Forwarded variables: what may reach the container, and how
# ---------------------------------------------------------------------------

# Environment names the ETL cycle reads that deploy.py handles by other means.
CYCLE_ENV_WAIVED = {"BROWSERLESS_ENDPOINT": "passed with -e by docker_run_command()"}


def _cycle_code() -> list[Path]:
    """The Python the ETL cycle runs: the script packages, their shared helpers and the two entry points."""
    files = [path for folder in ("src/etl", "src/watchers", "src/utils", "src/alerts") for path in (REPO_ROOT / folder).rglob("*.py") if "__pycache__" not in path.parts]
    files.append(REPO_ROOT / "src/miners/crypto_sentiment_miner.py")
    files += [REPO_ROOT / name for name in ("deployment/etl_scheduler.py", "run_all_etl_orchestrator.py")]
    return files


def _env_names_read_by_the_cycle() -> set[str]:
    """Environment names the cycle reads: literally, through a module constant, or as a ``${VAR}`` token in a config."""
    literal = re.compile(r"""(?:getenv|environ\.get|environ\[|environ\.setdefault)\(\s*["']([A-Z_][A-Z0-9_]*)["']""")
    indirect = re.compile(r"""(?:getenv|environ\.get|environ\[|environ\.setdefault)\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*[,)]""")
    constant = re.compile(r"""^([A-Z_][A-Z0-9_]*)\s*(?::[^=\n]+)?=\s*["']([A-Z][A-Z0-9_]{2,})["']""", re.MULTILINE)
    token = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")
    names: set[str] = set()
    for path in _cycle_code():
        text = path.read_text(encoding="utf-8", errors="replace")
        constants = dict(constant.findall(text))
        names.update(literal.findall(text))
        names.update(constants[name] for name in indirect.findall(text) if name in constants)
    # Only configs carry the tokens: in Python ``${VAR}`` is prose, not a read.
    configs = [path for pattern in ("*.json", "*.yaml", "*.yml") for path in (REPO_ROOT / "src/etl").rglob(pattern) if "__pycache__" not in path.parts]
    for path in configs:
        names.update(token.findall(path.read_text(encoding="utf-8", errors="replace")))
    return names


def _settings_secrets_read_by_the_cycle() -> set[str]:
    """Keys the cycle reads through pydantic-settings, as their ``WATCHTOWER_<SECTION>__<FIELD>`` environment names."""
    secret = r"(\w*(?:key|token|secret|password)\w*)"
    attribute = re.compile(rf"settings\.(\w+)\.{secret}", re.IGNORECASE)
    by_name = re.compile(rf"""getattr\(\s*[\w.]*settings\.(\w+)\s*,\s*["']{secret}["']""", re.IGNORECASE)
    read = set()
    for path in _cycle_code():
        text = path.read_text(encoding="utf-8", errors="replace")
        read.update(f"WATCHTOWER_{section.upper()}__{field.upper()}" for section, field in [*attribute.findall(text), *by_name.findall(text)])
    return read


def _is_settings_name(name: str) -> bool:
    """Whether ``WATCHTOWER_<SECTION>__<FIELD>`` (or ``WATCHTOWER_<FIELD>``) names a real setting."""
    from pydantic import BaseModel

    from src.config.settings import Settings

    section, _, field = name.removeprefix("WATCHTOWER_").lower().partition("__")
    if section not in Settings.model_fields:
        return False
    if not field:
        return True
    nested = Settings.model_fields[section].annotation
    return isinstance(nested, type) and issubclass(nested, BaseModel) and field in nested.model_fields


def _is_read_by_code(name: str) -> bool:
    """Whether a Python file of the repository quotes the name: the non-settings variables are read by name."""
    files = [path for folder in ("src", "deployment", "scripts") for path in (REPO_ROOT / folder).rglob("*.py") if "__pycache__" not in path.parts]
    files += [REPO_ROOT / name_ for name_ in ("run_all_etl_orchestrator.py", "run_watchtower_dashboard.py", "run_backup.py") if (REPO_ROOT / name_).exists()]
    quoted = re.compile(rf"""["']{re.escape(name)}["']""")
    return any(quoted.search(path.read_text(encoding="utf-8", errors="replace")) for path in files)


def test_collect_container_env_forwards_the_allowlist_and_nothing_else(monkeypatch: pytest.MonkeyPatch):
    """Only the listed names travel, only when set. The Unraid credentials never do."""
    monkeypatch.setattr(deploy, "load_dotenv", lambda: None)  # never read the real .env
    for name in ("GITHUB_TOKEN", "NVD_API_KEY", "GH_TOKEN", "UNRAID_PASSWORD", "SOME_OTHER_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    monkeypatch.setenv("NVD_API_KEY", "   ")  # blank: an empty key is no key
    monkeypatch.setenv("GH_TOKEN", "")
    monkeypatch.setenv("UNRAID_PASSWORD", "the-server-password")
    monkeypatch.setenv("SOME_OTHER_KEY", "not-on-the-list")

    assert deploy.collect_container_env() == {"GITHUB_TOKEN": "ghp_test"}


def test_allowlist_names_are_plain_identifiers_and_hold_no_server_credential():
    """A name with a separator or a space would be read differently by docker; the SSH credentials must not travel."""
    for name in deploy.CONTAINER_ENV_KEYS:
        assert re.fullmatch(r"[A-Z_][A-Z0-9_]*", name), name
    assert len(set(deploy.CONTAINER_ENV_KEYS)) == len(deploy.CONTAINER_ENV_KEYS)
    assert not {"UNRAID_HOST", "UNRAID_USER", "UNRAID_PASSWORD"} & set(deploy.CONTAINER_ENV_KEYS)


def test_every_variable_the_cycle_reads_is_forwarded_or_waived():
    """A new ``os.getenv("X")`` in an ETL is invisible in production until its name is on the allowlist."""
    read = _env_names_read_by_the_cycle()
    assert {"GITHUB_TOKEN", "IPT_PASSKEY"} <= read  # the scan really sees direct reads and config tokens
    unhandled = sorted(name for name in read if name not in deploy.CONTAINER_ENV_KEYS and name not in CYCLE_ENV_WAIVED)
    assert not unhandled, f"add these to deploy.CONTAINER_ENV_KEYS (or waive them with a reason): {unhandled}"


def test_every_settings_secret_the_cycle_reads_is_forwarded():
    """Keys read through pydantic-settings need their ``WATCHTOWER_<SECTION>__<FIELD>`` name on the allowlist."""
    read = _settings_secrets_read_by_the_cycle()
    assert "WATCHTOWER_API__NEWS_API_KEY" in read  # the scan really sees the getattr form
    unhandled = sorted(read - set(deploy.CONTAINER_ENV_KEYS))
    assert not unhandled, f"add these to deploy.CONTAINER_ENV_KEYS: {unhandled}"


def test_write_env_file_is_what_docker_env_file_reads():
    """One ``NAME=value`` per line, LF, the value verbatim: quotes and ``=`` are not syntax there."""
    path = deploy.write_env_file({"A": "1", "B": "x=y", "C": 'quo"ted', "WATCHTOWER_API__NEWS_API_KEY": "abc"})
    try:
        assert Path(path).read_bytes() == b'A=1\nB=x=y\nC=quo"ted\nWATCHTOWER_API__NEWS_API_KEY=abc\n'
    finally:
        os.remove(path)


def test_write_env_file_refuses_a_line_break():
    """docker cannot carry one, so the deploy must stop before it touches the server."""
    with pytest.raises(ValueError, match="GITHUB_TOKEN contains a line break"):
        deploy.write_env_file({"GITHUB_TOKEN": "ghp_test\nGH_TOKEN=other"})


def test_upload_env_file_creates_an_owner_only_file_and_leaves_nothing_behind(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """The remote file is created under umask 077 before any value arrives; the local copy is deleted afterwards."""
    target = tmp_path / "server" / "container.env"
    monkeypatch.setattr(deploy, "CONTAINER_ENV_VOLUME", target.as_posix())
    exit_codes: list[int] = []
    uploaded: list[tuple[bytes, str]] = []

    def remote(_ssh: object, command: str) -> tuple[int, str]:
        code, _calls = _run_in_sandbox(monkeypatch, tmp_path, lambda: command)  # real bash runs the real command line
        exit_codes.append(code)
        return code, ""

    def put(local_path: str, remote_path: str) -> None:
        uploaded.append((Path(local_path).read_bytes(), remote_path))

    monkeypatch.setattr(deploy, "remote", remote)
    ssh = SimpleNamespace(open_sftp=lambda: SimpleNamespace(put=put, close=lambda: None))

    deploy.upload_env_file(ssh, {"GITHUB_TOKEN": "ghp_test", "IPT_USER_ID": "42"})

    assert exit_codes == [0]
    assert uploaded == [(b"GITHUB_TOKEN=ghp_test\nIPT_USER_ID=42\n", target.as_posix())]  # pragma: allowlist secret - fake values; the env-file layout is what is under test
    if os.name != "nt":  # Windows keeps no POSIX mode bits for chmod to set
        assert target.stat().st_mode & 0o777 == 0o600
    assert not list(Path(tempfile.gettempdir()).glob("watchtower_container_*.env"))


def test_upload_env_file_stops_when_the_file_cannot_be_created(monkeypatch: pytest.MonkeyPatch):
    """No owner-only file, no upload: the values must not land with wider permissions."""

    def put(_local_path: str, _remote_path: str) -> None:
        raise AssertionError("uploaded without the owner-only file")

    monkeypatch.setattr(deploy, "remote", lambda _ssh, _command: (1, "Permission denied\n"))
    ssh = SimpleNamespace(open_sftp=lambda: SimpleNamespace(put=put, close=lambda: None))

    with pytest.raises(RuntimeError, match="could not create"):
        deploy.upload_env_file(ssh, {"GITHUB_TOKEN": "ghp_test"})
    assert not list(Path(tempfile.gettempdir()).glob("watchtower_container_*.env"))


def test_docker_run_takes_the_env_file_only_when_given():
    """Without forwarded variables the command line is exactly what it was before the allowlist existed."""
    plain = deploy.docker_run_command("watchtower", SETTINGS.browserless_endpoint)
    assert "--env-file" not in plain
    assert f"--env-file /srv/watchtower/container.env -p {deploy.HOST_PORT}:{deploy.CONTAINER_PORT}" in deploy.docker_run_command("watchtower", SETTINGS.browserless_endpoint, "/srv/watchtower/container.env")


def test_swap_with_forwarded_variables_replaces_the_container(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    env_file = "/srv/watchtower/container.env"
    code, calls = _run_in_sandbox(monkeypatch, tmp_path, lambda: deploy.swap_command("watchtower", SETTINGS.browserless_endpoint, env_file))

    assert code == 0
    assert calls == ["docker rm -f watchtower", "docker " + deploy.docker_run_command("watchtower", SETTINGS.browserless_endpoint, env_file).removeprefix("docker ")]


def test_deploy_forwards_the_listed_variables_through_an_env_file(run_deploy: Callable[..., tuple[int, FakeServer]], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_value")
    monkeypatch.setenv("NVD_API_KEY", "nvd_test_value")
    monkeypatch.setenv("UNRAID_PASSWORD", "the-server-password")
    code, server = run_deploy({INSPECT: [(0, "ok\n")], ENV_CREATE: QUIET, BUILD: [(0, "Successfully built abc\n")], SWAP_WITH_ENV: [(0, "0123456789abcdef\n")], HEALTH: [(0, "healthy\n")]})

    assert code == 0
    assert server.steps() == ["inspect", "env", "build", "swap", "health", "cleanup"]
    assert server.uploads == [ENV_FILE, f"/tmp/{deploy.TAR_FILENAME}"]  # the variables, then the archive
    assert server.env_upload == b"GITHUB_TOKEN=ghp_test_value\nNVD_API_KEY=nvd_test_value\n"  # allowlist order, values verbatim  # pragma: allowlist secret - fake values
    swap = server.commands[3]
    assert swap == SWAP_WITH_ENV
    assert "GITHUB_TOKEN=" not in swap  # a value never sits on a command line
    output = capsys.readouterr().out
    assert "Forwarding 2 variable(s) to the container: GITHUB_TOKEN, NVD_API_KEY" in output  # names only
    for value in ("ghp_test_value", "nvd_test_value", "the-server-password"):
        assert value not in output


def test_deploy_stops_before_the_build_when_the_env_file_cannot_be_created(run_deploy: Callable[..., tuple[int, FakeServer]], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    """No owner-only file, no deploy: the running container is not touched with half a change."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_value")
    code, server = run_deploy({INSPECT: [(0, "ok\n")], ENV_CREATE: [(1, "Permission denied\n")], BUILD: [(0, "Successfully built abc\n")], SWAP_WITH_ENV: [(0, "0123456789abcdef\n")]})

    assert code == 1
    assert server.steps() == ["inspect", "env", "cleanup"]
    assert server.uploads == []
    assert "could not create" in capsys.readouterr().out


def test_rollback_drops_the_forwarded_variables_when_they_may_be_the_cause(run_deploy: Callable[..., tuple[int, FakeServer]], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    """A rollback must not fail on the one optional part of the command line that docker may have refused."""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_value")
    refused = [(125, "docker: Error response from daemon: file not found\n")]
    code, server = run_deploy({INSPECT: [(0, "ok\n")], ENV_CREATE: QUIET, BUILD: [(0, "Successfully built abc\n")], SWAP_WITH_ENV: refused, **UNHEALTHY_DIAGNOSTICS, ROLLBACK_WITH_ENV: refused, ROLLBACK: [(0, "fedcba9876543210\n")]})

    assert code == 1
    assert server.steps() == ["inspect", "env", "build", "swap", "diagnostics", "diagnostics", "diagnostics", "rollback", "rollback", "cleanup"]
    output = capsys.readouterr().out
    assert "Retrying the rollback without the forwarded variables" in output
    assert "Rollback done" in output
    assert server.commands[8] == ROLLBACK  # second attempt: previous image, no --env-file


def _env_example_names(commented_too: bool = False) -> set[str]:
    """Variable names ``.env.example`` assigns; a commented line documents a name without setting it."""
    pattern = r"^#?\s*([A-Z_][A-Z0-9_]*)=" if commented_too else r"^([A-Z_][A-Z0-9_]*)="
    return set(re.findall(pattern, (REPO_ROOT / ".env.example").read_text(encoding="utf-8"), flags=re.MULTILINE))


def test_env_example_documents_every_forwarded_variable():
    """``.env.example`` is where a user learns what to put in ``.env``: every forwarded name is there."""
    missing = sorted(set(deploy.CONTAINER_ENV_KEYS) - _env_example_names(commented_too=True))
    assert not missing, f"add these to .env.example: {missing}"


def test_env_example_lists_only_names_something_reads():
    """A key nothing reads is a key a user fills in for nothing: 17 of 44 were like that until 2026-11-26."""
    unread = sorted(name for name in _env_example_names(commented_too=True) if not (_is_settings_name(name) or _is_read_by_code(name)))
    assert not unread, f"nothing reads these: {unread}"
