"""Cinema sessions ETL: what is on at the cinemas of València, read from several sources.

Composed like ``valencia_events_etl``: each source module reads its listing
pages on its own, and a source that fails is logged and left out while the
others still load. The output is one record per session in
``data/cinema/cinema_sessions_latest.json``: film, cinema, city, day, time,
version, format and the links the listing publishes. A price is stored only
when a listing prints one — none does today — and ``first_detected_at`` is
kept from run to run.
"""

import json
import logging
import os
from collections.abc import Callable
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.etl.base import BaseETL
from src.etl.cinema import babel, exhicine, filmaffinity, filmoteca
from src.etl.cinema.common import ListingResult, PageFetcher, drop_past_days, today
from src.models.cinema import CinemaSession, session_id, sessions_key_of

OUTPUT_FILE = "cinema_sessions_latest.json"
STATUS_FILE = "cinema_sources_latest.json"

# (source key, source site, reader): Cine Tívoli's chain first.
SOURCES: tuple[tuple[str, str, Callable[[Any, date], list[ListingResult]]], ...] = (
    ("exhicine", "exhicine.es", exhicine.fetch),
    ("babel", "cinesbabel.com", babel.fetch),
    ("filmoteca", "ivc.gva.es", filmoteca.fetch),
    ("filmaffinity", "filmaffinity.com", filmaffinity.fetch),
)


class CinemaSessionsETL(BaseETL[dict[str, Any], CinemaSession]):
    """ETL for the cinema sessions of València, from the chain's, the cinemas' and the aggregator's listings."""

    def __init__(self) -> None:
        """Prepare the pipeline: no retries, so each listing page is requested once per run."""
        super().__init__(name="cinema", description="Cinema sessions of València (EXHICINE, Babel, Filmoteca, FilmAffinity)", max_retries=0, enable_checkpointing=False, enable_deduplication=False)
        self.output_file = self.data_dir / OUTPUT_FILE
        self.status_file = self.data_dir / STATUS_FILE
        self.listing_results: list[tuple[str, str, ListingResult]] = []

    def extract(self) -> list[dict[str, Any]]:
        """Read every listing page, once, and keep the sessions from today on.

        Returns:
            Session dictionaries from every page that could be read.

        Raises:
            RuntimeError: When not one listing page could be read, or when pages were read but not one session
                came out of them: a run that writes nothing must be seen as a failure, not as an empty day.
        """
        fetcher = PageFetcher()
        reference = today()
        self.listing_results = []
        records: list[dict[str, Any]] = []
        for source, host, read in SOURCES:
            for result in read(fetcher, reference):
                self.listing_results.append((source, host, result))
                records.extend(result.sessions)

        read_pages = [entry for entry in self.listing_results if entry[2].ok]
        if not read_pages:
            failures = "; ".join(f"{result.listing}: {result.error}" for _, _, result in self.listing_results)
            raise RuntimeError(f"none of the {len(self.listing_results)} cinema listing pages could be read ({failures})")
        sessions = drop_past_days(records, reference)
        if not sessions:
            raise RuntimeError(f"{len(read_pages)} cinema listing pages read and not one session parsed: the listings changed")
        self.logger.info("Cinema: %d listing pages read out of %d, %d sessions of today or later (%d requests)", len(read_pages), len(self.listing_results), len(sessions), len(fetcher.urls_requested))
        return sessions

    def transform(self, data: list[dict[str, Any]]) -> list[CinemaSession]:
        """Drop the repeated sessions, keep ``first_detected_at`` of the known ones and validate the rest.

        Args:
            data: Session dictionaries, already limited to today and the days ahead.

        Returns:
            Valid sessions in the order the sources were read (Cine Tívoli first), then by day, time and title:
            the tab lists the cinemas in this order whatever the first day each of them has something on.
        """
        previous = self._previous_sessions()
        now = datetime.now(timezone.utc)
        rank = {result.cinema: index for index, (_, _, result) in enumerate(self.listing_results)}

        sessions: list[CinemaSession] = []
        seen: set[str] = set()
        for record in data:
            key = session_id(sessions_key_of(record))
            if key in seen:
                self.metrics.duplicates_removed += 1
                continue
            seen.add(key)
            record["id"] = key
            known = previous.get(key)
            record["first_detected_at"] = (known.get("first_detected_at") or now) if known else now
            if known and known.get("created_at"):
                record["created_at"] = known["created_at"]
            try:
                sessions.append(CinemaSession(**record))
            except ValidationError as exc:
                self.logger.warning("Cinema: dropped a session that does not validate (%s): %s", record.get("title"), exc.errors()[0]["msg"] if exc.errors() else exc)
                self.metrics.records_failed += 1

        sessions.sort(key=lambda session: (rank.get(session.cinema, len(rank)), session.date, session.time, session.title.casefold()))
        return sessions

    def load(self, data: list[CinemaSession]) -> None:
        """Write the sessions and the per-listing status, each file replaced whole once it is complete."""
        records = [session.model_dump(mode="json") for session in data]
        _write_json(self.output_file, records)
        status = {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "reference_day": today().isoformat(),
            "sessions": len(records),
            "listings": [
                {"source": source, "host": host, "cinema": result.cinema or result.listing.key, "city": result.city, "url": result.listing.url, "sessions": len(result.sessions), "error": result.error}
                for source, host, result in self.listing_results
            ],
        }
        _write_json(self.status_file, status)
        self.logger.info("Cinema: saved %d sessions of %d cinemas to %s", len(records), len({record["cinema"] for record in records}), self.output_file)

    def _previous_sessions(self) -> dict[str, dict[str, Any]]:
        """The sessions of the previous run by id, or nothing when there is no previous output."""
        if not self.output_file.exists():
            return {}
        try:
            previous = json.loads(self.output_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            self.logger.warning("Cinema: previous output could not be read, every session is detected anew: %s", exc)
            return {}
        if not isinstance(previous, list):
            return {}
        return {str(record["id"]): record for record in previous if isinstance(record, dict) and record.get("id")}


def _write_json(path: Path, payload: Any) -> None:
    """Write ``payload`` as JSON, replacing ``path`` only once the file is complete."""
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_metrics = CinemaSessionsETL().run()
    if any(error["type"] == "CircuitBreakerOpen" for error in run_metrics.errors_detail):
        raise SystemExit(1)
