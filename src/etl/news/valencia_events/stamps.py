"""When each event was first detected, kept across runs in a small state file.

The tab's "Nuevos desde tu última visita" needs to know whether an event is
newer than the visitor's last visit. That cannot be read off the data file: the
whole file is rewritten on every run, so every record looks fresh. The state
file, ``data/valencia_events/detected_at.json``, remembers two moments per
event id: the run that first saw it and the last run that saw it. The first is
never moved; the second lets a record that disappeared and came back be treated
as new again, and prunes entries nobody has seen for :data:`RETENTION_DAYS`.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

from src.etl.news.valencia_events.dates import iso, parse_moment
from src.etl.news.valencia_events.storage import write_text_atomic

STAMPS_FILE = "detected_at.json"
STAMPS_VERSION = 1
RETENTION_DAYS = 400

Stamps = dict[str, dict[str, str]]


def load_stamps(path: Path) -> Stamps:
    """Read the state file; an absent, unreadable or malformed file means nothing is known yet."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    events = data.get("events") if isinstance(data, dict) else None
    if not isinstance(events, dict):
        return {}
    clean: Stamps = {}
    for event_id, entry in events.items():
        if not isinstance(entry, dict) or not entry.get("first_detected_at"):
            continue
        first = str(entry["first_detected_at"])
        clean[str(event_id)] = {"first_detected_at": first, "last_seen_at": str(entry.get("last_seen_at") or first)}
    return clean


def update_stamps(stamps: Stamps, event_ids: list[str], now: datetime) -> Stamps:
    """The stamps after a run that saw ``event_ids``.

    Args:
        stamps: The stamps before the run.
        event_ids: Ids of every event of the new file.
        now: The moment of the run, aware.

    Returns:
        A new dict: for each seen id the first detection is kept (or set to
        ``now``) and the last sighting is ``now``; an id not seen in this run
        is kept as it was until it has not been seen for
        :data:`RETENTION_DAYS`, then dropped.
    """
    horizon = now - timedelta(days=RETENTION_DAYS)
    updated: Stamps = {}
    for event_id in event_ids:
        previous = stamps.get(event_id)
        first = previous["first_detected_at"] if previous else iso(now)
        updated[event_id] = {"first_detected_at": first, "last_seen_at": iso(now)}
    for event_id, entry in stamps.items():
        if event_id in updated:
            continue
        last_seen = parse_moment(entry.get("last_seen_at"))
        if last_seen is not None and last_seen >= horizon:
            updated[event_id] = dict(entry)
    return updated


def save_stamps(path: Path, stamps: Stamps, now: datetime) -> None:
    """Write the state file atomically."""
    payload = {"version": STAMPS_VERSION, "updated_at": iso(now), "events": dict(sorted(stamps.items()))}
    write_text_atomic(path, json.dumps(payload, indent=2, ensure_ascii=False))
