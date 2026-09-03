"""Tests for the watcher-events daily summary builder (T-083).

Covers window filtering, grouping, message derivation and tolerance of
malformed filenames/payloads. All event files live under ``tmp_path`` — the
real ``data/`` tree is never touched.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.services.watcher_events import _format_relative, build_daily_summary

NOW = datetime(2026, 9, 3, 12, 0, 0)


def _write_event(
    root: Path,
    watcher: str,
    stamp: datetime,
    name_suffix: str = "change_detected",
    payload: dict[str, Any] | None = None,
    filename: str | None = None,
) -> Path:
    """Write one event file mirroring ``BaseWatcher._record_event``'s contract."""
    events_dir = root / watcher / "events"
    events_dir.mkdir(parents=True, exist_ok=True)
    fname = filename or f"{stamp:%Y%m%d%H%M%S}_{name_suffix}.json"
    if payload is None:
        payload = {
            "id": fname,
            "type": name_suffix,
            "timestamp": stamp.isoformat(),
            "watcher": watcher,
            "old_value": None,
            "new_value": None,
            "details": {},
        }
    path = events_dir / fname
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class TestWindowFiltering:
    """Only events stamped inside the look-back window are considered."""

    def test_missing_root_yields_empty_summary(self, tmp_path: Path) -> None:
        """A nonexistent events root (first deploy) gives an empty summary."""
        summary = build_daily_summary(events_root=tmp_path / "nope", now=NOW)
        assert summary.total == 0
        assert summary.groups == []
        assert summary.per_watcher == {}
        assert summary.window_hours == 24

    def test_events_older_than_window_ignored(self, tmp_path: Path) -> None:
        """Files older than 24h are never grouped."""
        _write_event(tmp_path, "courses", NOW - timedelta(hours=48))
        summary = build_daily_summary(events_root=tmp_path, now=NOW)
        assert summary.total == 0

    def test_window_hours_parameter_respected(self, tmp_path: Path) -> None:
        """A tighter window excludes events inside the default one."""
        _write_event(tmp_path, "courses", NOW - timedelta(hours=3))
        assert build_daily_summary(events_root=tmp_path, now=NOW, window_hours=1).total == 0
        assert build_daily_summary(events_root=tmp_path, now=NOW, window_hours=24).total == 1

    def test_future_dated_files_beyond_slack_ignored(self, tmp_path: Path) -> None:
        """Far-future stamps (clock skew) are skipped; small slack is kept."""
        _write_event(tmp_path, "courses", NOW + timedelta(hours=2))
        _write_event(tmp_path, "courses", NOW + timedelta(minutes=1))
        summary = build_daily_summary(events_root=tmp_path, now=NOW)
        assert summary.total == 1


