"""Unit tests for the Data Freshness Watcher (T-042, alert wiring in T-052)."""

import json
import os
import time
from pathlib import Path

import pytest

from src.watchers.data_freshness_watcher import SOURCE_FILES, assess_freshness

# Fixed epoch so staleness math and alert messages are deterministic.
NOW = 1_800_000_000.0


def _touch(path, age_hours, now=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[]", encoding="utf-8")
    stamp = (now if now is not None else time.time()) - age_hours * 3600
    os.utime(path, (stamp, stamp))


def _registry(path_rel):
    return [{"key": "t", "label": "Test", "path": path_rel, "warn_hours": 26, "critical_hours": 168}]


def _hermetic_watcher(tmp_path: Path, statuses: dict[str, str] | None = None):
    """Build a DataFreshnessWatcher whose state/events/output live under tmp_path.

    ``get_project_root()`` resolves from the module location (not the cwd), so
    chdir-based isolation does not work — paths are injected explicitly and the
    in-memory previous state is reset so no real ``data/`` file is read or written.
    """
    from src.watchers.data_freshness_watcher import DataFreshnessWatcher

    watcher = DataFreshnessWatcher()
    watcher.data_dir = tmp_path / "watchers" / "data_freshness"
    watcher.events_dir = watcher.data_dir / "events"
    watcher.state_file = watcher.data_dir / "state.json"
    watcher.output_file = watcher.data_dir / "freshness_latest.json"
    watcher.events_dir.mkdir(parents=True, exist_ok=True)
    watcher.previous_state = {"statuses": statuses or {}, "first_seen": "2026-08-28T00:00:00"}
    return watcher


def _run_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, age_hours: float, statuses: dict[str, str] | None = None):
    """One hermetic check over a single-source registry; returns (watcher, rules, rules_file)."""
    from src.watchers import data_freshness_watcher as dfw

    monkeypatch.setattr(dfw, "SOURCE_FILES", _registry("news/x_latest.json"))
    data_dir = tmp_path / "data"
    _touch(data_dir / "news" / "x_latest.json", age_hours, now=NOW)
    rules_file = tmp_path / "alerts" / "rules.json"
    watcher = _hermetic_watcher(tmp_path, statuses)
    watcher.check_freshness(data_dir=data_dir, now=NOW, rules_file=rules_file)
    rules = json.loads(rules_file.read_text(encoding="utf-8")) if rules_file.exists() else []
    return watcher, rules, rules_file


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
    """Summary, state, and initial-alert event land under the injected tmp dirs."""
    watcher, _, _ = _run_check(tmp_path, monkeypatch, age_hours=30)
    summary = json.loads((watcher.data_dir / "freshness_latest.json").read_text(encoding="utf-8"))
    assert set(summary) == {"checked_at", "counts", "sources"}  # schema unchanged for Metrics tab card
    assert watcher.state_file.exists()
    state = json.loads(watcher.state_file.read_text(encoding="utf-8"))
    assert set(state["statuses"]) == {s["key"] for s in summary["sources"]}
    events = list(watcher.events_dir.glob("*_freshness_initial_alert.json"))
    assert len(events) == 1  # the synthetic stale file


# --- Alert-rule wiring (T-052): watcher -> data/alerts/rules.json -> Notifications tab ---


def test_stale_source_creates_exactly_one_medium_rule(tmp_path, monkeypatch):
    _, rules, _ = _run_check(tmp_path, monkeypatch, age_hours=30)
    assert len(rules) == 1
    rule = rules[0]
    assert rule["id"] == "data_freshness_t"
    assert rule["severity"] == "medium"
    assert rule["active"] is True
    assert rule["description"].startswith("Fuente Test sin datos desde ")
    assert rule["description"].endswith("(30h)")


def test_critical_source_creates_high_severity_rule(tmp_path, monkeypatch):
    _, rules, _ = _run_check(tmp_path, monkeypatch, age_hours=200)
    assert len(rules) == 1
    assert rules[0]["severity"] == "high"
    assert rules[0]["description"].endswith("(200h)")


