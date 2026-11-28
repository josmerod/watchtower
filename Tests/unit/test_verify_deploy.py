"""``judge`` of the deploy verifier: what counts as a match between the container and the commit.

A deploy ships the working tree, and the image it builds holds only what the archive carried, so a file deleted before
the commit has to be gone from the container. The verifier reported every such file as ``NOT IN COMMIT`` and counted the
answer of ``md5sum`` against the result: the deploy that removed two dead scripts (PR #48) failed its own check.

The script imports ``deployment.deploy`` and needs the checkout, so it is loaded from its path, as ``test_session_context.py`` does with its hook.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / ".agents" / "skills" / "unraid-deploy" / "scripts" / "verify_deploy.py"

KEPT = "src/kept.py"
GONE = "src/dead.py"
DIGEST = "a" * 32
NOT_THERE = "md5sum: src/dead.py: No such file or directory"


@pytest.fixture(scope="module")
def verify():
    spec = importlib.util.spec_from_file_location("verify_deploy", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_file_the_commit_holds_matches_when_the_container_holds_the_same_bytes(verify):
    assert verify.judge([KEPT], {KEPT: DIGEST}, {KEPT: DIGEST}, []) == (["ok         src/kept.py"], 0, 0)


def test_a_file_deleted_before_the_commit_matches_once_it_is_gone_from_the_container(verify):
    lines, failed, gone = verify.judge([GONE], {}, {}, [NOT_THERE])

    assert (failed, gone) == (0, 1)
    assert lines == ["deleted    src/dead.py"]


@pytest.mark.parametrize("answer", ["md5sum: 'src/dead.py': No such file or directory", 'md5sum: "src/dead.py": No such file or directory'])
def test_the_answer_of_md5sum_is_recognized_with_its_path_between_quotes(verify, answer):
    _lines, failed, gone = verify.judge([GONE], {}, {}, [answer])

    assert (failed, gone) == (0, 1)


def test_a_deleted_file_the_image_kept_counts_against_the_deploy(verify):
    lines, failed, gone = verify.judge([GONE], {}, {GONE: "b" * 32}, [])

    assert (failed, gone) == (1, 0)
    assert lines == [f"STILL IN CONTAINER  {GONE}  (commit -, container {'b' * 32})"]


@pytest.mark.parametrize(("verdict", "actual"), [("NOT IN CONTAINER", {}), ("DIFFERENT", {KEPT: "b" * 32})])
def test_a_file_the_commit_holds_fails_when_the_container_lacks_it_or_holds_other_bytes(verify, verdict, actual):
    lines, failed, gone = verify.judge([KEPT], {KEPT: DIGEST}, actual, [])

    assert failed == 1 and gone == 0
    assert lines == [f"{verdict:<17}  {KEPT}  (commit {DIGEST}, container {actual.get(KEPT, '-')})"]


def test_why_a_file_is_not_in_the_container_is_told_once(verify):
    """The line of ``md5sum`` for a file the commit holds explains its verdict; it is not a second failure."""
    lines, failed, _gone = verify.judge([KEPT], {KEPT: DIGEST}, {}, ["md5sum: src/kept.py: No such file or directory"])

    assert failed == 1
    assert lines == [f"{'NOT IN CONTAINER':<17}  {KEPT}  (commit {DIGEST}, container -)", "server said: md5sum: src/kept.py: No such file or directory"]


@pytest.mark.parametrize("answer", ["md5sum: src/other.py: No such file or directory", "docker: Error response from daemon: No such container"])
def test_anything_else_the_server_said_counts_against_the_deploy(verify, answer):
    """A file nobody asked about, or an error that names none: the comparison cannot be trusted."""
    lines, failed, _gone = verify.judge([GONE], {}, {}, [answer])

    assert failed == 1
    assert lines == ["deleted    src/dead.py", f"server said: {answer}"]


def test_the_run_exits_0_when_the_deleted_files_are_gone(verify, monkeypatch, capsys):
    """The deploy of PR #48, end to end with the server replaced: exit 0 and the deleted files in the summary."""
    monkeypatch.setattr(sys, "argv", ["verify_deploy.py", "--since", "before", "--expect", "after"])
    monkeypatch.setattr(verify, "shipped_paths", lambda *_: [KEPT, GONE])
    monkeypatch.setattr(verify, "committed_md5", lambda _commit, _paths: {KEPT: DIGEST})
    monkeypatch.setattr(verify.deploy, "load_settings", lambda: None)
    monkeypatch.setattr(verify, "connect_quietly", lambda _settings: type("Session", (), {"close": lambda self: None})())
    monkeypatch.setattr(verify, "container_md5", lambda _ssh, _paths: ({KEPT: DIGEST}, [NOT_THERE]))

    assert verify.main() == 0
    assert [line for line in capsys.readouterr().out.splitlines() if line][-2:] == ["deleted    src/dead.py", "2 of 2 shipped file(s) match after (1 deleted before it, and gone from the container)."]


def test_the_run_exits_1_when_the_image_kept_a_deleted_file(verify, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["verify_deploy.py", "--since", "before", "--expect", "after"])
    monkeypatch.setattr(verify, "shipped_paths", lambda *_: [KEPT, GONE])
    monkeypatch.setattr(verify, "committed_md5", lambda _commit, _paths: {KEPT: DIGEST})
    monkeypatch.setattr(verify.deploy, "load_settings", lambda: None)
    monkeypatch.setattr(verify, "connect_quietly", lambda _settings: type("Session", (), {"close": lambda self: None})())
    monkeypatch.setattr(verify, "container_md5", lambda _ssh, _paths: ({KEPT: DIGEST, GONE: "b" * 32}, []))

    assert verify.main() == 1
    assert [line for line in capsys.readouterr().out.splitlines() if line][-1] == "1 of 2 shipped file(s) match after."
