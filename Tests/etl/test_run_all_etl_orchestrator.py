"""Registry-truthfulness and process-tree tests for the root ETL orchestrator.

T-110: a script registered in ``ETL_SCRIPTS`` without an ``if __name__ ==``
guard exits 0 doing nothing — the orchestrator reports fake SUCCESS while no
data is written. T-111: the data-freshness watcher must run after the pool, not
inside it. T-112: the timeout path must kill the whole child tree on every
platform. T-106: the backup after the cycle reports what it did. No network:
the kill test spawns a local sleep-only Python child.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import IO

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


# ---------------------------------------------------------------------------
# Backup after the cycle (T-106)
# ---------------------------------------------------------------------------


def _ship_backup_script(root: Path) -> None:
    """Make ``run_backup.py`` exist where the orchestrator looks for it."""
    (root / "run_backup.py").write_text("", encoding="utf-8")


def test_backup_runs_after_retention() -> None:
    """The archive is taken from the pruned tree, never from a half-written one."""
    main_src = (REPO_ROOT / "run_all_etl_orchestrator.py").read_text(encoding="utf-8")
    assert main_src.index("as_completed(futures)") < main_src.index("Snapshot retention failed") < main_src.index("run_backup()")


def test_backup_without_the_script_says_so(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """T-106: the backups had stopped silently when the script stopped shipping."""
    monkeypatch.chdir(tmp_path)

    assert orch.run_backup(tmp_path / "backup.log") is None
    assert "not found: no backup this cycle" in capsys.readouterr().out


def test_backup_asks_for_an_archive_a_day_and_repeats_the_outcome(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """The script decides by ``--max-age-hours``; its result line is what the cycle log shows."""
    monkeypatch.chdir(tmp_path)
    _ship_backup_script(tmp_path)
    calls: list[list[str]] = []

    def run(cmd: list[str], stdout: IO[str], stderr: int) -> subprocess.CompletedProcess:
        calls.append(cmd)
        stdout.write('log\nBACKUP_RESULT {"status": "skipped", "reason": "the newest verified archive is 2.8 h old (limit 20 h)"}\n')
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(orch.subprocess, "run", run)

    assert orch.run_backup(tmp_path / "backup.log") is True
    assert calls == [["uv", "run", "python", "run_backup.py", "--max-age-hours", str(orch.BACKUP_MAX_AGE_HOURS)]]
    assert "Backup skipped: the newest verified archive is 2.8 h old (limit 20 h)." in capsys.readouterr().out


@pytest.mark.parametrize(
    ("result_line", "returncode", "expected", "ok"),
    [
        ('BACKUP_RESULT {"status": "created", "archive": "backup_data_logs_20261127_135350.zip", "size_mib": 512.3, "files": 59129, "verified": true}', 0, "Backup created backup_data_logs_20261127_135350.zip (512.3 MiB, 59129 files, verified).", True),
        ('BACKUP_RESULT {"status": "failed", "archive": "backup_data_logs_20261127_135350.zip", "errors": ["CRC check failed on data/x.json"]}', 2, "Backup failed: CRC check failed on data/x.json. Check logs/backup_process.log.", False),
        ("", 1, "Backup exit code 1, no result line. Check logs/backup_process.log.", False),
    ],
)
def test_backup_outcome_reaches_the_cycle_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], result_line: str, returncode: int, expected: str, ok: bool) -> None:
    """Created, failed, or dead without a result: each one reads differently in the cycle log."""
    monkeypatch.chdir(tmp_path)
    _ship_backup_script(tmp_path)

    def run(cmd: list[str], stdout: IO[str], stderr: int) -> subprocess.CompletedProcess:
        stdout.write(f"log line\n{result_line}\n")
        return subprocess.CompletedProcess(cmd, returncode)

    monkeypatch.setattr(orch.subprocess, "run", run)

    assert orch.run_backup(tmp_path / "backup.log") is ok
    assert expected in capsys.readouterr().out
