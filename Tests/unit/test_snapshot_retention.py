"""Tests for src.utils.snapshot_retention (T-055).

All tests run against ``tmp_path`` fixtures only — the real ``data/``
directory is historical and must never be touched by unit tests.
"""

from datetime import datetime
from pathlib import Path

import pytest

from src.utils.snapshot_retention import (
    apply_prune,
    main,
    parse_snapshot_filename,
    plan_prune,
    run_retention,
)


def _write(path: Path, content: str = "x") -> Path:
    """Create parent dirs and write a file, returning its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _snapshots(data_dir: Path, subdir: str, prefix: str, timestamps: list[str], size: int = 1) -> list[Path]:
    """Write ``{prefix}_{timestamp}.json`` snapshots under ``data_dir/subdir``."""
    return [_write(data_dir / subdir / f"{prefix}_{ts}.json", "a" * size) for ts in timestamps]


class TestParseSnapshotFilename:
    """Timestamp extraction from bare filenames."""

    def test_dominant_format(self):
        """YYYYMMDD_HHMMSS parses with prefix and .json suffix."""
        result = parse_snapshot_filename("stack_releases_20260828_100626.json")
        assert result == (datetime(2026, 8, 28, 10, 6, 26), "stack_releases", ".json")

    def test_timestamp_first_metrics_format(self):
        """Timestamp-first metrics files parse with empty prefix."""
        result = parse_snapshot_filename("20260827_161621_metrics.json")
        assert result == (datetime(2026, 8, 27, 16, 16, 21), "", "_metrics.json")

    def test_compact_format(self):
        """Compact YYYYMMDDHHMMSS parses (watcher event style)."""
        result = parse_snapshot_filename("20260828104905_change_detected.json")
        assert result == (datetime(2026, 8, 28, 10, 49, 5), "", "_change_detected.json")

    def test_iso_date_formats(self):
        """Dashed dates parse, date-only defaulting to midnight."""
        assert parse_snapshot_filename("report-2026-08-28.json") == (datetime(2026, 8, 28), "report", ".json")
        assert parse_snapshot_filename("report-2026-08-28T10:06:26.json") == (datetime(2026, 8, 28, 10, 6, 26), "report", ".json")

    def test_underscore_date_format(self):
        """YYYY_MM_DD_HHMMSS parses."""
        assert parse_snapshot_filename("trends_2026_08_18_100611.json") == (datetime(2026, 8, 18, 10, 6, 11), "trends", ".json")

    def test_unparseable_names_return_none(self):
        """Files without a valid timestamp token return None."""
        assert parse_snapshot_filename("hf_learn.json") is None
        assert parse_snapshot_filename("foo_12345.json") is None
        assert parse_snapshot_filename("stack_releases_latest.json") is None  # 'latest' carries no timestamp token
        assert parse_snapshot_filename("20261301_000000.json") is None  # month 13 is impossible

    def test_long_digit_runs_do_not_match(self):
        """A 16-digit hash-like token is not partially parsed as a date."""
        assert parse_snapshot_filename("item_1234567890123456.json") is None


class TestPlanPrune:
    """Pure planning: grouping, newest-N selection, protected files."""

    def test_keeps_newest_n_per_prefix(self, tmp_path):
        """Only files beyond the newest keep_last per prefix are marked."""
        _snapshots(tmp_path, "github", "stack_releases", ["20260101_000000", "20260102_000000", "20260103_000000", "20260104_000000", "20260105_000000"])
        actions = plan_prune(tmp_path, keep_last=2)
        assert sorted(a.path.name for a in actions) == ["stack_releases_20260101_000000.json", "stack_releases_20260102_000000.json", "stack_releases_20260103_000000.json"]

    def test_never_touches_protected_files(self, tmp_path):
        """Latest files, state files, watchers and untimestamped files are never marked."""
        _snapshots(tmp_path, "news/output", "techcrunch", ["20260101_000000", "20260102_000000"])
        _write(tmp_path / "news/output/techcrunch_latest.json")
        _write(tmp_path / "news/output/run_summary_latest.json")
        _write(tmp_path / "news/output/run_summary_20260101_000000.json")
        _write(tmp_path / "news/output/run_summary_20260102_000000.json")
        _write(tmp_path / "watchers/courses/state.json")
        _write(tmp_path / "watchers/data_freshness/events/20260101_000000_change_detected.json")
        _write(tmp_path / "news/output/hf_learn.json")
        _write(tmp_path / "news/output/state.json")
        _write(tmp_path / "etl_runs_latest.json")
        actions = plan_prune(tmp_path, keep_last=1)
        marked = {a.path for a in actions}
        # Timestamped snapshots and timestamped run summaries ARE prunable...
        assert (tmp_path / "news/output/techcrunch_20260101_000000.json") in marked
        assert (tmp_path / "news/output/run_summary_20260101_000000.json") in marked
        # ...but nothing protected ever is.
        for protected in (
            tmp_path / "news/output/techcrunch_latest.json",
            tmp_path / "news/output/run_summary_latest.json",
            tmp_path / "news/output/run_summary_20260102_000000.json",  # newest in its group, kept
            tmp_path / "watchers/courses/state.json",
            tmp_path / "watchers/data_freshness/events/20260101_000000_change_detected.json",
            tmp_path / "news/output/hf_learn.json",
            tmp_path / "news/output/state.json",
            tmp_path / "etl_runs_latest.json",
        ):
            assert protected not in marked

    def test_mixed_format_timestamps_sort_correctly(self, tmp_path):
        """Files using different timestamp formats rank by parsed instant, not string."""
        _write(tmp_path / "feed_20260101_120000.json")  # underscore format, oldest
        _write(tmp_path / "feed_20260102120000.json")  # compact format, middle
        _write(tmp_path / "feed_2026-01-03.json")  # ISO date-only, newest
        actions = plan_prune(tmp_path, keep_last=1)
        assert sorted(a.path.name for a in actions) == ["feed_20260101_120000.json", "feed_20260102120000.json"]

    def test_same_prefix_in_different_dirs_groups_independently(self, tmp_path):
        """Identical prefixes in different directories keep their own newest N."""
        # Timestamp-first metrics layout AND prefix layout, in four directories.
        for group_dir, prefix in (("metrics/etl_a", ""), ("metrics/etl_b", ""), ("a", "feed"), ("b", "feed")):
            stem = f"{prefix}_" if prefix else ""
            _write(tmp_path / group_dir / f"{stem}20260101_000000.json")
            _write(tmp_path / group_dir / f"{stem}20260102_000000.json")
        actions = plan_prune(tmp_path, keep_last=1)
        marked = {a.path for a in actions}
        assert len(actions) == 4  # exactly the oldest file from each of the 4 groups
        for group_dir, prefix in (("metrics/etl_a", ""), ("metrics/etl_b", ""), ("a", "feed"), ("b", "feed")):
            stem = f"{prefix}_" if prefix else ""
            assert (tmp_path / group_dir / f"{stem}20260101_000000.json") in marked
            assert (tmp_path / group_dir / f"{stem}20260102_000000.json") not in marked

    def test_keep_last_must_be_positive(self, tmp_path):
        """keep_last < 1 is rejected — a full purge must never be planned."""
        with pytest.raises(ValueError, match="keep_last"):
            plan_prune(tmp_path, keep_last=0)

    def test_missing_data_dir_returns_no_actions(self, tmp_path):
        """A nonexistent data directory plans nothing instead of raising."""
        assert plan_prune(tmp_path / "does_not_exist") == []


class TestApplyPrune:
    """Execution: dry-run safety, deletion and byte accounting."""

    def _make_files(self, tmp_path):
        """Write four snapshots of known sizes; return (paths by ts, sizes)."""
        sizes = {"20260101_000000": 100, "20260102_000000": 200, "20260103_000000": 300, "20260104_000000": 400}
        paths = {ts: _write(tmp_path / f"stack_{ts}.json", "a" * size) for ts, size in sizes.items()}
        return paths, sizes

    def test_dry_run_deletes_nothing(self, tmp_path):
        """Default dry_run=True leaves every file on disk."""
        paths, _ = self._make_files(tmp_path)
        actions = plan_prune(tmp_path, keep_last=2)
        report = apply_prune(actions, dry_run=True)
        assert all(p.exists() for p in paths.values())
        assert report.planned == 2
        assert report.deleted == 0
        assert report.bytes_freed == 0

    def test_apply_deletes_old_and_keeps_new(self, tmp_path):
        """Apply mode removes exactly the marked files."""
        paths, _ = self._make_files(tmp_path)
        actions = plan_prune(tmp_path, keep_last=2)
        report = apply_prune(actions, dry_run=False)
        assert not paths["20260101_000000"].exists()
        assert not paths["20260102_000000"].exists()
        assert paths["20260103_000000"].exists()
        assert paths["20260104_000000"].exists()
        assert report.deleted == 2
        assert report.failed == 0

    def test_bytes_freed_math(self, tmp_path):
        """bytes_freed equals the sum of the deleted files' sizes."""
        _, sizes = self._make_files(tmp_path)
        actions = plan_prune(tmp_path, keep_last=2)
        report = apply_prune(actions, dry_run=False)
        assert report.bytes_freed == sizes["20260101_000000"] + sizes["20260102_000000"]
        assert report.per_prefix[".::stack::.json"]["bytes_freed"] == report.bytes_freed

    def test_unparseable_and_unknown_extensions_skipped(self, tmp_path):
        """Bad timestamps are counted as skipped; unknown extensions are ignored entirely."""
        _snapshots(tmp_path, "foo", "bar", ["20260101_000000", "20260102_000000"])
        _write(tmp_path / "foo/bar_notes_12345.json")  # digits but no valid token
        _write(tmp_path / "foo/bar_20261332_999999.json")  # impossible date
        _write(tmp_path / "foo/bar_20260101_000000.txt")  # timestamped but unknown extension
        report = run_retention(tmp_path, keep_last=1, dry_run=True)
        assert report.skipped_unparseable == 2
        marked = {a.path.name for a in plan_prune(tmp_path, keep_last=1)}
        assert marked == {"bar_20260101_000000.json"}
        assert (tmp_path / "foo/bar_20260101_000000.txt").exists()

    def test_timestamped_csv_pruned_with_json(self, tmp_path):
        """Timestamped .csv snapshots join the same keep-last groups as .json."""
        _write(tmp_path / "news/vb_20260101_000000.csv", "a,b")
        _write(tmp_path / "news/vb_20260102_000000.csv", "a,b")
        _write(tmp_path / "news/vb_20260103_000000.csv", "a,b")
        _write(tmp_path / "news/vb_latest.csv", "a,b")
        marked = {a.path.name for a in plan_prune(tmp_path, keep_last=1)}
        assert marked == {"vb_20260101_000000.csv", "vb_20260102_000000.csv"}
        assert (tmp_path / "news/vb_latest.csv").exists()
        run_retention(tmp_path, keep_last=1, dry_run=False)
        assert not (tmp_path / "news/vb_20260101_000000.csv").exists()
        assert not (tmp_path / "news/vb_20260102_000000.csv").exists()
        assert (tmp_path / "news/vb_20260103_000000.csv").exists()
        assert (tmp_path / "news/vb_latest.csv").exists()

    def test_apply_refuses_unsafe_handbuilt_actions(self, tmp_path):
        """Hand-built actions pointing at *_latest.json are refused, not deleted."""
        latest = _write(tmp_path / "keep_latest.json", "important")
        from src.utils.snapshot_retention import PruneAction

        action = PruneAction(path=latest, group="g", timestamp=datetime(2026, 1, 1), size_bytes=9)
        report = apply_prune([action], dry_run=False)
        assert latest.exists()
        assert report.failed == 1
        assert report.deleted == 0


