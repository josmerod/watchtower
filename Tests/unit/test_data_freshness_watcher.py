"""Unit tests for the Data Freshness Watcher (T-042, alert wiring in T-052)."""

import json
import os
import time
from datetime import datetime, timezone
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


# --- The age of the content (T-176): a file rewritten every cycle can hold years-old items ---


def _dated_source(path_rel, field="published_at"):
    return [{"key": "t", "label": "Test", "path": path_rel, "warn_hours": 26, "critical_hours": 168, "content_date": field}]


def _ago(hours, form="iso"):
    """A date ``hours`` before NOW, in the form a feed writes it."""
    moment = datetime.fromtimestamp(NOW - hours * 3600, tz=timezone.utc)
    if form == "rfc":
        return moment.strftime("%a, %d %b %Y %H:%M:%S +0000")
    if form == "naive":
        return moment.strftime("%Y-%m-%dT%H:%M:%S")
    return moment.isoformat()


def _write_items(path, dates, age_hours=1, field="published_at"):
    """A file rewritten ``age_hours`` ago whose items carry the given dates."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([{"title": f"item {i}", field: date} for i, date in enumerate(dates)]), encoding="utf-8")
    stamp = NOW - age_hours * 3600
    os.utime(path, (stamp, stamp))


def test_a_file_rewritten_every_cycle_with_old_items_is_critical(tmp_path):
    """FutureTools in 2026: written every 2 h, newest item from 2024-05."""
    rel = "futuretools/news.json"
    newest = datetime(2024, 5, 1, 16, 7, 36, tzinfo=timezone.utc)
    _write_items(tmp_path / rel, ["2024-04-28T18:12:13+00:00", newest.isoformat(), "2024-03-11T17:32:49Z"])

    record = assess_freshness(_dated_source(rel), data_dir=tmp_path, now=NOW)["sources"][0]

    expected = round((NOW - newest.timestamp()) / 3600, 1)
    assert record["status"] == "critical"
    assert record["content_age_hours"] == expected
    assert record["age_hours"] == expected  # the age that decided is the one the alert shows


def test_nothing_new_for_a_week_is_stale(tmp_path):
    rel = "tldr/news.json"
    _write_items(tmp_path / rel, [_ago(400), _ago(200)])

    record = assess_freshness(_dated_source(rel), data_dir=tmp_path, now=NOW)["sources"][0]

    assert record["status"] == "stale"
    assert record["content_age_hours"] == 200.0
    assert record["age_hours"] == 200.0


def test_a_digest_that_publishes_twice_a_week_stays_fresh(tmp_path):
    rel = "bensbites/news.json"
    _write_items(tmp_path / rel, [_ago(500), _ago(60)])

    record = assess_freshness(_dated_source(rel), data_dir=tmp_path, now=NOW)["sources"][0]

    assert record["status"] == "fresh"
    assert record["content_age_hours"] == 60.0
    assert record["age_hours"] == 1.0  # the file is what was written an hour ago


def test_the_age_of_the_file_still_decides_when_its_items_are_new(tmp_path):
    rel = "hackernews/news.json"
    _write_items(tmp_path / rel, [_ago(1)], age_hours=200)

    record = assess_freshness(_dated_source(rel), data_dir=tmp_path, now=NOW)["sources"][0]

    assert record["status"] == "critical"
    assert record["age_hours"] == 200.0
    assert record["content_age_hours"] == 1.0


def test_dates_are_read_in_the_forms_the_feeds_write_them(tmp_path):
    rel = "news/mixed.json"
    _write_items(tmp_path / rel, [_ago(100), _ago(50, "naive"), _ago(30, "rfc")], field="published")

    record = assess_freshness(_dated_source(rel, field="published"), data_dir=tmp_path, now=NOW)["sources"][0]

    assert record["content_age_hours"] == 30.0


def test_items_without_a_readable_date_are_not_judged(tmp_path):
    rel = "news/undated.json"
    _write_items(tmp_path / rel, ["", "yesterday", None])

    record = assess_freshness(_dated_source(rel), data_dir=tmp_path, now=NOW)["sources"][0]

    assert record["status"] == "fresh"
    assert "content_age_hours" not in record


def test_a_file_that_is_not_json_is_judged_by_its_age_only(tmp_path):
    rel = "news/broken.json"
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('["cut in the middle of', encoding="utf-8")
    os.utime(path, (NOW - 3600, NOW - 3600))

    record = assess_freshness(_dated_source(rel), data_dir=tmp_path, now=NOW)["sources"][0]

    assert record["status"] == "fresh"  # by the file's own age (written an hour ago)
    assert "content_age_hours" not in record


def test_an_object_holding_one_list_of_items_is_read(tmp_path):
    rel = "news/wrapped.json"
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"fetched_at": _ago(1), "articles": [{"title": "a", "published_at": _ago(300)}]}), encoding="utf-8")
    os.utime(path, (NOW - 3600, NOW - 3600))

    record = assess_freshness(_dated_source(rel), data_dir=tmp_path, now=NOW)["sources"][0]

    assert record["status"] == "stale"
    assert record["content_age_hours"] == 300.0


def test_every_news_source_is_registered_with_its_content_date():
    """No file of the News tab may sit outside the registry: three dead ones went unnoticed for months."""
    from src.services.data_loader import NEWS_SOURCES_CONFIG

    registered = {entry["path"]: entry for entry in SOURCE_FILES}
    missing = []
    for key, config in NEWS_SOURCES_CONFIG.items():
        rel = Path(config["path"]).as_posix().split("/data/")[-1]
        if rel not in registered or not registered[rel].get("content_date"):
            missing.append(key)
    assert not missing, f"without a dated entry in SOURCE_FILES: {missing}"
    assert len({entry["key"] for entry in SOURCE_FILES}) == len(SOURCE_FILES)  # one alert rule per source


def test_the_game_deal_feeds_are_watched_by_the_age_of_their_items(tmp_path):
    """deals.json and bundles.json kept July data for four months: never rewritten, and watched by nobody (T-192)."""
    registered = {entry["key"]: entry for entry in SOURCE_FILES}
    for key in ("games_deals", "games_bundles"):
        assert registered[key]["content_date"] == "published"

    entry = dict(registered["games_deals"], path="games/deals.json")
    _write_items(tmp_path / "games/deals.json", [_ago(48)], field="published")  # the file is an hour old
    assert assess_freshness([entry], data_dir=tmp_path, now=NOW)["sources"][0]["status"] == "stale"  # a week for the others

    _write_items(tmp_path / "games/deals.json", [_ago(128 * 24)], field="published")  # the file as found on 2026-11-27
    record = assess_freshness([entry], data_dir=tmp_path, now=NOW)["sources"][0]
    assert record["status"] == "critical"
    assert record["age_hours"] == 128 * 24  # the rule shows the age of the deals, not of the file


def test_a_source_keeps_the_common_thresholds_unless_it_sets_its_own(tmp_path):
    entry = {**_dated_source("games/b.json", field="published")[0], "content_warn_hours": 72, "content_critical_hours": 336}
    _write_items(tmp_path / "games/b.json", [_ago(100)], field="published")

    assert assess_freshness([entry], data_dir=tmp_path, now=NOW)["sources"][0]["status"] == "stale"
    assert assess_freshness([{k: v for k, v in entry.items() if not k.startswith("content_") or k == "content_date"}], data_dir=tmp_path, now=NOW)["sources"][0]["status"] == "fresh"


def test_a_source_with_old_items_gets_a_high_rule_that_names_the_date(tmp_path, monkeypatch):
    from src.watchers import data_freshness_watcher as dfw

    rel = "futuretools/news.json"
    monkeypatch.setattr(dfw, "SOURCE_FILES", _dated_source(rel))
    newest = datetime(2024, 5, 1, 16, 7, 36, tzinfo=timezone.utc)
    _write_items(tmp_path / "data" / rel, [newest.isoformat()])
    rules_file = tmp_path / "alerts" / "rules.json"
    watcher = _hermetic_watcher(tmp_path)
    watcher.check_freshness(data_dir=tmp_path / "data", now=NOW, rules_file=rules_file)
    rules = json.loads(rules_file.read_text(encoding="utf-8"))

    age = round((NOW - newest.timestamp()) / 3600, 1)
    # the rule dates the source from the age it is given, rounded to a tenth of an hour
    since = datetime.fromtimestamp(NOW - age * 3600, tz=timezone.utc)
    assert [(rule["id"], rule["severity"]) for rule in rules] == [("data_freshness_t", "high")]
    assert rules[0]["description"] == f"Fuente Test sin datos desde {since:%Y-%m-%d %H:%M} UTC ({age:g}h)"
    assert age > 23_000  # the date in the message is the item's, not the file's (written an hour ago)
    event = json.loads(next(watcher.events_dir.glob("*_freshness_initial_alert.json")).read_text(encoding="utf-8"))
    assert event["details"]["content_age_hours"] == age


def test_the_open_source_file_is_watched_by_the_age_of_its_items(tmp_path):
    """latest.json kept a post from 2026-04-29 for seven months while its ETL ended every cycle at zero (T-204)."""
    entry = {entry["key"]: entry for entry in SOURCE_FILES}["opensource_projects"]
    assert entry["path"] == "open_source_intelligence/output/latest.json"
    assert entry["content_date"] == "published_at"

    # The site skips two or three days between batches every few weeks: four days are still fresh.
    _write_items(tmp_path / entry["path"], [_ago(96, "naive")], age_hours=1)
    assert assess_freshness([entry], data_dir=tmp_path, now=NOW)["sources"][0]["status"] == "fresh"

    # A quiet weekend: nothing new to write, so the file itself is two days old too.
    _write_items(tmp_path / entry["path"], [_ago(48, "naive")], age_hours=48)
    assert assess_freshness([entry], data_dir=tmp_path, now=NOW)["sources"][0]["status"] == "fresh"

    # Six days without a post happened once in seventeen months: stale, not critical.
    _write_items(tmp_path / entry["path"], [_ago(6 * 24, "naive")], age_hours=1)
    assert assess_freshness([entry], data_dir=tmp_path, now=NOW)["sources"][0]["status"] == "stale"

    # The ETL keeps rewriting the file while GitHub answers: three days without a write are stale.
    _write_items(tmp_path / entry["path"], [_ago(2, "naive")], age_hours=72)
    assert assess_freshness([entry], data_dir=tmp_path, now=NOW)["sources"][0]["status"] == "stale"

    # The file as found on 2026-11-28, rewritten by the cycle a minute earlier: the rule shows the age of the post.
    _write_items(tmp_path / entry["path"], ["2026-04-29 07:26:03.537000"], age_hours=1 / 60)
    record = assess_freshness([entry], data_dir=tmp_path, now=NOW)["sources"][0]
    assert record["status"] == "critical"
    assert record["age_hours"] == record["content_age_hours"] > 240


def test_the_cinema_and_valencia_listings_are_watched_by_their_first_detection(tmp_path):
    """A screening day and an event day lie ahead and never age; what ages is the day a session or an event was first listed (T-151, T-143)."""
    entries = {entry["key"]: entry for entry in SOURCE_FILES}
    for key, path in (("cinema", "cinema/cinema_sessions_latest.json"), ("valencia_events", "valencia_events/valencia_events.json")):
        assert entries[key]["path"] == path
        assert entries[key]["content_date"] == "first_detected_at"

        # Something was first listed three days ago, and the file was rewritten a minute ago: the listings still change.
        _write_items(tmp_path / path, [_ago(72)], age_hours=1 / 60, field="first_detected_at")
        assert assess_freshness([entries[key]], data_dir=tmp_path, now=NOW)["sources"][0]["status"] == "fresh"

        # Two weeks without a session or an event nobody had seen, file rewritten a minute ago: the listings
        # no longer change, or are no longer parsed. The age that decided is the age of the listing.
        _write_items(tmp_path / path, [_ago(14 * 24)], age_hours=1 / 60, field="first_detected_at")
        record = assess_freshness([entries[key]], data_dir=tmp_path, now=NOW)["sources"][0]
        assert record["status"] == "stale"
        assert record["age_hours"] == record["content_age_hours"] > 168

        # The file itself a day and a quarter old: every run failed. A Valencia run in which no source gives
        # an event fails instead of writing a thinner file.
        _write_items(tmp_path / path, [_ago(1)], age_hours=30, field="first_detected_at")
        record = assess_freshness([entries[key]], data_dir=tmp_path, now=NOW)["sources"][0]
        assert record["status"] == "stale" and record["age_hours"] == 30.0
