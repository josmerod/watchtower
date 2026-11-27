"""What every test in the suite shares."""

import os
from collections.abc import MutableMapping

import pytest

# The variables that tie a git process to one repository: git's own list
# (``local_repo_env`` in environment.c). A git hook exports them for
# everything it starts, the pre-push test run included, and a ``git`` started
# by a test then follows ``GIT_DIR`` into this repository instead of the
# throwaway one the test just made.
REPO_ENV = (
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CONFIG",
    "GIT_CONFIG_COUNT",
    "GIT_OBJECT_DIRECTORY",
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_IMPLICIT_WORK_TREE",
    "GIT_GRAFT_FILE",
    "GIT_INDEX_FILE",
    "GIT_NO_REPLACE_OBJECTS",
    "GIT_REPLACE_REF_BASE",
    "GIT_PREFIX",
    "GIT_INTERNAL_SUPER_PREFIX",
    "GIT_SUPER_PREFIX",
    "GIT_SHALLOW_FILE",
    "GIT_COMMON_DIR",
)


def drop_repo_env(environ: MutableMapping[str, str]) -> None:
    """Remove the repository-scoped git variables from ``environ``."""
    for name in REPO_ENV:
        environ.pop(name, None)


def pytest_configure(config: pytest.Config) -> None:
    """Run the session as if started from a plain shell, whatever started it."""
    drop_repo_env(os.environ)
