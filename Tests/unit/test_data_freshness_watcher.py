"""Unit tests for the Data Freshness Watcher (T-042)."""

import json
import os
import time

from src.watchers.data_freshness_watcher import SOURCE_FILES, assess_freshness


def _touch(path, age_hours):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[]", encoding="utf-8")
    stamp = time.time() - age_hours * 3600
    os.utime(path, (stamp, stamp))


def _registry(path_rel):
    return [{"key": "t", "label": "Test", "path": path_rel, "warn_hours": 26, "critical_hours": 168}]


def test_fresh_stale_critical_thresholds(tmp_path):
    rel = "news/x_latest.json"
    srcs = _registry(rel)
    _touch(tmp_path / rel, 1)
    assert assess_freshness(srcs, data_dir=tmp_path)["sources"][0]["status"] == "fresh"
    _touch(tmp_path / rel, 30)
    assert assess_freshness(srcs, data_dir=tmp_path)["sources"][0]["status"] == "stale"
    _touch(tmp_path / rel, 200)
    assert assess_freshness(srcs, data_dir=tmp_path)["sources"][0]["status"] == "critical"


def test_missing_file_is_critical(tmp_path):
    summary = assess_freshness(_registry("news/never.json"), data_dir=tmp_path)
    rec = summary["sources"][0]
    assert rec["status"] == "critical" and rec["exists"] is False and rec["age_hours"] is None


def test_counts_and_checked_at(tmp_path):
    rel = "a.json"
    _touch(tmp_path / rel, 2)
    summary = assess_freshness([*_registry(rel), *_registry("missing.json")], data_dir=tmp_path)
    assert summary["counts"] == {"fresh": 1, "stale": 0, "critical": 1}
    assert summary["checked_at"]


def test_registry_paths_are_registry_shaped():
    assert len(SOURCE_FILES) >= 15
    for src in SOURCE_FILES:
        assert {"key", "label", "path", "warn_hours", "critical_hours"} <= set(src)
        assert src["path"].endswith(".json") and not src["path"].startswith("/")
        assert 0 < src["warn_hours"] < src["critical_hours"]


def test_watcher_writes_summary_and_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from src.watchers.data_freshness_watcher import DataFreshnessWatcher

    w = DataFreshnessWatcher()
    summary = w.check_freshness()
    assert (w.data_dir / "freshness_latest.json").exists()
    assert (w.state_file).exists()
    state = json.loads(w.state_file.read_text(encoding="utf-8"))
    assert set(state["statuses"]) == {s["key"] for s in summary["sources"]}
    events = list((w.events_dir).glob("*_freshness_initial_alert.json"))
    assert len(events) >= 1  # local repo has stale files by construction
