"""Trendshift ETL — the trending repositories of trendshift.io, one record per repository.

What the source gives (checked on 2026-11-28 with ``curl`` and ``requests``: no
key, no login, no browser):

- ``https://trendshift.io/`` is a Next.js page whose HTML embeds the ranking
  as a React Server Components payload: ``self.__next_f.push([1, "…"])`` strings,
  one of which carries ``"initialData"``, an object per repository. The same
  page embeds a schema.org ``ItemList`` too (name, description, language and
  created date, but no stars).
- One page per period, the top 25 of all languages: daily ``/``, weekly
  ``/weekly``, monthly ``/monthly`` and yearly ``/yearly``.
- Per repository: full name, description, primary language, stars, forks, stars
  and forks gained in the period, created date, rank, score, tags and the
  platforms it was mentioned on.

What it does not give:

- A publication date: a ranking has none. The record carries the date of the
  snapshot (``snapshot_at``), the first day of the period as the source dates
  it (``period_starts_at``) and, per repository, ``first_seen`` — the
  first run that saw it on a trendshift list, kept from the previous file.
- Language filters and past dates: ``?language=`` and ``?date=`` are applied in
  the browser, and the server answers the same current all-languages page.
- More than 25 repositories per period, or a JSON endpoint a plain client can
  call. The repository pages (``/repositories/<id>``) answer a Cloudflare
  challenge.

The site sits behind Cloudflare. A blocked, empty or changed answer leaves the
last good file in place: the run logs a warning and exits 0, and the freshness
watcher reports the file as stale after a day without a rewrite.

Only the daily ranking is fetched (``FETCH_PERIODS``); the parser reads the
four periods. Feeds the "Trendshift" subtab of Knowledge Garden (T-134).

Usage:
    uv run python -m src.etl.github.trendshift_etl

Output:
    data/github/trendshift_<period>_latest.json (+ a timestamped snapshot)
"""

import json
import logging
import os
import re
import time
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from src.constants.etl import SCRAPER_BRANDED_USER_AGENT
from src.models.github import TrendshiftPeriod, TrendshiftRepoModel
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.retry import with_retry

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TRENDSHIFT_BASE_URL = "https://trendshift.io"
GITHUB_BASE_URL = "https://github.com"

# Path of each period's ranking on the site.
TRENDSHIFT_PERIOD_PATHS: dict[TrendshiftPeriod, str] = {"daily": "/", "weekly": "/weekly", "monthly": "/monthly", "yearly": "/yearly"}

# Periods fetched in production: one request per period and per cycle.
FETCH_PERIODS: tuple[TrendshiftPeriod, ...] = ("daily",)

REQUEST_TIMEOUT_SECONDS = 30
# Between two period pages, so a cycle with several periods stays polite.
REQUEST_DELAY_SECONDS = 2.0

# Start of the inline scripts that carry the React Server Components payload.
_FLIGHT_PUSH = "self.__next_f.push([1,"
# The prop the list component receives: the ranking, one object per repository.
_INITIAL_DATA = '"initialData":'

# Cloudflare's interstitial. A plain client never passes it, so such an answer
# is not retried.
_CHALLENGE_HEADER = "cf-mitigated"
_CHALLENGE_VALUE = "challenge"
_CHALLENGE_TITLE = "<title>Just a moment"

# "owner/repo": both parts filled in, no whitespace. The GitHub URL is built from it.
_FULL_NAME = re.compile(r"^[^\s/]+/[^\s/]+$")

# Fields every record gets from Watchtower itself; the others are counted after each run.
_UNCOUNTED_FIELDS = frozenset({"source", "title", "full_name", "url", "trend_period", "snapshot_at", "first_seen", "platform", "content_type"})


