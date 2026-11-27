"""Unit tests for run_backup.py — creation, restore verification, pruning, cadence.

The Google-Drive path is intentionally not unit-tested here (it is best-effort
and requires live credentials); everything local is pure filesystem logic.
"""

from __future__ import annotations

import json
import logging
import os
import time
import zipfile
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

import run_backup
from run_backup import (
    DEFAULT_FOLDERS,
    DEFAULT_KEEP,
    RESULT_PREFIX,
    create_local_backup,
    prune_local_backups,
    verify_backup,
)


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """A minimal project tree: two ETL outputs + a log file."""
    out = tmp_path / "data" / "news" / "output"
    out.mkdir(parents=True)
    (out / "news_latest.json").write_text(json.dumps([{"title": "hello"}]), encoding="utf-8")
    (out / "news_20260910_000000.json").write_text(json.dumps([{"title": "old"}]), encoding="utf-8")
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "app.log").write_text("log line", encoding="utf-8")
    return tmp_path


def test_create_local_backup_zips_data_and_logs(project: Path) -> None:
    archive = create_local_backup(project)
    assert archive is not None and archive.exists()
    with zipfile.ZipFile(archive) as zipf:
        names = zipf.namelist()
    assert any(n.endswith("news_latest.json") for n in names)
    assert any(n.startswith("logs/") for n in names)
    # arcnames stay relative to the project root
    assert all(not n.startswith(("C:", "/", "\\")) for n in names)


def test_verify_backup_passes_on_healthy_archive(project: Path) -> None:
    archive = create_local_backup(project)
    report = verify_backup(archive)
    assert report["ok"] is True
    assert report["critical_latest_count"] >= 1
    assert report["json_samples_validated"] >= 2  # both news_*.json files parse
    assert report["errors"] == []


def test_verify_backup_fails_on_corrupt_archive(project: Path) -> None:
    corrupt = project / "corrupt.zip"
    corrupt.write_bytes(b"this is not a zip file")
    report = verify_backup(corrupt)
    assert report["ok"] is False
    assert any("Cannot open archive" in e for e in report["errors"])


def test_verify_backup_fails_without_critical_latest(project: Path) -> None:
    # An archive with files but zero *_latest.json outputs must NOT verify.
    archive = project / "stale.zip"
    with zipfile.ZipFile(archive, "w") as zipf:
        zipf.writestr("logs/app.log", "log")
    report = verify_backup(archive)
    assert report["ok"] is False
    assert any("_latest.json" in e for e in report["errors"])


def test_verify_backup_fails_on_broken_json_sample(project: Path) -> None:
    (project / "data" / "news" / "output" / "broken_latest.json").write_text("{not json", encoding="utf-8")
    archive = create_local_backup(project)
    report = verify_backup(archive)
    assert report["ok"] is False
    assert any("broken_latest.json" in e for e in report["errors"])


def test_create_local_backup_empty_tree_returns_none(tmp_path: Path) -> None:
    assert create_local_backup(tmp_path, folders=("does-not-exist",)) is None


def test_prune_keeps_newest_n(project: Path) -> None:
    backup_dir = project / "backups"
    backup_dir.mkdir()
    for i in range(7):
        archive = backup_dir / f"backup_data_logs_20260910_00000{i}.zip"
        archive.write_bytes(b"x")
        # Explicit mtimes: files written in the same run share a timestamp to
        # the stored second, which would make the mtime sort unstable.
        import os

        os.utime(archive, (1_800_000_000 + i, 1_800_000_000 + i))
    removed = prune_local_backups(backup_dir, keep=5)
    assert removed == 2
    remaining = sorted(p.name for p in backup_dir.glob("backup_data_logs_*.zip"))
    assert len(remaining) == 5
    # oldest (000000, 000001) are the ones pruned
    assert "backup_data_logs_20260910_000000.zip" not in remaining
    assert "backup_data_logs_20260910_000006.zip" in remaining


def test_default_folders_are_data_and_logs() -> None:
    assert DEFAULT_FOLDERS == ("data", "logs")


def test_prune_keeps_seven_by_default(project: Path) -> None:
    """A week at one archive a day (T-106)."""
    backup_dir = project / "backups"
    backup_dir.mkdir()
    for i in range(9):
        archive = backup_dir / f"backup_data_logs_202611{i}_000000.zip"
        archive.write_bytes(b"x")
        stamp = 1_800_000_000 + i
        os.utime(archive, (stamp, stamp))
    assert prune_local_backups(backup_dir) == 9 - DEFAULT_KEEP == 2


