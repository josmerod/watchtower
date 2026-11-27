"""The suite runs as if from a plain shell, even when a git hook started it."""

import importlib.util
import os
from pathlib import Path
from types import ModuleType

import pytest

CONFTEST = Path(__file__).resolve().parents[1] / "conftest.py"


@pytest.fixture(scope="module")
def conftest() -> ModuleType:
    """The root conftest as a module: loading it by path runs nothing."""
    spec = importlib.util.spec_from_file_location("root_conftest", CONFTEST)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_repository_of_a_hook_does_not_reach_a_test(conftest: ModuleType) -> None:
    """A pre-push hook from a linked worktree exports ``GIT_DIR`` with an absolute path: the ``git`` of a test then
    commits into the repository being pushed instead of into its throwaway one (2026-11-27)."""
    environ = {"GIT_DIR": "C:/repo/.git/worktrees/wt", "GIT_INDEX_FILE": "C:/repo/.git/worktrees/wt/index", "GIT_PREFIX": "", "GIT_EDITOR": "true", "PATH": "/usr/bin"}

    conftest.drop_repo_env(environ)

    assert environ == {"GIT_EDITOR": "true", "PATH": "/usr/bin"}


def test_this_session_runs_without_them(conftest: ModuleType) -> None:
    """Fails under a hook if ``pytest_configure`` stops dropping them."""
    assert sorted(set(os.environ) & set(conftest.REPO_ENV)) == []
