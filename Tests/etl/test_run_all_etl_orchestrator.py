"""Registry-truthfulness and process-tree tests for the root ETL orchestrator.

T-110: a script registered in ``ETL_SCRIPTS`` without an ``if __name__ ==``
guard exits 0 doing nothing — the orchestrator reports fake SUCCESS while no
data is written. T-111: the data-freshness watcher must run after the pool, not
inside it. T-112: the timeout path must kill the whole child tree on every
platform. No network: the kill test spawns a local sleep-only Python child.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import run_all_etl_orchestrator as orch


def test_every_registered_script_exists() -> None:
    """No dead entries: every path in ETL_SCRIPTS must exist on disk."""
    assert len(orch.ETL_SCRIPTS) > 100
    missing = [s for s in orch.ETL_SCRIPTS if not (REPO_ROOT / s).exists()]
    assert missing == [], f"registered but missing on disk: {missing}"


def test_every_registered_script_has_entrypoint() -> None:
    """A script without a ``__main__`` guard fakes SUCCESS each cycle (T-110)."""
    no_guard = [s for s in orch.ETL_SCRIPTS if "__main__" not in (REPO_ROOT / s).read_text(encoding="utf-8", errors="replace")]
    assert no_guard == [], f"registered without __main__ guard: {no_guard}"


def test_shoppy_mock_is_gone() -> None:
    """The shoppy stub wrote mock 'Placeholder' data every cycle (T-110)."""
    assert not any("shoppy" in s for s in orch.ETL_SCRIPTS)
    assert not (REPO_ROOT / "src/etl/ecommerce/shoppy_etl.py").exists()


def test_linkedin_learning_is_not_registered_without_a_consumer() -> None:
    """It was listed by mistake on 2026-11-25: nothing reads its output (T-124).

    Flip this test together with a consumer — a loader in courses_tab.py and
    an entry in ``SOURCE_FILES`` of data_freshness_watcher.py — not before.
    """
    assert "src/etl/courses/linkedin_learning_etl.py" not in orch.ETL_SCRIPTS


def test_freshness_watcher_not_in_pool() -> None:
    """The MUST BE LAST watcher must not compete inside the pool (T-111)."""
    assert "src/watchers/data_freshness_watcher.py" not in orch.ETL_SCRIPTS
    main_src = (REPO_ROOT / "run_all_etl_orchestrator.py").read_text(encoding="utf-8")
    assert main_src.index("as_completed(futures)") < main_src.index("freshness_ok = run_freshness_watcher("), "post-pool freshness step must come after the pool block"


def test_freshness_watcher_runs_after_the_pool_and_reports_its_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """T-111: it runs on its own after the pool and its outcome reaches the cycle summary."""
    ran: list[str] = []
    monkeypatch.setattr(orch, "run_script", lambda script: (ran.append(script) or True, script, 1.0))

    assert orch.run_freshness_watcher([]) is True
    assert ran == ["src/watchers/data_freshness_watcher.py"]

    monkeypatch.setattr(orch, "run_script", lambda script: (False, script, 1.0))
    assert orch.run_freshness_watcher([]) is False  # a failing watcher is a failed step, not silence


def test_freshness_watcher_honors_exclude(monkeypatch: pytest.MonkeyPatch) -> None:
    """``--exclude data_freshness_watcher.py`` skips it: nothing runs, nothing counts."""
    ran: list[str] = []
    monkeypatch.setattr(orch, "run_script", lambda script: (ran.append(script) or True, script, 1.0))

    assert orch.run_freshness_watcher(["data_freshness_watcher.py"]) is None
    assert orch.run_freshness_watcher(["src/watchers/"]) is None
    assert ran == []


def test_kill_process_tree_kills_live_child() -> None:
    """T-112: platform-appropriate tree kill leaves no orphan behind."""
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        assert child.poll() is None
        orch.kill_process_tree(child)
        child.wait(timeout=15)
    finally:
        if child.poll() is None:  # pragma: no cover - only if kill_process_tree failed
            child.kill()
            child.wait(timeout=15)
    assert child.returncode is not None
