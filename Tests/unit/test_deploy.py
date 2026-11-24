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
# out of the archive. run_backup.py zips data/ into the container's own layer:
# production holds ~3 GB there, so it must not ship until it is redesigned
# together with a persistent backups volume (see docs/TASK_BOARD.md).
DELIBERATELY_NOT_SHIPPED = {"run_backup.py"}

# Repo-root files the code names but the container must or need not have.
# .env: deploy.py loads it here for the Unraid credentials — the container gets
# no secrets. docker-compose*.yml: src/launcher starts compose on a developer's
# machine; the production path is deploy.py.
NOT_SHIPPED_ROOT_FILES = {".env", "docker-compose.yml", "docker-compose.dev.yml"}

SETTINGS = deploy.DeploySettings(server_ip="unraid.invalid", username="root", password=None, browserless_endpoint="ws://unraid.invalid:3000")

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
    """Repo-root files whose name the shipped code quotes: the ones it reads by name at runtime."""
    root_files = [path.name for path in REPO_ROOT.iterdir() if path.is_file()]
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
    # Point the commands at the sandbox: these three are read when they are built.
    monkeypatch.setattr(deploy, "REMOTE_DIR", (tmp_path / "remote").as_posix())
    monkeypatch.setattr(deploy, "DATA_VOLUME", (tmp_path / "data").as_posix())
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
CLEANUP = f"rm -rf {deploy.REMOTE_DIR} /tmp/{deploy.TAR_FILENAME}"
QUIET = [(0, "")]  # a command whose answer does not matter


class FakeServer:
    """Stands in for both the SSH session and ``deploy.remote``: scripted answers, recorded commands."""

    def __init__(self, answers: dict[str, list[tuple[int, str]]]):
        self.answers = answers  # marker -> [(exit code, output), ...]; the last answer repeats
        self.commands: list[str] = []
        self.uploads: list[str] = []
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
            if command == SWAP:
                labels.append("swap")
            elif command == ROLLBACK:
                labels.append("rollback")
            elif command == CLEANUP:
                labels.append("cleanup")
            elif INSPECT in command:
                labels.append("inspect")
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

    def put(self, _local_path: str, remote_path: str) -> None:
        self.uploads.append(remote_path)

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def run_deploy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Callable[..., tuple[int, FakeServer]]:
    """Run ``deploy.deploy()`` against a scripted server; returns (exit code, what the server saw)."""
    monkeypatch.setenv("TEMP", str(tmp_path))  # where deploy.py builds the local archive
    monkeypatch.setattr(deploy, "load_settings", lambda: SETTINGS)
    monkeypatch.setattr(deploy, "create_archive", lambda path: Path(path).write_bytes(b"tar"))
    monkeypatch.setattr(deploy, "HEALTH_POLL_SECONDS", 0)

    def run(answers: dict[str, list[tuple[int, str]]], server: FakeServer | None = None) -> tuple[int, FakeServer]:
        server = server or FakeServer({**answers, CLEANUP: QUIET})
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
    assert server.steps() == ["inspect", "build", "swap", "health", "health", "cleanup"]
    assert server.uploads == [f"/tmp/{deploy.TAR_FILENAME}"]
    assert "docker tag watchtower:latest watchtower:previous || true" in server.commands[1]
    assert server.commands[3] == deploy.HEALTH_QUERY
    assert server.closed
    assert not list(tmp_path.glob("*.tar.gz"))  # local archive removed too


def test_deploy_rolls_back_when_the_new_container_is_not_healthy(run_deploy: Callable[..., tuple[int, FakeServer]], capsys: pytest.CaptureFixture[str]):
    code, server = run_deploy(
        {
            INSPECT: [(0, "ok\n")],
            BUILD: [(0, "Successfully built abc\n")],
            SWAP: [(0, "0123456789abcdef\n")],
            HEALTH: [(0, "unhealthy\n")],
            "docker ps -a": QUIET,
            "supervisorctl status": [(0, "api FATAL exited too quickly\n")],
            "docker logs": QUIET,
            ROLLBACK: [(0, "fedcba9876543210\n")],
        }
    )

    assert code == 1
    assert server.steps() == ["inspect", "build", "swap", "health", "diagnostics", "diagnostics", "diagnostics", "rollback", "cleanup"]
    assert "api FATAL" in capsys.readouterr().out  # the reason is shown before rolling back
    assert server.commands[7] == f"{{ docker rm -f {deploy.DOCKER_IMAGE} || true; }} && {deploy.docker_run_command(f'{deploy.DOCKER_IMAGE}:previous', SETTINGS.browserless_endpoint)}"


def test_deploy_rolls_back_when_the_swap_itself_fails(run_deploy: Callable[..., tuple[int, FakeServer]], capsys: pytest.CaptureFixture[str]):
    """`docker run` refusing (port taken, bad mount) leaves no container: put the previous one back."""
    code, server = run_deploy(
        {
            INSPECT: [(0, "ok\n")],
            BUILD: [(0, "Successfully built abc\n")],
            SWAP: [(125, "docker: Error response from daemon: driver failed programming external connectivity\n")],
            "docker ps -a": QUIET,
            "supervisorctl status": [(1, "no such container\n")],
            "docker logs": [(1, "no such container\n")],
            ROLLBACK: [(0, "fedcba9876543210\n")],
        }
    )

    assert code == 1
    assert server.steps() == ["inspect", "build", "swap", "diagnostics", "diagnostics", "diagnostics", "rollback", "cleanup"]
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
    assert server.steps() == ["inspect", "build", "diagnostics", "diagnostics", "diagnostics", "cleanup"]
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
