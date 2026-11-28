"""Reading the dates and times the sources print, as Valencia local time.

Every source writes dates its own way: Spanish ``DD/MM/YYYY`` text, epoch
milliseconds, ``SA 28.11.26``, ``Del 21 de octubre al 16 de diciembre de 2026``,
``25 ene. 2026 - 08 dic. 2026``, or a schema.org timestamp in UTC. Everything is
turned into an aware datetime in ``Europe/Madrid``: that is the zone the events
happen in, and a date is the calendar day there, never the day of the digits.

Two rules from past tasks are the law here and are enforced in code:

- T-178: what is shown is a readable local date, never a raw ISO string.
- T-193: a date is never invented. A day and a month without a year are only
  resolved when the source itself supplies the year (another field, or the order
  of an ascending list); otherwise the record stays undated.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")

WEEKDAYS_SHORT = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")

_ISO_DATE_RE = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
_ES_DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
_CLOCK_RE = re.compile(r"\b(\d{1,2}):(\d{2})\b")

# Spanish, Valencian and English month names, told apart by their first letters.
_MONTH_PREFIXES = {
    "jan": 1,
    "ene": 1,
    "gen": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "apr": 4,
    "may": 5,
    "mai": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "aug": 8,
    "sep": 9,
    "set": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
    "dec": 12,
}

# "28 de noviembre de 2026", "29 nov 2026", "01 dic. 2026", "5 d'abril", "27 Nov".
# The letters must spell a real month: "10 años" or "Ciclo 12 mar" are not dates.
_WRITTEN_RE = re.compile(r"(?<![\d])(\d{1,2})\s*(?:de\s+|d[’']\s*)?([a-zà-ÿ]{3,10})\.?(?:\s*(?:de|,)\s*|\s+)?(\d{4})?(?!\d)", re.IGNORECASE)

# Several days that share one month: "Del 28 al 29 noviembre de 2026", "Del 11 al 12 de
# diciembre de 2026", "5/6/7 febrero 2027". Read before the single-date pattern, which
# would only see the last day.
_SHARED_MONTH_RE = re.compile(
    r"(?<![\d])(?P<days>\d{1,2}(?:(?:\s+(?:al|a|y|e|i)\s+|\s*[—–\-/,]\s*)\d{1,2})*)\s*(?:de\s+|d[’']\s*)?(?P<month>[a-zà-ÿ]{3,10})\.?(?:\s*(?:de|,)\s*|\s+)?(?P<year>\d{4})?(?!\d)", re.IGNORECASE
)
_DAYS_RE = re.compile(r"\d{1,2}")

# Numeric dates: ISO, Spanish DD/MM/YYYY and the dotted DD.MM.YY of Les Arts.
_NUMERIC_RE = re.compile(r"(?<!\d)(?:(\d{4})-(\d{1,2})-(\d{1,2})|(\d{1,2})/(\d{1,2})/(\d{4})|(\d{1,2})\.(\d{1,2})\.(\d{4}|\d{2}))(?!\d)")


# ---------------------------------------------------------------------------
# Legacy date helpers (moved unchanged from valencia_events_etl.py)
# ---------------------------------------------------------------------------


def _madrid_calendar_date(raw: str) -> str:
    """Read an ISO timestamp that carries a zone as its calendar date in Valencia.

    Meetup gives its start times in UTC: an evening there can already be the
    next day in Spain, and the event belongs to that day.

    Args:
        raw: Raw timestamp; a zone-less or unparsable value is not converted.

    Returns:
        YYYY-MM-DD, or "" when the value carries no zone.
    """
    if "T" not in raw:
        return ""
    # A zone name in brackets ("+02:00[Europe/Madrid]") adds nothing to the offset before it.
    try:
        moment = datetime.fromisoformat(raw.split("[")[0].replace("Z", "+00:00"))
    except ValueError:
        return ""
    if moment.tzinfo is None:
        return ""
    return moment.astimezone(MADRID).strftime("%Y-%m-%d")


def to_iso_date(raw: Any) -> str:
    """Normalise a raw date value to an ISO calendar date (YYYY-MM-DD).

    Accepts Spanish DD/MM/YYYY, ISO YYYY-MM-DD and full ISO timestamps. A
    timestamp that carries a zone (``+02:00``, ``Z``) is first changed to
    Valencia local time, so the date is the one the event has there; a
    zone-less one is read as it comes.

    Args:
        raw: Raw date value; non-strings are coerced, falsy values yield "".

    Returns:
        YYYY-MM-DD string, or "" when no plausible date can be extracted.
    """
    text = str(raw or "").strip()
    if not text:
        return ""
    local_date = _madrid_calendar_date(text)
    if local_date:
        return local_date
    match = _ISO_DATE_RE.search(text)
    if match:
        year, month, day = (int(group) for group in match.groups())
    else:
        match = _ES_DATE_RE.search(text)
        if not match:
            return ""
        day, month, year = (int(group) for group in match.groups())
    try:
        return datetime(year, month, day).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def parse_dates_from_text(text: Any) -> tuple[str, str]:
    """Extract a (start, end) ISO date pair from free-form date text.

    Handles "Del DD/MM/YYYY al DD/MM/YYYY", "DD/MM/YYYY - DD/MM/YYYY",
    "Fecha: ..." prefixes and bare ISO/Spanish date tokens, in any
    combination the sources print them.

    Args:
        text: Raw date text as shown on the listing.

    Returns:
        Tuple of (start_date, end_date). end_date is "" for single-day
        events; both are "" when the text carries no date at all.
    """
    value = str(text or "").strip()
    if not value:
        return "", ""
    tokens: list[str] = []
    for token in re.findall(r"\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{1,2}-\d{1,2}", value):
        iso = to_iso_date(token)
        if iso:
            tokens.append(iso)
    if not tokens:
        return "", ""
    # Deduplicate preserving order: a repeated identical date is a one-day
    # event, not a range.
    unique = list(dict.fromkeys(tokens))
    return unique[0], unique[1] if len(unique) > 1 else ""


# ---------------------------------------------------------------------------
# Aware moments
# ---------------------------------------------------------------------------


def parse_moment(raw: Any) -> datetime | None:
    """Parse an ISO 8601 timestamp that carries a zone, as an aware datetime in Madrid time.

    Args:
        raw: Timestamp string (``Z``, ``+02:00`` and a bracketed zone name are accepted).

    Returns:
        The moment in ``Europe/Madrid``, or None when the value is empty,
        unparsable or carries no zone.
    """
    text = str(raw or "").strip().split("[")[0]
    if not text:
        return None
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        return None
    return moment.astimezone(MADRID)


def parse_local_moment(raw: Any) -> datetime | None:
    """A full ISO timestamp that carries no zone, read as Valencia time.

    The tab always read such a timestamp (older files carry it) as the local
    hour: every event of these sources takes place in or around València.

    Args:
        raw: Timestamp string.

    Returns:
        The moment in ``Europe/Madrid``, or None unless the text is a full
        ISO timestamp (``2026-11-27T23:30:00``).
    """
    text = str(raw or "").strip().split("[")[0]
    if "T" not in text:
        return None
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment.astimezone(MADRID) if moment.tzinfo else moment.replace(tzinfo=MADRID)


def date_from_iso(raw: Any) -> date | None:
    """Read ``YYYY-MM-DD`` (or a value ``to_iso_date`` accepts) as a date; None when absent or impossible."""
    iso = to_iso_date(raw)
    if not iso:
        return None
    try:
        return date.fromisoformat(iso)
    except ValueError:
        return None


def local_date_of(raw: Any) -> date | None:
    """Calendar day in Valencia of a timestamp that carries a zone; None otherwise."""
    moment = parse_moment(raw)
    return moment.date() if moment else None


def parse_clock(raw: Any) -> time | None:
    """Read ``19:30``, ``19:30 h`` or ``11:30 horas`` as a time; None when the text has no clock."""
    match = _CLOCK_RE.search(str(raw or ""))
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    return time(hour, minute) if hour < 24 and minute < 60 else None


def iso(moment: datetime) -> str:
    """Aware datetime as ``2026-11-28T19:30:00+01:00``: ISO 8601 with its offset, to the second."""
    return moment.isoformat(timespec="seconds")


def format_local(moment: datetime, *, with_time: bool) -> str:
    """Readable Valencia form: ``sáb 28/11/2026`` or ``sáb 28/11/2026 · 19:30``."""
    text = f"{WEEKDAYS_SHORT[moment.weekday()]} {moment:%d/%m/%Y}"
    return f"{text} · {moment:%H:%M}" if with_time else text


@dataclass(frozen=True)
class Moments:
    """When an event happens, as aware datetimes in ``Europe/Madrid``.

    ``end`` is None when the source gives no end. For an all-day event ``end`` is
    the midnight after its last day (exclusive), the iCalendar convention; the
    inclusive last day is ``end_date``.
    """

    start: datetime | None
    end: datetime | None
    all_day: bool


def _midnight(day: date) -> datetime:
    return datetime.combine(day, time(0, 0), tzinfo=MADRID)


def build_moments(start_date: str = "", end_date: str = "", *, start_time: str = "", end_time: str = "", zoned: tuple[datetime | None, datetime | None] | None = None) -> Moments:
    """Turn the dates and clock times a source gives into aware moments in Valencia time.

    Args:
        start_date: Inclusive first day, ``YYYY-MM-DD``.
        end_date: Inclusive last day, ``YYYY-MM-DD``; empty for a single day.
        start_time: Clock text such as ``19:30 h``; empty for an all-day event.
        end_time: Clock text for the end; empty when the source gives none.
        zoned: A ``(start, end)`` pair of aware datetimes, for sources that give
            full timestamps (Meetup); the dates and clocks are then ignored.

    Returns:
        The moments; ``start`` is None when there is no usable start date. An
        event with a start time and no end time has ``end`` None: the end is not
        guessed. An all-day event ends at the midnight after its last day.
    """
    if zoned is not None and zoned[0] is not None:
        return Moments(zoned[0], zoned[1], all_day=False)
    day = date_from_iso(start_date)
    if day is None:
        return Moments(None, None, True)
    last = date_from_iso(end_date) or day
    if last < day:
        last = day
    clock = parse_clock(start_time)
    if clock is None:
        return Moments(_midnight(day), _midnight(last + timedelta(days=1)), True)
    start = datetime.combine(day, clock, tzinfo=MADRID)
    end_clock = parse_clock(end_time)
    if end_clock is not None:
        end: datetime | None = datetime.combine(last, end_clock, tzinfo=MADRID)
    elif last > day:
        end = _midnight(last + timedelta(days=1))
    else:
        end = None
    return Moments(start, end, False)


# ---------------------------------------------------------------------------
# Written dates: "28 de noviembre de 2026", "25 ene. 2026 - 08 dic. 2026"
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DateToken:
    """One day and month read from a text, with the year when the text has one."""

    month: int
    day: int
    year: int | None


def month_number(token: str | None) -> int | None:
    """Month number for a Spanish, Valencian or English month name or abbreviation; None for any other word."""
    prefix = (token or "").strip().lower()[:3]
    return _MONTH_PREFIXES.get(prefix) if prefix.isalpha() else None


def _written_tokens(text: str) -> list[tuple[int, DateToken]]:
    tokens: list[tuple[int, DateToken]] = []
    covered: list[tuple[int, int]] = []
    for match in _SHARED_MONTH_RE.finditer(text):
        month = month_number(match.group("month"))
        if month is None:
            continue
        year = int(match.group("year")) if match.group("year") else None
        covered.append(match.span())
        # Every day of the run takes the position of the run, so they keep their printed order.
        tokens.extend((match.start(), DateToken(month, int(day), year)) for day in _DAYS_RE.findall(match.group("days")))
    for match in _WRITTEN_RE.finditer(text):
        if any(start <= match.start() < end for start, end in covered):
            continue  # already read as part of a run of days
        month = month_number(match.group(2))
        if month is not None:
            tokens.append((match.start(), DateToken(month, int(match.group(1)), int(match.group(3)) if match.group(3) else None)))
    return tokens


def _numeric_tokens(text: str) -> list[tuple[int, DateToken]]:
    tokens: list[tuple[int, DateToken]] = []
    for match in _NUMERIC_RE.finditer(text):
        iso_y, iso_m, iso_d, es_d, es_m, es_y, dot_d, dot_m, dot_y = match.groups()
        if iso_y:
            tokens.append((match.start(), DateToken(int(iso_m), int(iso_d), int(iso_y))))
        elif es_y:
            tokens.append((match.start(), DateToken(int(es_m), int(es_d), int(es_y))))
        elif dot_y:
            year = int(dot_y) if len(dot_y) == 4 else 2000 + int(dot_y)
            tokens.append((match.start(), DateToken(int(dot_m), int(dot_d), year)))
    return tokens


def date_tokens(text: Any) -> list[DateToken]:
    """Every date in a text, in the order it prints them."""
    found = _written_tokens(str(text or "")) + _numeric_tokens(str(text or ""))
    return [token for _position, token in sorted(found, key=lambda entry: entry[0])]


def resolve_years(tokens: Iterable[DateToken], default_year: int | None = None) -> list[date | None]:
    """Give a year to every token, from the years the text has and the order it prints them.

    A token without a year takes the year of the nearest dated token: the one
    after it when it comes first, the one before it otherwise. A later token
    whose month is earlier than its predecessor's rolls over to the next year
    (``Del 26 Dic al 4 Ene``), and an earlier one whose month is later takes the
    previous year (``Del 21 de octubre al 16 de diciembre de 2026``).

    Args:
        tokens: Dates in the order the text prints them.
        default_year: Year for the first token when the text has no year at all.
            None keeps such tokens unresolved: the year is not guessed.

    Returns:
        One date per token, None where the year could not be established or the
        day does not exist in that month.
    """
    items = list(tokens)
    if not items:
        return []
    years: list[int | None] = [token.year for token in items]
    # The token the others take their year from: the first one that has a year, else the first one with the default year.
    anchor = -1
    anchor_year = 0
    for index, token in enumerate(items):
        if token.year is not None:
            anchor, anchor_year = index, token.year
            break
    if anchor < 0:
        if default_year is None:
            return [None] * len(items)
        anchor, anchor_year = 0, default_year
        years[0] = default_year
    year = anchor_year
    for index in range(anchor + 1, len(items)):
        given = items[index].year
        if given is not None:
            year = given
        elif (items[index].month, items[index].day) < (items[index - 1].month, items[index - 1].day):
            year += 1
        years[index] = year
    year = anchor_year
    for index in range(anchor - 1, -1, -1):
        given = items[index].year
        if given is not None:
            year = given
        elif (items[index].month, items[index].day) > (items[index + 1].month, items[index + 1].day):
            year -= 1
        years[index] = year
    resolved: list[date | None] = []
    for token, chosen in zip(items, years, strict=True):
        try:
            resolved.append(date(chosen, token.month, token.day) if chosen is not None else None)
        except ValueError:
            resolved.append(None)
    return resolved


def parse_written_range(text: Any, default_year: int | None = None) -> tuple[date | None, date | None]:
    """Read the first and last date of a text such as ``Del 21 de octubre al 16 de diciembre de 2026``.

    Args:
        text: The text as printed by the source.
        default_year: Year to use when the text has none (None keeps it unresolved).

    Returns:
        ``(start, end)``: ``end`` is None for a single date, ``start`` is None
        when the text carries no date whose year can be established. An end
        before the start is dropped rather than shown as an inverted range.
    """
    resolved = [found for found in resolve_years(date_tokens(text), default_year) if found is not None]
    if not resolved:
        return None, None
    start = resolved[0]
    end = resolved[-1] if len(resolved) > 1 else None
    if end is not None and end < start:
        end = None
    return start, end


def madrid_now(now: datetime | None = None) -> datetime:
    """``now`` in Madrid time to the second, or the current time when None is given."""
    moment = now or datetime.now(MADRID)
    return (moment if moment.tzinfo else moment.replace(tzinfo=MADRID)).astimezone(MADRID).replace(microsecond=0)