class TestGrouping:
    """Events are bucketed by (watcher, event_type) with latest-first ordering."""

    def test_groups_by_watcher_and_type(self, tmp_path: Path) -> None:
        """Two events of one type collapse; another type stays separate."""
        _write_event(tmp_path, "courses", NOW - timedelta(hours=5))
        _write_event(tmp_path, "courses", NOW - timedelta(hours=1))
        _write_event(tmp_path, "courses", NOW - timedelta(hours=2), name_suffix="papers_changed")
        summary = build_daily_summary(events_root=tmp_path, now=NOW)
        assert summary.total == 3
        assert len(summary.groups) == 2
        by_type = {g.event_type: g for g in summary.groups}
        assert by_type["change_detected"].count == 2
        assert by_type["papers_changed"].count == 1
        assert summary.per_watcher == {"courses": 3}

    def test_sequence_suffixed_files_merge_by_content_type(self, tmp_path: Path) -> None:
        """Courses-style ``_001``/``_002`` filenames merge on the in-file type."""
        for seq in ("001", "002"):
            stamp = NOW - timedelta(hours=1)
            _write_event(
                tmp_path,
                "courses",
                stamp,
                filename=f"{stamp:%Y%m%d%H%M%S}_new_matching_course_{seq}.json",
                payload={
                    "id": f"{stamp:%Y%m%d%H%M%S}_new_matching_course_{seq}",
                    "type": "new_matching_course",
                    "timestamp": stamp.isoformat(),
                    "watcher": "courses",
                    "old_value": None,
                    "new_value": f"Course {seq}",
                    "details": {"message": f"Nuevo curso que matchea: Course {seq}"},
                },
            )
        summary = build_daily_summary(events_root=tmp_path, now=NOW)
        assert len(summary.groups) == 1
        group = summary.groups[0]
        assert group.event_type == "new_matching_course"
        assert group.count == 2

    def test_message_comes_from_latest_event(self, tmp_path: Path) -> None:
        """The sample message is taken from the newest event of the bucket."""
        _write_event(tmp_path, "courses", NOW - timedelta(hours=4), payload={"type": "change_detected", "details": {"message": "older"}})
        _write_event(tmp_path, "courses", NOW - timedelta(hours=1), payload={"type": "change_detected", "details": {"message": "newer"}})
        summary = build_daily_summary(events_root=tmp_path, now=NOW)
        assert summary.groups[0].message == "newer"

    def test_groups_sorted_newest_first(self, tmp_path: Path) -> None:
        """Buckets are ordered by their latest event, descending."""
        _write_event(tmp_path, "a_watcher", NOW - timedelta(hours=5))
        _write_event(tmp_path, "b_watcher", NOW - timedelta(hours=1))
        summary = build_daily_summary(events_root=tmp_path, now=NOW)
        assert [g.watcher for g in summary.groups] == ["b_watcher", "a_watcher"]

    def test_per_watcher_breakdown_and_total(self, tmp_path: Path) -> None:
        """Totals aggregate per watcher, highest count first."""
        _write_event(tmp_path, "courses", NOW - timedelta(hours=1))
        _write_event(tmp_path, "courses", NOW - timedelta(hours=2))
        _write_event(tmp_path, "data_freshness", NOW - timedelta(hours=3), name_suffix="freshness_initial_alert")
        summary = build_daily_summary(events_root=tmp_path, now=NOW)
        assert summary.total == 3
        assert list(summary.per_watcher.items()) == [("courses", 2), ("data_freshness", 1)]

    def test_latest_relative_is_prewarmed(self, tmp_path: Path) -> None:
        """Each group carries a ready-to-render relative timestamp."""
        _write_event(tmp_path, "courses", NOW - timedelta(hours=2))
        summary = build_daily_summary(events_root=tmp_path, now=NOW)
        assert summary.groups[0].latest_relative == "hace 2 h"


class TestTolerance:
    """Malformed names, payloads and odd directory shapes never raise."""

    def test_malformed_filenames_skipped(self, tmp_path: Path) -> None:
        """Filenames without a valid 14-digit prefix are ignored."""
        events_dir = tmp_path / "courses" / "events"
        events_dir.mkdir(parents=True)
        for name in ("not_a_timestamp.json", "20260903_x.json", "20261303120000_impossible_month.json"):
            (events_dir / name).write_text("{}", encoding="utf-8")
        assert build_daily_summary(events_root=tmp_path, now=NOW).total == 0

    def test_malformed_json_counted_under_stem_type(self, tmp_path: Path) -> None:
        """An unreadable payload still counts, grouped by filename remainder."""
        stamp = NOW - timedelta(hours=1)
        events_dir = tmp_path / "courses" / "events"
        events_dir.mkdir(parents=True)
        (events_dir / f"{stamp:%Y%m%d%H%M%S}_change_detected.json").write_text("{not json", encoding="utf-8")
        summary = build_daily_summary(events_root=tmp_path, now=NOW)
        assert summary.total == 1
        group = summary.groups[0]
        assert group.event_type == "change_detected"
        assert group.message == "change_detected"

    def test_non_dict_json_payload_counted_under_stem_type(self, tmp_path: Path) -> None:
        """A JSON array payload counts but contributes no message details."""
        events_dir = tmp_path / "courses" / "events"
        events_dir.mkdir(parents=True)
        (events_dir / f"{NOW:%Y%m%d%H%M%S}_change_detected.json").write_text("[1, 2]", encoding="utf-8")
        summary = build_daily_summary(events_root=tmp_path, now=NOW)
        assert summary.groups[0].message == "change_detected"

    def test_non_json_files_ignored(self, tmp_path: Path) -> None:
        """Only ``*.json`` files are candidates."""
        events_dir = tmp_path / "courses" / "events"
        events_dir.mkdir(parents=True)
        (events_dir / f"{NOW:%Y%m%d%H%M%S}_change_detected.txt").write_text("x", encoding="utf-8")
        assert build_daily_summary(events_root=tmp_path, now=NOW).total == 0

    def test_watcher_dir_without_events_dir_ignored(self, tmp_path: Path) -> None:
        """A watcher directory holding only state/other files is fine."""
        watcher_dir = tmp_path / "courses"
        watcher_dir.mkdir(parents=True)
        (watcher_dir / "state.json").write_text("{}", encoding="utf-8")
        assert build_daily_summary(events_root=tmp_path, now=NOW).total == 0

    def test_empty_events_dir_is_fine(self, tmp_path: Path) -> None:
        """An existing but empty events dir yields an empty summary."""
        (tmp_path / "courses" / "events").mkdir(parents=True)
        summary = build_daily_summary(events_root=tmp_path, now=NOW)
        assert summary.total == 0
        assert summary.groups == []