def flight_chunks(html: str) -> list[str]:
    """Decode the page's ``self.__next_f.push([1, "…"])`` strings, in order.

    Each one is a JSON string literal, so the payload reads with the JSON
    decoder. A push that does not decode is skipped.
    """
    decoder = json.JSONDecoder()
    chunks: list[str] = []
    position = 0
    while (start := html.find(_FLIGHT_PUSH, position)) != -1:
        start += len(_FLIGHT_PUSH)
        while start < len(html) and html[start] in " \t\r\n":
            start += 1
        try:
            chunk, position = decoder.raw_decode(html, start)
        except ValueError:
            position = start
            continue
        if isinstance(chunk, str):
            chunks.append(chunk)
    return chunks


def extract_initial_data(chunks: list[str]) -> list[dict[str, Any]]:
    """The ranking the page hands its list component, as the source's objects.

    The payload is not one JSON document: ``"initialData"`` is a prop among
    others, so its value is decoded where it is found. The first list whose
    objects name a repository wins; non-objects are left out.
    """
    decoder = json.JSONDecoder()
    for chunk in chunks:
        position = 0
        while (start := chunk.find(_INITIAL_DATA, position)) != -1:
            start += len(_INITIAL_DATA)
            try:
                value, position = decoder.raw_decode(chunk, start)
            except ValueError:
                break
            if not isinstance(value, list):
                continue
            entries = [entry for entry in value if isinstance(entry, dict)]
            if any(isinstance(entry.get("full_name"), str) for entry in entries):
                return entries
    return []


def parse_trendshift_page(html: str) -> list[dict[str, Any]]:
    """The entries of one ranking page, in the page's (rank) order, one per repository.

    An entry without a usable ``full_name`` is left out and counted.
    """
    entries: dict[str, dict[str, Any]] = {}
    dropped = 0
    for entry in extract_initial_data(flight_chunks(html)):
        full_name = entry.get("full_name")
        if not isinstance(full_name, str) or not _FULL_NAME.fullmatch(full_name):
            dropped += 1
            continue
        entries.setdefault(full_name, entry)
    if dropped:
        logger.warning(f"{dropped} trendshift entries without a usable full name were left out")
    logger.info(f"Parsed {len(entries)} trendshift repositories")
    return list(entries.values())


