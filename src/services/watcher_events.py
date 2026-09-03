"""Daily roll-up of watcher events for the dashboard's Notifications tab.

Watcher events are persisted by ``BaseWatcher._record_event`` (and per-watcher
variants such as ``CoursesWatcher._record_course_event``) as JSON files named
``YYYYMMDDHHMMSS_<event_type>.json`` under ``data/watchers/<name>/events/``.
This module scans those files for the last ``window_hours`` (24 by default),
groups them by ``(watcher, event_type)`` and produces a small summary object
the Notifications tab renders as its "Últimas 24h" resumen.

Timestamps in filenames are naive local time (that is how watchers stamp them),
so all window math here is naive-local too.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.utils.file_system import get_project_root

#: Look-back window of the daily resumen, in hours.
DEFAULT_WINDOW_HOURS = 24

#: Length of the ``YYYYMMDDHHMMSS`` prefix in event filenames.
_TIMESTAMP_PREFIX_LEN = 14

#: Safety valve so a runaway events dir can never stall the dashboard.
_MAX_EVENT_READS = 500

#: Tolerance for filenames stamped slightly in the future (clock skew).
_FUTURE_SLACK = timedelta(minutes=5)

#: Cap for stringified ``old_value``/``new_value`` preview text.
_VALUE_PREVIEW_LEN = 80


@dataclass(frozen=True)
class EventGroup:
    """A ``(watcher, event_type)`` bucket of events inside the window.

    Attributes:
        watcher: Watcher directory name the events came from.
        event_type: Event type as recorded in the file (filename remainder as
            fallback when the payload was unreadable).
        count: Number of events in the window for this bucket.
        latest: Naive-local timestamp of the newest event (from the filename).
        latest_relative: ``latest`` humanized relative to the scan's "now"
            (e.g. ``"hace 3 h"``), precomputed so the tab renders purely.
        message: Human message derived from the newest event's details.
    """

    watcher: str
    event_type: str
    count: int
    latest: datetime
    latest_relative: str
    message: str


@dataclass(frozen=True)
class WatcherEventsSummary:
    """Roll-up of watcher events for the last ``window_hours``.

    Attributes:
        total: Total number of events in the window across all watchers.
        window_hours: Size of the look-back window in hours.
        groups: ``(watcher, event_type)`` buckets, newest first.
        per_watcher: Event count per watcher, highest count first.
        generated_at: The "now" the summary was computed against.
    """

    total: int
    window_hours: int
    groups: list[EventGroup]
    per_watcher: dict[str, int]
    generated_at: datetime


def _timestamp_from_filename(filename: str) -> datetime | None:
    """Parse the ``YYYYMMDDHHMMSS`` prefix of an event filename.

    Args:
        filename: Event filename such as ``20260827161225_freshness_initial_alert.json``.

    Returns:
        Naive local datetime, or ``None`` when the prefix is missing/malformed.
    """
    prefix = filename.split("_", 1)[0]
    if len(prefix) != _TIMESTAMP_PREFIX_LEN or not prefix.isdigit():
        return None
    try:
        return datetime.strptime(prefix, "%Y%m%d%H%M%S")
    except ValueError:  # well-formed digits, impossible date (e.g. month 13)
        return None


def _format_relative(moment: datetime, now: datetime) -> str:
    """Humanize ``moment`` relative to ``now`` in Spanish.

    Mirrors the ``"hace X h"`` style already used by the dashboard's health
    badges (``components/shared/health.py``).

    Args:
        moment: The past timestamp to describe.
        now: Reference "current" time.

    Returns:
        Text like ``"hace unos segundos"``, ``"hace 12 min"``, ``"hace 3 h"``
        or ``"hace 2 d"``.
    """
    seconds = max(0.0, (now - moment).total_seconds())
    if seconds < 60:
        return "hace unos segundos"
    if seconds < 3600:
        return f"hace {int(seconds // 60)} min"
    hours = seconds / 3600
    if hours < 48:
        return f"hace {int(hours)} h"
    return f"hace {int(hours // 24)} d"


def _preview(value: Any) -> str:
    """Render an event value as short display text."""
    if value is None:
        return "—"
    text = str(value)
    if len(text) > _VALUE_PREVIEW_LEN:
        return text[: _VALUE_PREVIEW_LEN - 1] + "…"
    return text


def _load_event(file_path: Path) -> dict[str, Any] | None:
    """Load one event JSON file.

    Args:
        file_path: Event file to read.

    Returns:
        The event payload, or ``None`` when unreadable/not a JSON object.
    """
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _event_message(event: dict[str, Any], fallback: str) -> str:
    """Derive a human message from an event's ``details`` and values.

    Priority: ``details.message`` (courses), ``details.label`` with the
    old→new transition (data freshness), then a generic ``old → new``
    preview, and finally the event type itself.

    Args:
        event: Event payload as written by the watcher.
        fallback: Text to return when the payload carries nothing readable.

    Returns:
        A single-line message suitable for the resumen rows.
    """
    details = event.get("details")
    if not isinstance(details, dict):
        details = {}
    message = details.get("message")
    if isinstance(message, str) and message.strip():
        return message
    label = details.get("label")
    if isinstance(label, str) and label.strip():
        age_hours = details.get("age_hours")
        age_note = f" ({age_hours:.0f} h sin datos)" if isinstance(age_hours, (int, float)) else ""
        return f"{label}: {_preview(event.get('old_value'))} → {_preview(event.get('new_value'))}{age_note}"
    old_value, new_value = event.get("old_value"), event.get("new_value")
    if old_value is None and new_value is None:
        return fallback
    return f"{_preview(old_value)} → {_preview(new_value)}"


def build_daily_summary(
    events_root: Path | None = None,
    now: datetime | None = None,
    window_hours: int = DEFAULT_WINDOW_HOURS,
) -> WatcherEventsSummary:
    """Compile the last ``window_hours`` of watcher events into a summary.

    Only files whose ``YYYYMMDDHH%M%S`` filename prefix falls inside the
    window are considered — older files are never opened. Malformed
    filenames are skipped; malformed payloads are still counted (grouped
    under their filename-derived type) but contribute no sample message.

    Args:
        events_root: Root holding ``<watcher>/events/`` trees (defaults to
            the project's ``data/watchers/``; a missing dir yields an empty
            summary, e.g. on a first deploy before any watcher ran).
        now: Reference "current" time for the window (defaults to local
            now; naive local time, matching how watchers stamp filenames).
        window_hours: Size of the look-back window in hours.

    Returns:
        The summary with groups (newest first), per-watcher breakdown and
        total event count.
    """
    moment = now if now is not None else datetime.now()
    cutoff = moment - timedelta(hours=window_hours)
    root = events_root if events_root is not None else Path(get_project_root()) / "data" / "watchers"

    entries: list[tuple[datetime, Path, str, str]] = []  # (stamp, path, watcher, stem type)
    if root.is_dir():
        for watcher_dir in root.iterdir():
            events_dir = watcher_dir / "events"
            if not watcher_dir.is_dir() or not events_dir.is_dir():
                continue
            for file_path in events_dir.iterdir():
                if not file_path.is_file() or file_path.suffix != ".json":
                    continue
                stamp = _timestamp_from_filename(file_path.name)
                if stamp is None or stamp < cutoff or stamp > moment + _FUTURE_SLACK:
                    continue
                stem_type = file_path.stem[_TIMESTAMP_PREFIX_LEN + 1 :] or "evento"
                entries.append((stamp, file_path, watcher_dir.name, stem_type))
    entries.sort(key=lambda entry: entry[0], reverse=True)

    # Newest files first, so the first hit per bucket carries the sample
    # message and the read cap only ever degrades the oldest tail.
    reads_left = _MAX_EVENT_READS
    counts: dict[tuple[str, str], int] = {}
    latest_stamp: dict[tuple[str, str], datetime] = {}
    latest_message: dict[tuple[str, str], str] = {}

    for stamp, file_path, watcher, stem_type in entries:
        event_type = stem_type
        message: str | None = None
        if reads_left > 0:
            reads_left -= 1
            payload = _load_event(file_path)
            if payload is not None:
                content_type = payload.get("type")
                if isinstance(content_type, str) and content_type:
                    event_type = content_type
                message = _event_message(payload, event_type)
        key = (watcher, event_type)
        counts[key] = counts.get(key, 0) + 1
        if key not in latest_stamp or stamp > latest_stamp[key]:
            latest_stamp[key] = stamp
            if message is not None:
                latest_message[key] = message
            else:
                latest_message.setdefault(key, event_type)

    groups = [
        EventGroup(
            watcher=key[0],
            event_type=key[1],
            count=count,
            latest=latest_stamp[key],
            latest_relative=_format_relative(latest_stamp[key], moment),
            message=latest_message.get(key, key[1]),
        )
        for key, count in counts.items()
    ]
    groups.sort(key=lambda group: (group.latest, group.watcher, group.event_type), reverse=True)

    per_watcher: dict[str, int] = {}
    for (watcher, _event_type), count in counts.items():
        per_watcher[watcher] = per_watcher.get(watcher, 0) + count
    ordered_per_watcher = dict(sorted(per_watcher.items(), key=lambda item: (-item[1], item[0])))

    return WatcherEventsSummary(
        total=sum(counts.values()),
        window_hours=window_hours,
        groups=groups,
        per_watcher=ordered_per_watcher,
        generated_at=moment,
    )