class TestMessageDerivation:
    """Human messages come from details.message, details.label, or old→new."""

    def test_courses_message_from_details(self, tmp_path: Path) -> None:
        """``details.message`` (courses watcher) wins verbatim."""
        _write_event(
            tmp_path,
            "courses",
            NOW - timedelta(hours=1),
            payload={"type": "new_matching_course", "details": {"message": "Nuevo curso que matchea tus keywords: Python"}},
        )
        summary = build_daily_summary(events_root=tmp_path, now=NOW)
        assert summary.groups[0].message == "Nuevo curso que matchea tus keywords: Python"

    def test_freshness_message_with_label_and_age(self, tmp_path: Path) -> None:
        """Freshness events render label + transition + age note."""
        _write_event(
            tmp_path,
            "data_freshness",
            NOW - timedelta(hours=1),
            name_suffix="freshness_stale_to_critical",
            payload={
                "type": "freshness_stale_to_critical",
                "old_value": "stale",
                "new_value": "critical",
                "details": {"label": "Itch.io trending", "age_hours": 26.5, "exists": True},
            },
        )
        summary = build_daily_summary(events_root=tmp_path, now=NOW)
        message = summary.groups[0].message
        assert "Itch.io trending" in message
        assert "stale → critical" in message
        assert "(26 h sin datos)" in message

    def test_generic_change_message_old_to_new(self, tmp_path: Path) -> None:
        """Events without details fall back to an old → new preview."""
        _write_event(tmp_path, "test_watcher", NOW - timedelta(hours=1), payload={"type": "change_detected", "old_value": 3, "new_value": 7, "details": {}})
        summary = build_daily_summary(events_root=tmp_path, now=NOW)
        assert summary.groups[0].message == "3 → 7"

    def test_no_values_falls_back_to_type(self, tmp_path: Path) -> None:
        """No message/label/values at all: the event type is the message."""
        _write_event(tmp_path, "test_watcher", NOW - timedelta(hours=1), payload={"type": "check_started", "old_value": None, "new_value": None, "details": {}})
        summary = build_daily_summary(events_root=tmp_path, now=NOW)
        assert summary.groups[0].message == "check_started"

    def test_long_values_are_truncated(self, tmp_path: Path) -> None:
        """Huge old/new values (e.g. paper lists) are capped for display."""
        _write_event(tmp_path, "arxiv", NOW - timedelta(hours=1), payload={"type": "papers_changed", "old_value": "x" * 300, "new_value": "y" * 300, "details": {}})
        summary = build_daily_summary(events_root=tmp_path, now=NOW)
        assert len(summary.groups[0].message) < 200
        assert "…" in summary.groups[0].message


class TestFormatRelative:
    """Direct checks of the Spanish relative-time formatter."""

    def test_recent(self) -> None:
        """Under a minute reads as 'hace unos segundos'."""
        assert _format_relative(NOW - timedelta(seconds=30), NOW) == "hace unos segundos"

    def test_minutes(self) -> None:
        """Minutes bucket."""
        assert _format_relative(NOW - timedelta(minutes=45), NOW) == "hace 45 min"

    def test_hours(self) -> None:
        """Hours bucket (style shared with health badges)."""
        assert _format_relative(NOW - timedelta(hours=5), NOW) == "hace 5 h"

    def test_days(self) -> None:
        """Beyond 48h switches to days."""
        assert _format_relative(NOW - timedelta(days=3), NOW) == "hace 3 d"