# ---------------------------------------------------------------------------
# main(): the cadence the orchestrator relies on (T-106)
# ---------------------------------------------------------------------------

# How the orchestrator calls the script after every cycle.
DAILY = ["--no-gdrive", "--max-age-hours", "20"]


def _tick(monkeypatch: pytest.MonkeyPatch, *moments: str) -> None:
    """Make each ``datetime.now()`` of the script return the next given ``HH:MM``.

    Two runs in one test would otherwise name their archives with the same
    second, and the second would replace the first.
    """
    times = iter(datetime(2026, 11, 27, int(hour), int(minute)) for hour, minute in (moment.split(":") for moment in moments))
    monkeypatch.setattr(run_backup, "datetime", SimpleNamespace(now=lambda: next(times)))


def _result_of(capsys: pytest.CaptureFixture[str]) -> dict:
    """The ``BACKUP_RESULT`` line of the last ``main()`` call."""
    lines = [line for line in capsys.readouterr().out.splitlines() if line.startswith(RESULT_PREFIX)]
    assert lines, "main() printed no result line"
    return json.loads(lines[-1][len(RESULT_PREFIX) :])


def _archives(project: Path) -> list[str]:
    """Names of the finished archives of the project."""
    backup_dir = project / "backups"
    return sorted(path.name for path in backup_dir.glob("backup_data_logs_*.zip")) if backup_dir.is_dir() else []


def _age(path: Path, hours: float) -> None:
    """Move the modification time of ``path`` back by ``hours``."""
    stamp = time.time() - hours * 3600
    os.utime(path, (stamp, stamp))