def test_missing_source_file_alerts_as_high(tmp_path, monkeypatch):
    """A missing file is critical by definition — rule exists with the no-file message."""
    from src.watchers import data_freshness_watcher as dfw

    monkeypatch.setattr(dfw, "SOURCE_FILES", _registry("news/never.json"))
    rules_file = tmp_path / "alerts" / "rules.json"
    watcher = _hermetic_watcher(tmp_path)
    watcher.check_freshness(data_dir=tmp_path / "data", now=NOW, rules_file=rules_file)
    rules = json.loads(rules_file.read_text(encoding="utf-8"))
    assert len(rules) == 1
    assert rules[0]["severity"] == "high"
    assert rules[0]["description"] == "Fuente Test sin datos (archivo ausente)"


def test_recheck_with_same_freshness_upserts_without_duplicates(tmp_path, monkeypatch):
    """Repeated checks with unchanged freshness keep exactly one identical rule."""
    watcher, rules, rules_file = _run_check(tmp_path, monkeypatch, age_hours=30)
    assert len(rules) == 1
    first_created, first_updated = rules[0]["created_at"], rules[0]["updated_at"]

    watcher.check_freshness(data_dir=tmp_path / "data", now=NOW, rules_file=rules_file)
    rules_again = json.loads(rules_file.read_text(encoding="utf-8"))
    assert len(rules_again) == 1  # no duplicate
    assert rules_again[0]["id"] == "data_freshness_t"
    assert rules_again[0]["created_at"] == first_created
    assert rules_again[0]["updated_at"] == first_updated  # unchanged pass leaves the rule untouched


def test_recovery_to_fresh_resolves_rule_and_records_event(tmp_path, monkeypatch):
    watcher, rules, rules_file = _run_check(tmp_path, monkeypatch, age_hours=30)
    assert len(rules) == 1

    _touch(tmp_path / "data" / "news" / "x_latest.json", 1, now=NOW)  # fresh again
    watcher.check_freshness(data_dir=tmp_path / "data", now=NOW, rules_file=rules_file)
    assert json.loads(rules_file.read_text(encoding="utf-8")) == []  # rule resolved/cleared
    assert list(watcher.events_dir.glob("*_freshness_stale_to_fresh.json"))  # transition event kept


def test_all_fresh_sources_create_no_rules(tmp_path, monkeypatch):
    _, rules, rules_file = _run_check(tmp_path, monkeypatch, age_hours=1)
    assert rules == []
    assert not rules_file.exists()  # nothing to alert on — store not even created


def test_manual_rules_are_preserved(tmp_path, monkeypatch):
    """The sync only manages data_freshness_* rules; user rules pass through untouched."""
    from src.watchers import data_freshness_watcher as dfw

    monkeypatch.setattr(dfw, "SOURCE_FILES", _registry("news/x_latest.json"))
    rules_file = tmp_path / "alerts" / "rules.json"
    manual = {"id": "rule_manual", "name": "Manual rule", "active": True}
    rules_file.parent.mkdir(parents=True, exist_ok=True)
    rules_file.write_text(json.dumps([manual]), encoding="utf-8")

    data_dir = tmp_path / "data"
    _touch(data_dir / "news" / "x_latest.json", 30, now=NOW)
    watcher = _hermetic_watcher(tmp_path)
    watcher.check_freshness(data_dir=data_dir, now=NOW, rules_file=rules_file)
    assert sorted(r["id"] for r in json.loads(rules_file.read_text(encoding="utf-8"))) == ["data_freshness_t", "rule_manual"]

    _touch(data_dir / "news" / "x_latest.json", 1, now=NOW)  # recover
    watcher.check_freshness(data_dir=data_dir, now=NOW, rules_file=rules_file)
    assert json.loads(rules_file.read_text(encoding="utf-8")) == [manual]