def _int_or_none(value: Any) -> int | None:
    """An integer as the source counts; anything else is an unknown value."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _text(value: Any) -> str:
    """A non-empty string from the source; anything else is an empty field."""
    return value.strip() if isinstance(value, str) else ""


def _strings(items: Iterable[Any]) -> list[str]:
    """The non-empty strings among the values, in order, without repeats."""
    values: list[str] = []
    for item in items:
        text = _text(item)
        if text and text not in values:
            values.append(text)
    return values


def _display_names(items: Any) -> list[str]:
    """``display_name`` of a list of tag objects; anything else is an empty list."""
    return _strings(tag.get("display_name") for tag in items if isinstance(tag, dict)) if isinstance(items, list) else []


def _datetime_or_none(value: Any) -> datetime | None:
    """An ISO 8601 timestamp of the source, parsed; ``None`` when it is missing or is not one.

    A naive value is taken as UTC.
    """
    raw = _text(value)
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def period_starts_at(entry: dict[str, Any], period: TrendshiftPeriod) -> datetime | None:
    """First day of the period as the source dates the entry; ``None`` when it gives none.

    Daily and weekly entries carry a timestamp (``date``, ``week_start``);
    monthly and yearly ones a year and a month, or a year alone.
    """
    if period == "daily":
        return _datetime_or_none(entry.get("date"))
    if period == "weekly":
        return _datetime_or_none(entry.get("week_start"))
    year, month = _int_or_none(entry.get("year")), _int_or_none(entry.get("month"))
    if year is None or (period == "monthly" and month is None):
        return None
    try:
        return datetime(year, month or 1, 1, tzinfo=timezone.utc)
    except ValueError:
        return None


def build_records(entries: list[dict[str, Any]], period: TrendshiftPeriod, *, snapshot_at: datetime, first_seen: dict[str, datetime] | None = None) -> list[dict[str, Any]]:
    """Turn the page's entries into one stored record per repository, in page order.

    Args:
        entries: Entries as ``parse_trendshift_page`` returns them.
        period: The ranking they come from.
        snapshot_at: When the page was read; a naive value is taken as UTC.
        first_seen: ``full name -> first_seen`` of the previous file.
            A repository missing from it is detected at ``snapshot_at``.

    Returns:
        The records as the model serializes them. What the source leaves out
        stays empty: a blank text, ``None`` or an empty list.
    """
    snapshot_at = (snapshot_at if snapshot_at.tzinfo else snapshot_at.replace(tzinfo=timezone.utc)).replace(microsecond=0)
    stamps = first_seen or {}
    records: list[dict[str, Any]] = []
    for entry in entries:
        full_name = entry["full_name"]
        repository_id = _int_or_none(entry.get("repository_id"))
        records.append(
            TrendshiftRepoModel(
                title=full_name,
                full_name=full_name,
                url=f"{GITHUB_BASE_URL}/{full_name}",
                description=_text(entry.get("repository_description")),
                language=_text(entry.get("repository_language")) or _text(entry.get("language")),
                stars=_int_or_none(entry.get("repository_stars")),
                forks=_int_or_none(entry.get("repository_forks")),
                stars_gained=_int_or_none(entry.get("repository_stars_gained")),
                forks_gained=_int_or_none(entry.get("repository_forks_gained")),
                rank=_int_or_none(entry.get("rank")),
                score=_int_or_none(entry.get("score")),
                trend_period=period,
                period_starts_at=period_starts_at(entry, period),
                tags=_display_names(entry.get("tags")),
                social_mention_platforms=_strings(entry.get("social_mention_platforms") or []),
                repo_created_at=_datetime_or_none(entry.get("repository_created_at")),
                trendshift_id=repository_id,
                trendshift_url=f"{TRENDSHIFT_BASE_URL}/repositories/{repository_id}" if repository_id else "",
                snapshot_at=snapshot_at,
                first_seen=stamps.get(full_name) or snapshot_at,
            ).model_dump(mode="json")
        )
    return records


def empty_field_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    """How many records leave each source field empty (missing, blank or no list)."""
    fields = [name for name in TrendshiftRepoModel.model_fields if name not in _UNCOUNTED_FIELDS]
    return {field: sum(1 for record in records if record.get(field) is None or record.get(field) == "" or record.get(field) == []) for field in fields}


@with_retry
def _get(url: str) -> requests.Response:
    """One GET. Network and server errors are retried with a backoff; a refused request is returned as it is."""
    response = requests.get(url, headers={"User-Agent": SCRAPER_BRANDED_USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS)
    if response.status_code >= 500:
        response.raise_for_status()
    return response


def blocked_reason(response: requests.Response) -> str | None:
    """Why an answer is not the page asked for, or ``None`` when it may be."""
    status = response.status_code
    head = response.content[:4000].decode("utf-8", errors="replace")
    if response.headers.get(_CHALLENGE_HEADER, "").lower() == _CHALLENGE_VALUE or _CHALLENGE_TITLE in head:
        return f"HTTP {status}, Cloudflare challenge"
    if status == 429:
        return "HTTP 429, rate limited"
    if status >= 400:
        return f"HTTP {status}"
    return None


def fetch_trendshift_period(period: TrendshiftPeriod) -> list[dict[str, Any]] | None:
    """Entries of one period's ranking, or ``None`` when the source gave nothing usable.

    A refused or unreadable answer is logged and left to the caller, who keeps
    the last good file.
    """
    url = f"{TRENDSHIFT_BASE_URL}{TRENDSHIFT_PERIOD_PATHS[period]}"
    logger.info(f"Fetching the trendshift.io {period} ranking from {url}")
    try:
        response = _get(url)
    except requests.RequestException as exc:
        logger.warning(f"Could not fetch {url}: {exc}")
        return None
    reason = blocked_reason(response)
    if reason:
        logger.warning(f"trendshift.io did not answer the {period} ranking ({reason}); not retrying this run")
        return None
    entries = parse_trendshift_page(response.content.decode("utf-8", errors="replace"))
    if not entries:
        logger.warning(f"The trendshift.io {period} ranking at {url} carries no repository list: the page changed or is blocked")
    return entries


def latest_path(output_dir: str | Path, period: TrendshiftPeriod) -> Path:
    """The file the dashboard reads for one period."""
    return Path(output_dir) / f"trendshift_{period}_latest.json"


def load_first_seen(paths: list[Path]) -> dict[str, datetime]:
    """``full name -> first_seen`` read from previous files.

    A missing file contributes nothing. A broken one contributes nothing
    either, with a warning: its repositories are then dated as detected now.
    """
    stamps: dict[str, datetime] = {}
    for path in paths:
        if not path.exists():
            continue
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.warning(f"Could not read {path.name} to keep the first-seen dates ({exc})")
            continue
        if not isinstance(previous, list):
            logger.warning(f"{path.name} is not a list of records: its first-seen dates are not kept")
            continue
        for record in previous:
            if not isinstance(record, dict):
                continue
            full_name, stamp = record.get("full_name"), _datetime_or_none(record.get("first_seen"))
            if isinstance(full_name, str) and full_name and stamp:
                stamps.setdefault(full_name, stamp)
    return stamps


def _write_json(path: Path, data: Any) -> None:
    """Write JSON so a reader never sees half a file: a sibling temporary file, then replaced."""
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, path)


def save_trendshift(records: list[dict[str, Any]], period: TrendshiftPeriod, output_dir: str | Path | None = None, now: datetime | None = None) -> Path:
    """Persist one period under ``data/github/``: a timestamped snapshot and the ``_latest`` copy.

    Args:
        records: Records as ``build_records`` returns them.
        period: The ranking they come from.
        output_dir: Where to write; the project's ``data/github/`` by default.
        now: Time of the snapshot's file name; now by default.

    Returns:
        The path of the ``_latest`` file.
    """
    folder = Path(output_dir) if output_dir is not None else Path(get_project_root()) / "data" / "github"
    ensure_directories([str(folder)])
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    latest = latest_path(folder, period)
    for path in (folder / f"trendshift_{period}_{timestamp}.json", latest):
        _write_json(path, records)
    logger.info(f"Saved {len(records)} trendshift {period} repositories to {latest}")
    return latest


def run(now: datetime | None = None, periods: tuple[TrendshiftPeriod, ...] = FETCH_PERIODS, output_dir: str | Path | None = None) -> dict[str, int]:
    """Fetch every period and save it.

    Args:
        now: Time of the snapshot, for the records' dates; now (UTC) by default.
        periods: The rankings to fetch.
        output_dir: Where to write; the project's ``data/github/`` by default.

    Returns:
        Repositories written per period. A 0 means the source gave nothing
        usable and the previous file was left in place.
    """
    folder = Path(output_dir) if output_dir is not None else Path(get_project_root()) / "data" / "github"
    snapshot_at = now or datetime.now(timezone.utc)
    written: dict[str, int] = {}
    for index, period in enumerate(periods):
        if index:
            time.sleep(REQUEST_DELAY_SECONDS)
        latest = latest_path(folder, period)
        entries = fetch_trendshift_period(period)
        if not entries:
            logger.warning(f"No usable {period} ranking from trendshift.io: {latest.name} is left as it was")
            written[period] = 0
            continue
        records = build_records(entries, period, snapshot_at=snapshot_at, first_seen=load_first_seen([latest_path(folder, name) for name in periods]))
        save_trendshift(records, period, folder, now=snapshot_at)
        written[period] = len(records)
        empty = empty_field_counts(records)
        logger.info(f"trendshift.io {period}: {len(records)} repositories. Filled per field: " + ", ".join(f"{field} {len(records) - count}/{len(records)}" for field, count in empty.items()))
    return written


def main() -> None:
    """Run the Trendshift ETL."""
    logger.info("Starting Trendshift ETL")
    try:
        run()
    except Exception as exc:  # broad by design: whole-pipeline wrapper (network fetch + parse + save)
        logger.error(f"Trendshift ETL failed: {exc}")
        raise


if __name__ == "__main__":
    main()
