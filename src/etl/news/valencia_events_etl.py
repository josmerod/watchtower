"""Valencia events: the composer of the ``valencia_events`` package.

The sources live in :mod:`src.etl.news.valencia_events.sources`, one module
each. This module stays the registered script and the single owner of the
output file ``data/valencia_events/valencia_events.json``. A run:

1. asks every source once (:meth:`ValenciaEventsETL.extract`); a failing or
   blocked source leaves the others alone;
2. merges the raw records into one per event and per session
   (:meth:`ValenciaEventsETL.transform`), then completes each of them in one
   place (:func:`~src.etl.news.valencia_events.normalise.normalise_record`):
   real datetimes with a zone, the category, the zone, the price as a number
   and the moment the event was first detected;
3. writes the file atomically, and a small state file that remembers when each
   event was first seen (:meth:`ValenciaEventsETL.load`).

A source that gives nothing in a run — empty, failed or blocked — does not
erase what it gave before: its events that have not ended are carried over for
:data:`CARRY_OVER_DAYS`, flagged ``carried_over`` in their metadata. The status
of every source is written next to the events (``sources_status.json``), so the
tab can say which agendas answered. When not one of them gives an event, the
run fails instead of "completing" over stale data (T-192).
"""

import json
import re
from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit

# The pages are read by the source modules, but ``requests`` is imported here too:
# the tests patch ``requests.get`` through this module's name, as they always did.
import requests

from src.etl.base import BaseETL, ETLError
from src.etl.news.valencia_events.categories import UNKNOWN_CATEGORY, fold
from src.etl.news.valencia_events.dates import iso, madrid_now, parse_moment
from src.etl.news.valencia_events.dates import parse_dates_from_text as _parse_dates_from_text
from src.etl.news.valencia_events.dates import to_iso_date as _to_iso_date
from src.etl.news.valencia_events.http import SourceBlockedError, blocked_hosts, pause
from src.etl.news.valencia_events.jsonld import jsonld_offers as _jsonld_offers
from src.etl.news.valencia_events.normalise import normalise_record
from src.etl.news.valencia_events.sources import SOURCE_BY_KEY, SOURCES, Source, eventbrite, meetup, visitvalencia
from src.etl.news.valencia_events.stamps import STAMPS_FILE, Stamps, load_stamps, save_stamps, update_stamps
from src.etl.news.valencia_events.storage import write_text_atomic
from src.models.base import TimestampedModel

EVENTS_FILE = "valencia_events.json"
# How every source fared in the last run, for the tab to show.
SOURCE_STATUS_FILE = "sources_status.json"
# How long the events of a source that stopped answering are kept.
CARRY_OVER_DAYS = 7

# Fields a source may add to the original record shape; they are carried along untouched.
_OPTIONAL_FIELDS = ("start_time", "end_time", "address", "city", "tags", "start_datetime", "end_datetime")
# The fields of a raw record, as read back from a stored event.
_RAW_FIELDS = ("title", "url", "source", "category", "description", "start_date", "end_date", "date_text", "start_time", "end_time", "venue", "address", "city", "price_info", "is_free", "tags", "metadata")
# A category that says nothing: a specific one from another source wins over it.
_WEAK_CATEGORIES = ("", UNKNOWN_CATEGORY, "meetup", "eventbrite")


class ValenciaEvent(TimestampedModel):
    """Model for Valencia events.

    The first block of fields is the original one. The rest is filled by
    ``normalise_record``: ``start_at``/``end_at`` are ISO 8601 with their
    offset, ``start_local``/``end_local`` the readable Valencia form (T-178);
    ``price`` is a number, ``0`` when free and ``None`` when the source says
    nothing (never guessed); ``first_detected_at`` is the run that first saw
    the event and survives every later run.
    """

    title: str
    url: str = ""
    source: str = "visitvalencia.com"
    category: str = ""
    description: str = ""
    start_date: str = ""
    end_date: str = ""
    date_text: str = ""
    venue: str = ""
    price_info: str = ""
    is_free: bool | None = None
    metadata: dict[str, Any] = {}
    # when
    event_id: str = ""
    start_time: str = ""
    end_time: str = ""
    all_day: bool = True
    start_at: str = ""
    end_at: str = ""
    start_local: str = ""
    end_local: str = ""
    # where
    address: str = ""
    city: str = ""
    zone: str = ""
    # how much
    price: float | None = None
    price_max: float | None = None
    currency: str = ""
    # labels, and when the event was first detected
    tags: list[str] = []
    first_detected_at: str = ""
    first_detected_local: str = ""
    last_seen_at: str = ""