def test_main_creates_a_verified_archive_and_reports_it(project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """One run: the archive is there, the report names it, the result line says created."""
    monkeypatch.setattr(run_backup, "get_project_root", lambda: project)

    assert run_backup.main(["--no-gdrive"]) == 0
    assert len(_archives(project)) == 1
    report = json.loads((project / "backups" / "last_verification.json").read_text(encoding="utf-8"))
    assert report["ok"] is True and report["archive"] == _archives(project)[0]
    result = _result_of(capsys)
    assert result["status"] == "created" and result["archive"] == report["archive"] and result["verified"] is True
    # nothing half-made is left next to it
    assert [path.name for path in (project / "backups").iterdir() if path.name.endswith((".part", ".failed"))] == []


def test_a_young_verified_archive_skips_the_run(project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """The newest archive verified and is younger than the limit: nothing is made, exit 0."""
    monkeypatch.setattr(run_backup, "get_project_root", lambda: project)
    _tick(monkeypatch, "13:53")
    assert run_backup.main(["--no-gdrive"]) == 0
    first = _archives(project)

    assert run_backup.main(DAILY) == 0
    assert _archives(project) == first
    result = _result_of(capsys)
    assert result["status"] == "skipped" and "h old" in result["reason"]


def test_an_old_archive_does_not_skip(project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(run_backup, "get_project_root", lambda: project)
    _tick(monkeypatch, "13:53", "15:53")
    assert run_backup.main(["--no-gdrive"]) == 0
    _age(project / "backups" / _archives(project)[0], hours=21)

    assert run_backup.main(DAILY) == 0
    assert len(_archives(project)) == 2
    assert _result_of(capsys)["status"] == "created"


def test_an_archive_that_did_not_verify_does_not_skip(project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Only an archive that verified counts: the run after a failure makes a new one."""
    monkeypatch.setattr(run_backup, "get_project_root", lambda: project)
    _tick(monkeypatch, "13:53", "15:53")
    assert run_backup.main(["--no-gdrive"]) == 0
    report_path = project / "backups" / "last_verification.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["ok"] = False
    report_path.write_text(json.dumps(report), encoding="utf-8")

    assert run_backup.main(DAILY) == 0
    assert len(_archives(project)) == 2
    assert _result_of(capsys)["status"] == "created"


def test_force_makes_an_archive_even_when_the_last_one_is_young(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run_backup, "get_project_root", lambda: project)
    _tick(monkeypatch, "13:53", "13:54")
    assert run_backup.main(["--no-gdrive"]) == 0

    assert run_backup.main(["--no-gdrive", "--max-age-hours", "20", "--force"]) == 0
    assert len(_archives(project)) == 2


def test_an_archive_that_does_not_verify_is_kept_apart(project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """It never counts as a backup and never displaces a good one; the next run removes it."""
    monkeypatch.setattr(run_backup, "get_project_root", lambda: project)
    _tick(monkeypatch, "13:53", "15:53")
    broken = project / "data" / "news" / "output" / "broken_latest.json"
    broken.write_text("{not json", encoding="utf-8")

    assert run_backup.main(["--no-gdrive"]) == 2
    assert _archives(project) == []
    failed = list((project / "backups").glob("backup_data_logs_*.zip.failed"))
    assert len(failed) == 1
    report = json.loads((project / "backups" / "last_verification.json").read_text(encoding="utf-8"))
    assert report["ok"] is False and report["kept_as"] == failed[0].name
    result = _result_of(capsys)
    assert result["status"] == "failed" and any("broken_latest.json" in error for error in result["errors"])

    broken.unlink()
    assert run_backup.main(DAILY) == 0  # a failed run is never skipped
    assert failed[0].exists() is False
    assert len(_archives(project)) == 1


def test_an_interrupted_run_leaves_no_half_archive(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The archive gets its name only once it is closed; what a killed run left goes first."""
    monkeypatch.setattr(run_backup, "get_project_root", lambda: project)
    (project / "backups").mkdir()
    (project / "backups" / "backup_data_logs_20261126_100000.zip.part").write_bytes(b"half a zip")

    assert run_backup.main(["--no-gdrive"]) == 0
    assert list((project / "backups").glob("*.part")) == []
    assert len(_archives(project)) == 1
    assert verify_backup(project / "backups" / _archives(project)[0])["ok"] is True


def test_a_run_that_dies_while_zipping_leaves_only_the_partial_file(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def no_space(zipf: zipfile.ZipFile, folder: Path, root: Path) -> int:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(run_backup, "add_folder_to_zip", no_space)

    with pytest.raises(OSError):
        run_backup.create_local_backup(project)
    backup_dir = project / "backups"
    assert _archives(project) == []
    assert [path.suffix for path in backup_dir.iterdir()] == [".part"]


def test_nothing_to_back_up_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(run_backup, "get_project_root", lambda: tmp_path)

    assert run_backup.main(["--no-gdrive"]) == 1
    assert _result_of(capsys) == {"status": "failed", "reason": "no files to back up"}


def test_a_file_removed_while_the_backup_runs_is_skipped(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The tree is listed before it is read: the temp file of a running process can be gone by then."""
    real_write = zipfile.ZipFile.write

    def write(self: zipfile.ZipFile, path: str | os.PathLike[str], arcname: str | None = None) -> None:
        if os.path.basename(path) == "news_20260910_000000.json":
            raise FileNotFoundError(2, "No such file or directory", str(path))
        real_write(self, path, arcname)

    monkeypatch.setattr(zipfile.ZipFile, "write", write)
    archive = create_local_backup(project)
    assert archive is not None
    with zipfile.ZipFile(archive) as zipf:
        names = zipf.namelist()
    assert "data/news/output/news_20260910_000000.json" not in names
    assert any(name.endswith("news_latest.json") for name in names)


# ---------------------------------------------------------------------------
# The optional Google Drive upload: quiet when it is not there
# ---------------------------------------------------------------------------


def test_importing_backup_utils_without_pydrive2_prints_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    """The backup log used to open with a false "ERROR: PyDrive2 library is not installed" on every run."""
    import builtins
    import importlib
    from unittest import mock

    from src.utils import backup_utils

    real_import = builtins.__import__

    def without_pydrive2(name: str, *args: object, **kwargs: object):
        if name.startswith("pydrive2"):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    with mock.patch("builtins.__import__", without_pydrive2):
        module = importlib.reload(backup_utils)

    assert module.GoogleAuth is None
    assert capsys.readouterr().out == ""


def test_the_gdrive_upload_says_why_it_does_not_run_without_pydrive2(project: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    from src.utils import backup_utils

    (project / "creds.json").write_text("{}", encoding="utf-8")
    settings = SimpleNamespace(google_drive=SimpleNamespace(backup_folder_id="a-folder", credentials_file="creds.json"))
    monkeypatch.setattr("src.config.settings.get_settings", lambda: settings)
    monkeypatch.setattr(backup_utils, "GoogleAuth", None)

    with caplog.at_level(logging.WARNING, logger="RunBackup"):
        assert run_backup.upload_to_gdrive_best_effort(project) is False

    assert "PyDrive2 is not installed" in caplog.text
