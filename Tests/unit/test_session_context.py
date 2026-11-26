"""Tests for the SessionStart hook in ``.zcode/hooks/session_context.py``.

ZCode validates the hook's stdout strictly, so the contract under test is
narrow: either one well-formed SessionStart JSON object or nothing, and always
exit code 0. The git scenarios run against throwaway repositories.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / ".zcode" / "hooks" / "session_context.py"
INSTALL = "uv run pre-commit install --hook-type pre-commit --hook-type pre-push"
SECTIONS = ("git_lines", "hook_lines", "board_lines", "feedback_lines")


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args], capture_output=True, text=True, encoding="utf-8", check=True)
    return result.stdout.strip()


def boom(root: str) -> list[str]:
    raise RuntimeError(root)


def write(path: Path, text: str) -> None:
    """Write LF text: in text mode Windows would silently store CRLF."""
    path.write_text(text, encoding="utf-8", newline="\n")


def run_hook(cwd: Path) -> tuple[int, str, str]:
    """Run the script through the interpreter, as the configured process hook does."""
    result = subprocess.run([sys.executable, str(HOOK), str(cwd)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    return result.returncode, result.stdout, result.stderr


@pytest.fixture(scope="module")
def hook() -> ModuleType:
    spec = importlib.util.spec_from_file_location("session_context", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A committed repository with the two board documents and a pre-commit config."""
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "core.autocrlf", "false")
    (tmp_path / "docs").mkdir()
    write(tmp_path / "docs" / "TASK_BOARD.md", "## Board\n\n| ID | Status | Priority | Title | Area | Notes |\n")
    write(tmp_path / "docs" / "FEEDBACK.md", "## Entradas\n")
    write(tmp_path / ".pre-commit-config.yaml", "repos: []\n")
    write(tmp_path / ".gitignore", "data/\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path


def commit(repo: Path, filename: str, text: str) -> None:
    write(repo / filename, text)
    git(repo, "add", filename)
    git(repo, "commit", "-q", "-m", filename)


def hooks_dir_of(repo: Path) -> Path:
    return Path(git(repo, "rev-parse", "--path-format=absolute", "--git-path", "hooks"))


# ---------------------------------------------------------------------------
# The contract with ZCode
# ---------------------------------------------------------------------------


def test_main_prints_exactly_one_session_start_object(hook: ModuleType, repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.chdir(repo)

    assert hook.main() == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert list(payload) == ["hookSpecificOutput"]
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"


def test_silence_when_nothing_can_be_gathered(hook: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    for name in SECTIONS:
        monkeypatch.setattr(hook, name, boom)

    assert hook.digest(str(tmp_path)) == ""
    assert hook.main() == 0
    assert capsys.readouterr().out == ""


def test_a_failing_section_does_not_take_the_others_down(hook: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pending = "1 entry in docs/FEEDBACK.md not triaged yet (first: x)"
    monkeypatch.setattr(hook, "git_lines", lambda root: [f"On branch {root}."])
    monkeypatch.setattr(hook, "hook_lines", boom)
    monkeypatch.setattr(hook, "board_lines", lambda root: [])
    monkeypatch.setattr(hook, "feedback_lines", lambda root: [pending])

    assert hook.digest(str(tmp_path)) == f"<repo-state>\n- On branch {tmp_path}.\n- {pending}\n</repo-state>"


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------


def test_clean_repository(hook: ModuleType, repo: Path) -> None:
    assert hook.git_lines(repo.as_posix()) == [
        "On branch main.",
        "0 commits ahead of and 0 behind main.",
        "Working tree clean.",
    ]


def test_dirty_repository_keeps_leading_dots_in_names(hook: ModuleType, repo: Path) -> None:
    write(repo / ".gitignore", "data/\nlogs/\n")
    write(repo / "new file.txt", "x")
    write(repo / "diseño.txt", "x")

    # Plain `--porcelain` would answer "new file.txt" and "dise\xc3\xb1o.txt".
    assert hook.git_lines(repo.as_posix())[-1] == "3 uncommitted changes: .gitignore, diseño.txt, new file.txt"


def test_status_entries_survive_spaces_and_renames(hook: ModuleType) -> None:
    assert hook.parse_status(" M a.txt\0RM  new name.txt\0old name.txt\0?? diseño.txt\0") == [" M a.txt", "RM  new name.txt", "?? diseño.txt"]
    assert hook.parse_status("") == []
    assert hook.parse_status(None) == []


def test_many_changes_are_summarised(hook: ModuleType, repo: Path) -> None:
    for index in range(7):
        write(repo / f"file{index}.txt", "x")

    line = hook.git_lines(repo.as_posix())[-1]
    assert line.startswith("7 uncommitted changes: ")  # new files only: no "line endings" verdict
    assert line.endswith(" (+2 more)")


def test_distance_to_origin_main(hook: ModuleType, repo: Path) -> None:
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    commit(repo, "a.txt", "a")
    commit(repo, "b.txt", "b")

    assert "2 commits ahead of and 0 behind origin/main." in hook.git_lines(repo.as_posix())
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD~1")
    assert "1 commit ahead of and 0 behind origin/main." in hook.git_lines(repo.as_posix())


def test_detached_head(hook: ModuleType, repo: Path) -> None:
    git(repo, "checkout", "-q", "--detach")

    assert hook.git_lines(repo.as_posix())[0] == "Detached HEAD: no branch is checked out."


def test_line_endings_only_are_flagged_as_noise(hook: ModuleType, repo: Path) -> None:
    (repo / ".gitignore").write_bytes(b"data/\r\n")  # committed as b"data/\n"
    line = hook.git_lines(repo.as_posix())[-1]
    assert line == "1 uncommitted change — tracked files differ only in line endings (CRLF noise): .gitignore"

    (repo / ".gitignore").write_bytes(b"data/\r\nlogs/\r\n")
    assert hook.git_lines(repo.as_posix())[-1] == "1 uncommitted change: .gitignore"


def test_worktree_is_reported(hook: ModuleType, repo: Path, tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    git(repo, "worktree", "add", "-q", "-b", "side", str(worktree))

    assert "This is a git worktree, not the main clone." in hook.git_lines(worktree.as_posix())
    assert "This is a git worktree" not in hook.git_lines(repo.as_posix())


def test_missing_git_hooks_are_announced(hook: ModuleType, repo: Path) -> None:
    assert hook.hook_lines(repo.as_posix()) == [f"Git hooks not installed in this clone (pre-commit, pre-push): run `{INSTALL}` before committing."]


def test_partly_installed_hooks_name_the_missing_one(hook: ModuleType, repo: Path) -> None:
    (hooks_dir_of(repo) / "pre-commit").write_text("#!/bin/sh\n", encoding="utf-8")

    assert hook.hook_lines(repo.as_posix()) == [f"Git hooks not installed in this clone (pre-push): run `{INSTALL}` before committing."]


def test_installed_git_hooks_are_not_mentioned(hook: ModuleType, repo: Path) -> None:
    for name in ("pre-commit", "pre-push"):
        (hooks_dir_of(repo) / name).write_text("#!/bin/sh\n", encoding="utf-8")

    assert hook.hook_lines(repo.as_posix()) == []


def test_no_hook_warning_without_a_pre_commit_config(hook: ModuleType, repo: Path) -> None:
    (repo / ".pre-commit-config.yaml").unlink()

    assert hook.hook_lines(repo.as_posix()) == []


# ---------------------------------------------------------------------------
# Task board and feedback notebook
# ---------------------------------------------------------------------------


def test_board_lines(hook: ModuleType, repo: Path) -> None:
    write(
        repo / "docs" / "TASK_BOARD.md",
        "## Board\n\n"
        "| ID | Status | Priority | Title | Area | Notes |\n"
        "| :-- | :-- | :-- | :-- | :-- | :-- | :-- |\n"
        "| T-100 | in-progress | P1 | Ship it | infra | note |\n"
        "| T-101 | todo | P2 | Later | etl | note |\n"
        "| T-102 | todo | P3 | Much later | docs | note |\n"
        "| T-103 | blocked | P3 | Waiting | api | note |\n\n"
        "## Changelog\n\n- 2026-11-24 — something\n",
    )

    assert hook.board_lines(repo.as_posix()) == [
        "In progress on the board: T-100 (P1) Ship it",
        "Open on the board: 2 todo, 1 blocked.",
        "The board changelog was last updated on 2026-11-24.",
    ]


def test_board_without_rows_or_document(hook: ModuleType, repo: Path, tmp_path: Path) -> None:
    assert hook.board_lines(repo.as_posix()) == ["docs/TASK_BOARD.md has no open rows."]
    assert hook.board_lines((tmp_path / "no-docs").as_posix()) == []


def test_feedback_counts_only_real_entries(hook: ModuleType, repo: Path) -> None:
    notebook = repo / "docs" / "FEEDBACK.md"
    write(
        notebook,
        "## Entradas\n\n<!--\n- [ ] 2026-08-27 — example one\n- [ ] 2026-08-27 — example two\n-->\n\n- [x] 2026-08-27 — done (T-059)\n",
    )
    assert hook.feedback_lines(repo.as_posix()) == []

    with notebook.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("- [ ] 2026-11-24 — El buscador del tab News no encuentra acentos\n")
    assert hook.feedback_lines(repo.as_posix()) == ["1 entry in docs/FEEDBACK.md not triaged yet (first: 2026-11-24 — El buscador del tab News no encuentra acentos)"]

    with notebook.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("* [ ] otra\n")
    assert hook.feedback_lines(repo.as_posix())[0].startswith("2 entries in docs/FEEDBACK.md not triaged yet (first: ")


def test_feedback_without_a_notebook(hook: ModuleType, tmp_path: Path) -> None:
    assert hook.feedback_lines((tmp_path / "no-docs").as_posix()) == []


# ---------------------------------------------------------------------------
# End to end, through the interpreter
# ---------------------------------------------------------------------------


def test_script_on_a_repository(repo: Path) -> None:
    code, stdout, stderr = run_hook(repo)

    assert (code, stderr) == (0, "")
    payload = json.loads(stdout)
    assert list(payload) == ["hookSpecificOutput"]
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert context.startswith("<repo-state>\n- On branch main.\n")
    assert context.endswith("\n</repo-state>")
    assert "- Not a git repository." not in context


def test_script_outside_any_repository(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Also the fail-open path: no git, no documents, still a valid answer."""
    empty = tmp_path_factory.mktemp("not-a-repository")

    code, stdout, stderr = run_hook(empty)

    assert (code, stderr) == (0, "")
    context = json.loads(stdout)["hookSpecificOutput"]
    assert context == {"hookEventName": "SessionStart", "additionalContext": "<repo-state>\n- Not a git repository.\n</repo-state>"}


def test_script_on_this_repository() -> None:
    code, stdout, stderr = run_hook(REPO_ROOT)

    assert (code, stderr) == (0, "")
    context = json.loads(stdout)["hookSpecificOutput"]["additionalContext"]
    assert "- On branch " in context or "- Detached HEAD" in context
    assert "board" in context