class ValenciaEventsETL(BaseETL[dict, ValenciaEvent]):
    """ETL for Valencia events from multiple sources."""

    def __init__(self) -> None:
        super().__init__(
            name="valencia_events",
            description="Extract Valencia events from multiple sources (visitvalencia.com, meetup.com, eventbrite, valencia.es, ...)",
            max_retries=3,
            retry_delay=5,
            # The generic engine merges records whose titles are 80 % alike, which would collapse the sessions of one show into a single event.
            # Events are merged by title AND start instead (_merge_events).
            enable_deduplication=False,
        )
        # Override output directory to write directly to main data directory
        self.output_dir = self.data_dir
        self._source_status: dict[str, str] = {}
        self._source_seen: dict[str, int] = {}
        self._nothing_answered = False
        self._carried_seen: dict[str, str] = {}
        self._run_now: datetime | None = None
        self._stamps: Stamps = {}
        self._fresh_ids: list[str] = []

    @property
    def source_status(self) -> dict[str, str]:
        """``ok``, ``empty``, ``failed`` or ``blocked`` per source key, as the last extract found it."""
        return dict(self._source_status)

    def get_current_and_next_month(self):
        """Returns the current and next month in YYYY-MM format.

        Returns:
            Tuple of (current_month, next_month) in YYYY-MM format
        """
        now = datetime.now()
        current_month = f"{now.year}-{now.month:02d}"

        # Calculate next month
        if now.month == 12:
            next_month = f"{now.year + 1}-01"
        else:
            next_month = f"{now.year}-{now.month + 1:02d}"

        return current_month, next_month

    def get_valencia_events(self, date: str) -> list[dict[str, Any]]:
        """Fetches events from the Valencia tourism website for a specific month.

        Args:
            date: Month in YYYY-MM format

        Returns:
            List of event dictionaries
        """
        return visitvalencia.fetch_month(date, self.logger)

    def get_meetup_events(self) -> list[dict]:
        """Fetch events from Meetup.com for Valencia."""
        return meetup.fetch_events(self.logger)

    def get_eventbrite_events(self) -> list[dict]:
        """Fetch events from Eventbrite for Valencia."""
        return eventbrite.fetch_events(self.logger)

    def _fetch_source(self, source: Source) -> tuple[list[dict], str]:
        """Ask one source; a failure is logged and leaves the other sources alone."""
        try:
            records = source.fetch(logger=self.logger)
        except SourceBlockedError as error:
            self.logger.error(f"{source.label}: {error}. The host is not asked again in this run.")
            return [], "blocked"
        except Exception as e:  # broad by design: per-source fetch wrapper (network + scraping)
            self.logger.error(f"Failed to fetch {source.label}: {e}")
            return [], "failed"
        if not records:
            # The legacy sources swallow the error of a refused host: the block list still knows it.
            if any(urlsplit(url).netloc in blocked_hosts() for url in source.urls):
                return [], "blocked"
            self.logger.warning(f"{source.label} answered but gave no event (the page changed?)")
            return [], "empty"
        return list(records), "ok"

    def extract(self) -> list[dict]:
        """Extract events from multiple sources for Valencia."""
        self.logger.info("Starting multi-source Valencia events extraction")
        if self._nothing_answered:
            # A retry of a run that already heard nothing from anybody asks nobody again.
            raise ETLError("No Valencia events source gave an event in this run (see the lines above).")

        all_events = []
        self._source_status = {}
        self._source_seen = {}

        for index, source in enumerate(SOURCES):
            if index:
                pause()
            records, status = self._fetch_source(source)
            self._source_status[source.key] = status
            self._source_seen[source.key] = len(records)
            all_events.extend(records)
            self.logger.info(f"{source.label}: {status}, {len(records)} events")

        if blocked_hosts():
            self.logger.warning(f"Answered 403/429 and not asked again: {', '.join(sorted(blocked_hosts()))}")
        self.logger.info(f"Total events collected from all sources: {len(all_events)}")
        if not any(status == "ok" for status in self._source_status.values()):
            # Every source failed, was refused or gave nothing. The stored events are kept as they
            # are, and the run is reported as the failure it is: a run that "completed" here would
            # count as a success while the file goes stale (T-192).
            self._nothing_answered = True
            silent = ", ".join(f"{source.label}: {self._source_status[source.key]}" for source in SOURCES)
            self.logger.error(f"No Valencia events source gave an event ({silent}). The stored events are kept.")
            raise ETLError(f"No Valencia events source gave an event ({silent}). The stored events are kept.")
        return all_events

    def process_valencia_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Process and transform Valencia events into a standardized format.

        Args:
            events: List of raw event dictionaries from the Valencia website

        Returns:
            List of processed event dictionaries
        """
        self.logger.info(f"Processing {len(events)} Valencia events")
        processed_events = []

        for event in events:
            try:
                # Dates: extractors may already carry ISO start/end dates (JSON-LD
                # or structured listing cards); otherwise parse them from the
                # Spanish/free-form date text. Everything ends up ISO (YYYY-MM-DD)
                # or empty — undated events stay undated by design.
                date_info = str(event.get("date_text", "") or "")
                start_date = _to_iso_date(event.get("start_date", ""))
                end_date = _to_iso_date(event.get("end_date", ""))
                if not start_date:
                    start_date, end_date = _parse_dates_from_text(date_info)

                # Venue/price: the JSON-LD extractors carry them when the
                # source actually exposes them (Place name, offers); anything
                # else stays honestly empty / unknown (is_free None).
                venue = str(event.get("venue") or "").strip()
                price_info = str(event.get("price_info") or "").strip()
                raw_is_free = event.get("is_free")
                is_free: bool | None = raw_is_free if isinstance(raw_is_free, bool) else None

                # Clean up titles (sometimes they contain the event type)
                title = event.get("title", "").strip()

                # Enhanced category and description extraction
                category = event.get("category", "").strip()
                # A description is kept only when the source wrote one. The former
                # fallback — a slice of the title, or the title itself — only
                # repeated the title under itself.
                description = event.get("description", "").strip()
                title = event.get("title", "").strip()

                # Expanded category keywords
                category_keywords = {
                    "exposición": "exposición",
                    "música": "música",
                    "concierto": "música",
                    "festival": "festival",
                    "gastronomía": "gastronomía",
                    "food": "gastronomía",
                    "espectáculo": "espectáculo",
                    "teatro": "espectáculo",
                    "deporte": "deporte",
                    "sports": "deporte",
                    "naturaleza": "naturaleza",
                    "outdoor": "naturaleza",
                    "fiestas": "fiestas",
                    "celebración": "fiestas",
                    "cultura": "cultura",
                    "arte": "arte",
                    "literatura": "literatura",
                    "educación": "educación",
                    "tecnología": "tecnología",
                    "tech": "tecnología",
                    "conferencia": "conferencia",
                    "taller": "taller",
                    "workshop": "taller",
                }

                # Try to extract category from title if not already set
                if not category:
                    lower_title = title.lower()
                    for keyword, cat in category_keywords.items():
                        if re.search(rf"\b{keyword}\b", lower_title):
                            category = cat
                            break

                # Try to extract category from description if still not found
                if not category and description:
                    lower_desc = description.lower()
                    for keyword, cat in category_keywords.items():
                        if re.search(rf"\b{keyword}\b", lower_desc):
                            category = cat
                            break

                # Metadata: scraper defaults plus whatever the extractor carried
                # (e.g. location from JSON-LD sources) — the dashboard .ics
                # exporter reads metadata.location / metadata.venue when present.
                metadata: dict[str, Any] = {
                    "api_source": "valencia_scraper",
                    "processed_at": datetime.now().isoformat(),
                }
                raw_metadata = event.get("metadata")
                if isinstance(raw_metadata, dict):
                    metadata.update({key: value for key, value in raw_metadata.items() if value})

                processed_event = {
                    "title": title,
                    "url": event.get("url", ""),
                    "source": event.get("source", "visitvalencia.com"),
                    "category": category,
                    "description": description,
                    "start_date": start_date,
                    "end_date": end_date,
                    "date_text": date_info,
                    "venue": venue,
                    "price_info": price_info,
                    "is_free": is_free,
                    "metadata": metadata,
                }
                # What the newer sources add (clock, address, tags...) passes through untouched.
                for field in _OPTIONAL_FIELDS:
                    if event.get(field):
                        processed_event[field] = event[field]
                processed_events.append(processed_event)
                self.logger.debug(f"Processed event: {processed_event['title']}")

            except (ValueError, TypeError, KeyError, AttributeError, OverflowError, OSError) as e:
                self.logger.error(f"Error processing event: {e!s}")
                continue

        self.logger.info(f"Successfully processed {len(processed_events)} events")
        return processed_events

    def remove_duplicates(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate events based on title, merging data to create more complete records.

        Args:
            events: List of event dictionaries

        Returns:
            List of unique event dictionaries with merged data
        """
        self.logger.info(f"Removing duplicates from {len(events)} events")

        # Group events by title
        event_groups: dict[str, list[dict[str, Any]]] = {}
        for event in events:
            title = event.get("title", "")
            if title:
                if title not in event_groups:
                    event_groups[title] = []
                event_groups[title].append(event)

        # Merge events with the same title to create more complete records
        unique_events = []
        for _title, group in event_groups.items():
            if not group:
                continue

            # Start with the first event as base
            merged_event = group[0].copy()

            # Merge with subsequent events to get the most complete data
            for event in group[1:]:
                # Prefer non-empty URL
                if not merged_event.get("url") and event.get("url"):
                    merged_event["url"] = event.get("url")

                # Prefer non-empty category
                if not merged_event.get("category") and event.get("category"):
                    merged_event["category"] = event.get("category")

                # Prefer non-empty description
                if not merged_event.get("description") and event.get("description"):
                    merged_event["description"] = event.get("description")

                # Prefer non-empty venue / price information
                if not merged_event.get("venue") and event.get("venue"):
                    merged_event["venue"] = event.get("venue")
                if not merged_event.get("price_info") and event.get("price_info"):
                    merged_event["price_info"] = event.get("price_info")
                if merged_event.get("is_free") is None and event.get("is_free") is not None:
                    merged_event["is_free"] = event.get("is_free")

                # Prefer more complete date information
                if len(event.get("date_text", "")) > len(merged_event.get("date_text", "")):
                    merged_event["date_text"] = event.get("date_text")
                    merged_event["start_date"] = event.get("start_date", "")
                    merged_event["end_date"] = event.get("end_date", "")

                # Prefer dated duplicates over undated ones
                if not merged_event.get("start_date") and event.get("start_date"):
                    merged_event["start_date"] = event.get("start_date")
                    merged_event["end_date"] = event.get("end_date", "")

            unique_events.append(merged_event)

        self.logger.info(f"Removed {len(events) - len(unique_events)} duplicate events")
        return unique_events

    def _carry_over(self, processed: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
        """Add the stored events of the sources that gave nothing in this run.

        An event is carried over when it has not ended, when the source last
        saw it less than :data:`CARRY_OVER_DAYS` ago and when no record of
        this run describes it. Its ``last_seen_at`` is kept: the days count
        from the last run that really saw it, not from the runs that repeat it.

        Args:
            processed: The records of this run, after ``process_valencia_events``.
            now: The moment of the run, aware.

        Returns:
            ``processed`` followed by the carried records, flagged ``carried_over``.
        """
        silent = {key for key, status in self._source_status.items() if status != "ok"}
        self._carried_seen = {}
        if not silent:
            return processed
        horizon = now - timedelta(days=CARRY_OVER_DAYS)
        fresh_dates: dict[str, list[str]] = {}
        for event in processed:
            fresh_dates.setdefault(_title_key(event), []).append(str(event.get("start_date") or ""))

        kept = []
        for stored in self._previous_events():
            if stored.get("source") not in silent:
                continue
            seen = parse_moment(stored.get("last_seen_at"))
            if seen is None or seen < horizon or _has_ended(stored, now):
                continue
            start_date = str(stored.get("start_date") or "")
            dates = fresh_dates.get(_title_key(stored), [])
            if not start_date or "" in dates or start_date in dates:
                continue  # a record of this run already describes it
            record = {field: stored[field] for field in _RAW_FIELDS if field in stored}
            record["metadata"] = {**(stored.get("metadata") or {}), "carried_over": True}
            kept.append(record)
            self._carried_seen[str(stored.get("event_id") or "")] = str(stored.get("last_seen_at") or "")
        if kept:
            self.logger.warning(f"Carried over {len(kept)} stored events of the sources that gave nothing: {', '.join(sorted(silent))}")
        return processed + kept

    def _previous_events(self) -> list[dict[str, Any]]:
        """The events of the file as it is stored, [] when it cannot be read."""
        try:
            stored = json.loads((self.output_dir / EVENTS_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        return [event for event in stored if isinstance(event, dict)] if isinstance(stored, list) else []

    def _merge_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """One record per event and per session: same title, same start day and same clock.

        Two sources that print the same event are merged into its most complete
        record. A title on two days, or twice on one day at two clocks, is two
        sessions and stays two records. A record without a date joins the
        first dated one of its title: it is the same event, listed by a source
        that prints no date.
        """
        by_day: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for event in events:
            title, start_date = _session_key(event)
            by_day.setdefault((title, start_date), []).append(event)

        groups: list[list[dict[str, Any]]] = []
        first_session: dict[str, tuple[str, list[dict[str, Any]]]] = {}
        for (title, start_date), records in by_day.items():
            if not start_date:
                continue
            sessions = _split_sessions(records)
            groups.extend(sessions)
            if title not in first_session or start_date < first_session[title][0]:
                first_session[title] = (start_date, sessions[0])
        for (title, start_date), records in by_day.items():
            if start_date:
                continue
            target = first_session.get(title)
            if target is not None:
                target[1].extend(records)
            else:
                groups.append(records)
        return [self._merge_group(group) for group in groups]

    def _merge_group(self, group: list[dict[str, Any]]) -> dict[str, Any]:
        """The most complete record of one event, completed from the others."""
        if len(group) == 1:
            return group[0]
        # A dated record leads: its dates are the ones the event keeps.
        ordered = sorted(group, key=lambda event: not event.get("start_date"))
        merged = dict(ordered[0])
        for event in ordered[1:]:
            for field in ("url", "description", "venue", "price_info", "start_time", "end_time", "address", "city", "start_datetime", "end_datetime"):
                if not merged.get(field) and event.get(field):
                    merged[field] = event[field]
            if merged.get("category") in _WEAK_CATEGORIES and event.get("category"):
                merged["category"] = event["category"]
            if merged.get("is_free") is None and event.get("is_free") is not None:
                merged["is_free"] = event["is_free"]
            if not merged.get("start_date") and event.get("start_date"):
                merged["start_date"], merged["end_date"], merged["date_text"] = event.get("start_date", ""), event.get("end_date", ""), event.get("date_text", "")
            elif not merged.get("end_date") and event.get("end_date"):
                merged["end_date"] = event["end_date"]
            if not merged.get("tags") and event.get("tags"):
                merged["tags"] = event["tags"]
            metadata = dict(merged.get("metadata") or {})
            for key, value in (event.get("metadata") or {}).items():
                if value and key not in metadata:
                    metadata[key] = value
            merged["metadata"] = metadata
        return merged

    def transform(self, data: list[dict]) -> list[ValenciaEvent]:
        """Transform raw events into structured models."""
        if not data:
            return []

        now = madrid_now()
        stamps = load_stamps(self.output_dir / STAMPS_FILE)

        # Process events
        processed_events = self.process_valencia_events(data)
        processed_events = self._carry_over(processed_events, now)

        # One record per event and per session
        unique_events = self._merge_events(processed_events)

        # Complete and convert to models
        models = []
        for event in unique_events:
            source = SOURCE_BY_KEY.get(str(event.get("source") or ""))
            try:
                fields = normalise_record(event, now=now, stamps=stamps, source_label=source.label if source else "")
                if event.get("metadata", {}).get("carried_over"):
                    fields["last_seen_at"] = self._carried_seen.get(fields["event_id"], fields["last_seen_at"])
                models.append(ValenciaEvent(**fields))
            except (ValueError, TypeError) as e:
                self.logger.error(f"Failed to create model for event: {e}")
                continue

        self._run_now = now
        self._stamps = stamps
        self._fresh_ids = [model.event_id for model in models if not model.metadata.get("carried_over")]
        return models

    def load(self, data: list[ValenciaEvent]) -> None:
        """Save events to JSON and CSV files."""
        if not data:
            self.logger.info("No data to load")
            return

        # Convert to dictionaries, in the order the tab shows them: by start
        # date, the ones without a date last.
        data_dicts = [event.model_dump() for event in data]
        data_dicts.sort(key=lambda event: (not event.get("start_date"), str(event.get("start_date"))))

        # Save JSON, atomically: the tab and the API read it while the ETL runs
        json_file = self.output_dir / EVENTS_FILE
        write_text_atomic(json_file, json.dumps(data_dicts, indent=2, ensure_ascii=False, default=str))
        self.logger.info(f"Saved {len(data_dicts)} events to {json_file}")

        # Remember when each event was first detected (the first detection is never moved)
        if self._run_now is not None:
            save_stamps(self.output_dir / STAMPS_FILE, update_stamps(self._stamps, self._fresh_ids, self._run_now), self._run_now)
            self._write_source_status(data_dicts)
            self._log_totals(data_dicts)

        # Save CSV
        try:
            import pandas as pd

            csv_file = self.output_dir / "valencia_events.csv"
            pd.DataFrame(data_dicts).to_csv(csv_file, index=False, encoding="utf-8")
            self.logger.info(f"Saved CSV to {csv_file}")
        except ImportError:
            self.logger.warning("Pandas not available, skipping CSV export")

    def _write_source_status(self, data_dicts: list[dict[str, Any]]) -> None:
        """Write how every source fared, with the events of the file that come from it."""
        in_file = Counter(str(event.get("source") or "") for event in data_dicts)
        sources = [
            {"key": source.key, "label": source.label, "status": self._source_status.get(source.key, ""), "read": self._source_seen.get(source.key, 0), "events": in_file.get(source.key, 0)}
            for source in SOURCES
        ]
        payload = {"updated_at": iso(self._run_now) if self._run_now else "", "events": len(data_dicts), "sources": sources}
        write_text_atomic(self.output_dir / SOURCE_STATUS_FILE, json.dumps(payload, indent=2, ensure_ascii=False))

    def _log_totals(self, data_dicts: list[dict[str, Any]]) -> None:
        """Log what the run produced: events per source, prices, and what starts today and tomorrow."""
        in_file = Counter(str(event.get("source") or "") for event in data_dicts)
        for source in SOURCES:
            self.logger.info(f"  {source.label}: {self._source_status.get(source.key, '?')} - {self._source_seen.get(source.key, 0)} read, {in_file.get(source.key, 0)} in the file")
        priced = [event for event in data_dicts if event.get("price") is not None]
        today = self._run_now.date() if self._run_now else date.today()

        def _starts(day: date) -> int:
            return sum(1 for event in data_dicts if str(event.get("start_date") or "") == day.isoformat())

        free = sum(1 for event in priced if event.get("price") == 0)
        self.logger.info(f"Saved {len(data_dicts)} events: {len(priced)} with a price ({free} free); starting today {today:%d/%m/%Y}: {_starts(today)}, tomorrow: {_starts(today + timedelta(days=1))}")


def _title_key(event: dict[str, Any]) -> str:
    """A title as one key: accent-free, lower-case, single spaces."""
    return fold(" ".join(str(event.get("title") or "").split()))


def _session_key(event: dict[str, Any]) -> tuple[str, str]:
    """The title and the start day of a record: what a session is grouped by first."""
    return (_title_key(event), str(event.get("start_date") or ""))


def _clock_of(event: dict[str, Any]) -> str:
    """The clock a record carries: ``start_time``, else the time of a full timestamp in ``date_text``."""
    stated = str(event.get("start_time") or "")
    if stated:
        return stated
    moment = parse_moment(event.get("date_text"))
    return moment.strftime("%H:%M") if moment else ""


def _split_sessions(records: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """The sessions of one title on one day: one per clock; a record without a clock joins the first."""
    timed: dict[str, list[dict[str, Any]]] = {}
    untimed: list[dict[str, Any]] = []
    for record in records:
        clock = _clock_of(record)
        if clock:
            timed.setdefault(clock, []).append(record)
        else:
            untimed.append(record)
    groups = list(timed.values())
    if not groups:
        return [untimed]
    groups[0].extend(untimed)
    return groups


def _has_ended(event: dict[str, Any], now: datetime) -> bool:
    """Whether a stored event is over at ``now``; an event without dates is never over."""
    end = parse_moment(event.get("end_at"))
    if end is not None:
        return end <= now
    start = parse_moment(event.get("start_at"))
    return start is not None and start < now


def main():
    """Main function to run Valencia events ETL."""
    etl = ValenciaEventsETL()
    try:
        metrics = etl.run()
        etl.logger.info(f"ETL completed successfully. Metrics: {metrics.model_dump()}")
    except Exception as e:  # broad by design: wrapper around BaseETL.run() pipeline
        etl.logger.error(f"ETL failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