class TestCliMain:
    """CLI entry point behaviour."""

    def test_main_defaults_to_dry_run(self, tmp_path):
        """No --apply: exit 0, nothing deleted."""
        paths = self._make_cli_files(tmp_path)
        assert main(["--data-dir", str(tmp_path), "--keep-last", "2"]) == 0
        assert all(p.exists() for p in paths)

    def test_main_apply_deletes(self, tmp_path):
        """--apply deletes the oldest files beyond keep_last."""
        paths = self._make_cli_files(tmp_path)
        assert main(["--data-dir", str(tmp_path), "--keep-last", "2", "--apply"]) == 0
        assert not paths[0].exists()
        assert paths[-1].exists()

    def test_main_dry_run_false_flag_deletes(self, tmp_path):
        """--dry-run=false also enables deletion."""
        paths = self._make_cli_files(tmp_path)
        assert main(["--data-dir", str(tmp_path), "--keep-last", "1", "--dry-run=false"]) == 0
        assert not paths[0].exists() and not paths[1].exists() and not paths[2].exists()
        assert paths[3].exists()  # newest snapshot survives keep_last=1

    def test_main_rejects_bad_keep_last(self, tmp_path):
        """keep_last=0 exits non-zero without touching anything."""
        paths = self._make_cli_files(tmp_path)
        assert main(["--data-dir", str(tmp_path), "--keep-last", "0"]) == 1
        assert all(p.exists() for p in paths)

    @staticmethod
    def _make_cli_files(tmp_path):
        """Write four snapshots oldest-first; return the paths."""
        timestamps = ["20260101_000000", "20260102_000000", "20260103_000000", "20260104_000000"]
        return [_write(tmp_path / f"out_{ts}.json") for ts in timestamps]
