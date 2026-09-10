"""Unit tests for run_backup.py — creation, restore verification, pruning.

The Google-Drive path is intentionally not unit-tested here (it is best-effort
and requires live credentials); everything local is pure filesystem logic.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from run_backup import (
    DEFAULT_FOLDERS,
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
