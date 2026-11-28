"""What the cinema sources share: the HTTP call, the listings and the version labels.

Each source module in this package turns one listing page into session
dictionaries; this module holds the pieces they all need so they do not drift
apart.
"""

from __future__ import annotations

import logging
import re
import time
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests
from bs4 import Tag

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)

_MADRID = ZoneInfo("Europe/Madrid")

TIMEOUT_SECONDS = 30
POLITE_DELAY_SECONDS = 1.0

# Spanish, with the Valencian forms some public sites use ("març", "set", "des").
SPANISH_MONTHS = {"ene": 1, "gen": 1, "feb": 2, "mar": 3, "marc": 3, "abr": 4, "mai": 5, "may": 5, "jun": 6, "jul": 7, "ago": 8, "set": 9, "sep": 9, "oct": 10, "nov": 11, "des": 12, "dic": 12}
SPANISH_WEEKDAYS = {"lun": 0, "lunes": 0, "mar": 1, "martes": 1, "mie": 2, "miercoles": 2, "jue": 3, "jueves": 3, "vie": 4, "viernes": 4, "sab": 5, "sabado": 5, "dom": 6, "domingo": 6}

# A format word in a listing title: "(IMAX)", "(4DX 3D)", "(Infinity Vision) (ScreenX)".
FORMAT_MARKERS = ("imax", "3d", "4dx", "screenx", "isense", "infinity vision", "atmos", "urban", "dolby", "laser", "vip", "xplus", "premium", "large format")
# A suffix that names the plain screening: it tells nothing apart and is dropped.
PLAIN_FORMATS = {"digital", "digital 2d", "2d", "digital hd"}
# A city that the sources spell two ways, by lower-case source spelling.
CITY_ALIASES = {"valencia": "València"}
_DAY_LABEL = re.compile(r"(\d{1,2})\s+(?:de\s+)?([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)")
_TIME_RE = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*$")
_ANY_TIME_RE = re.compile(r"\b(\d{1,2}:\d{2})\b")
_TRAILING_GROUP = re.compile(r"\s*\(([^()]*)\)\s*$")
_LEADING_VERSION = re.compile(r"^(?:VOSE|VOS|VO|DOB)\s+", re.IGNORECASE)


class SourceUnavailable(Exception):
    """A listing page could not be read: transport error, HTTP error, or a page that is not the listing."""


@dataclass(frozen=True)
class Listing:
    """One page to read: the listing of one cinema."""

    url: str
    key: str = ""
    name: str = ""
    city: str = ""
    address: str = ""

    def __str__(self) -> str:
        """The cinema name, or the page key for a page whose name is read from the page itself."""
        return self.name or self.key


@dataclass
class ListingResult:
    """What one listing gave: its sessions, or the reason it could not be read."""

    listing: Listing
    cinema: str = ""
    city: str = ""
    sessions: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""

    @property
    def ok(self) -> bool:
        """True when the page was read, with sessions or without."""
        return not self.error


class PageFetcher:
    """Downloads listing pages once each, a pause apart.

    The cinema sites are small and read for free: one request per page and a
    second of quiet between two requests is the whole courtesy.
    """

    def __init__(self, delay_seconds: float = POLITE_DELAY_SECONDS, timeout_seconds: float = TIMEOUT_SECONDS) -> None:
        self.delay_seconds = delay_seconds
        self.timeout_seconds = timeout_seconds
        self.urls_requested: list[str] = []

    def get(self, url: str) -> bytes:
        """Return the body of ``url``.

        Args:
            url: Page to read.

        Returns:
            The response body, undecoded: BeautifulSoup reads the encoding from the document itself.

        Raises:
            SourceUnavailable: On a transport error or any HTTP error status. A 403 or a 429 is reported as
                such and not retried: the site said no.
        """
        if self.urls_requested:
            time.sleep(self.delay_seconds)
        self.urls_requested.append(url)
        try:
            response = requests.get(url, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT, "Accept-Language": "es-ES,es;q=0.9"}, timeout=self.timeout_seconds)
        except requests.RequestException as exc:
            raise SourceUnavailable(f"{url}: {type(exc).__name__}: {exc}") from exc
        if response.status_code in (403, 429):
            raise SourceUnavailable(f"{url}: HTTP {response.status_code}, the site refuses automated reads")
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise SourceUnavailable(f"{url}: HTTP {response.status_code}") from exc
        return response.content


def read_listings(fetcher: Any, listings: Sequence[Listing], parse: Callable[[bytes, Listing, date], list[dict[str, Any]]], reference: date) -> list[ListingResult]:
    """Read every listing page, one request each, and never let one failure sink the others.

    Args:
        fetcher: An object with ``get(url) -> bytes``.
        listings: The pages to read.
        parse: The source's parser: page body, listing and reference day into sessions.
        reference: The day the pages are read.

    Returns:
        One result per listing, in order. A page that could not be read gives a result with no sessions and
        the reason in ``error``.
    """
    results: list[ListingResult] = []
    for listing in listings:
        result = ListingResult(listing=listing, cinema=listing.name, city=listing.city)
        try:
            result.sessions = parse(fetcher.get(listing.url), listing, reference)
        except SourceUnavailable as exc:
            result.error = str(exc).removeprefix(listing.url).strip(": ")
        except Exception as exc:  # broad by design: a markup change on one page is reported, not raised
            logger.warning("cinema: %s could not be parsed: %s: %s", listing, type(exc).__name__, exc)
            result.error = f"parse error ({type(exc).__name__})"
        result.cinema = result.sessions[0]["cinema"] if result.sessions else result.cinema
        result.city = result.sessions[0]["city"] if result.sessions else result.city
        results.append(result)
        logger.info("cinema: %s -> %s sessions%s", listing.url, len(result.sessions), f" ({result.error})" if result.error else "")
    return results


def today() -> date:
    """The calendar day in Spain, where the cinemas are.

    Returns:
        Today's date in the Europe/Madrid zone.
    """
    return datetime.now(_MADRID).date()


def drop_past_days(records: list[dict[str, Any]], day: date, horizon_days: int = 120) -> list[dict[str, Any]]:
    """Keep the sessions of ``day`` and of the days after it, up to a sane horizon.

    Feeds keep yesterday's rows until they are rebuilt early in the morning,
    and a listing read before midnight still lists that day once midnight has
    passed. A feed now and then carries a stray date months ahead; nothing is
    on sale further out than a season.

    Args:
        records: Session dictionaries with an ISO ``date``.
        day: The first day that still counts.
        horizon_days: How many days ahead a session may be.

    Returns:
        The records within the window, in their order.
    """
    first = day.isoformat()
    last = date.fromordinal(day.toordinal() + horizon_days).isoformat()
    return [record for record in records if first <= str(record.get("date", "")) <= last]


def resolve_day(day_number: int, month: int, reference: date, weekday: int | None = None) -> date | None:
    """Give a day printed without its year the year it must have.

    Listings print "Sáb 28 Nov": the year is the one, this year or the next,
    that puts the day closest to the reference and, when the listing prints
    the weekday too, on that weekday.

    Args:
        day_number: Day of the month.
        month: Month number.
        reference: A day around which the listing is read, typically today.
        weekday: Weekday the listing prints, Monday being 0, when it prints one.

    Returns:
        The date, or None when the month and day do not form a calendar day.
    """
    candidates: list[date] = []
    for year in (reference.year, reference.year + 1):
        try:
            candidates.append(date(year, month, day_number))
        except ValueError:
            continue
    if weekday is not None:
        on_that_weekday = [candidate for candidate in candidates if candidate.weekday() == weekday]
        if on_that_weekday:
            candidates = on_that_weekday
    if not candidates:
        return None
    return min(candidates, key=lambda candidate: abs((candidate - reference).days))


def day_from_label(label: str, reference: date) -> str:
    """Read a day printed in Spanish without its year, "Sáb 28 Nov" or "domingo, 29 de noviembre".

    Args:
        label: The day label as printed.
        reference: A day around which the listing is read.

    Returns:
        YYYY-MM-DD, or "" when the label carries no day and month.
    """
    match = _DAY_LABEL.search(label)
    if not match:
        return ""
    month = spanish_month(match.group(2))
    if month is None:
        return ""
    words = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", label[: match.start()])
    weekday = spanish_weekday(words[0]) if words else None
    resolved = resolve_day(int(match.group(1)), month, reference, weekday)
    return resolved.isoformat() if resolved else ""


def clock_time(text: str) -> str:
    """Normalise a start time to HH:MM.

    Args:
        text: What the listing prints: "18:00 h", "9:30", " 20:15 ".

    Returns:
        HH:MM, or "" when ``text`` is not a 24-hour clock time.
    """
    match = _TIME_RE.match(text or "")
    if not match:
        return ""
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        return ""
    return f"{hour:02d}:{minute:02d}"


def clock_times(text: str) -> list[str]:
    """Every clock time printed in a text, "18:00 y 22:00 h", in order."""
    return [clock_time(found) for found in _ANY_TIME_RE.findall(text)]


def text_of(tag: Tag | None, separator: str = " ") -> str:
    """Read an element's text with the whitespace squeezed, or "" when there is no element."""
    return tag.get_text(separator, strip=True) if tag is not None else ""


def attr_of(tag: Tag | None, name: str) -> str:
    """Read an element's attribute as a plain string, or "" when there is no element or no such attribute."""
    if tag is None:
        return ""
    value = tag.get(name)
    return value.strip() if isinstance(value, str) else ""


def http_url(href: str) -> str:
    """Keep a link only when it is a plain web address; "#", "javascript:" and the like give ""."""
    href = href.strip()
    return href if href.startswith(("https://", "http://")) else ""


def _fold(text: str) -> str:
    """Lowercase and drop the accents, so "Mié" and "V.O.S." compare with their plain forms."""
    return unicodedata.normalize("NFD", text.lower()).encode("ascii", "ignore").decode("ascii")


def spanish_month(token: str) -> int | None:
    """Read a Spanish month, abbreviated ("nov", "dic") or in full ("noviembre"), into its month number."""
    folded = _fold(token.strip(". "))
    return SPANISH_MONTHS.get(folded) or SPANISH_MONTHS.get(folded[:3])


def spanish_weekday(token: str) -> int | None:
    """Read a Spanish weekday ("sáb", "domingo") into its weekday, Monday being 0."""
    return SPANISH_WEEKDAYS.get(_fold(token.strip(". ")))


def normalise_version(raw: str) -> str:
    """Fold what a listing prints about audio and subtitles into one of four labels.

    Sources write the same handful of versions many ways: "VOS español",
    "VOSE", "V.O.S.ING./CAST." and "VOS CASTELLANO" are all VOSE; "VOS
    VALENCIANO" is subtitled, but not in Spanish, so VOS; "DOBLADA CAST." and
    "DOBLADA AL ESPAÑOL" are DOB; a bare "VO" or "sin subtítulos" is VO.

    Args:
        raw: The version text as printed.

    Returns:
        VOSE, VOS, VO or DOB; "" when the listing prints none, a dash, or something not recognised.
    """
    text = _fold(raw).strip()
    if not text or text in {"-", "—"}:
        return ""
    if "doblad" in text or text in {"dob", "dob."}:
        return "DOB"
    if "sin subtitulos" in text:
        return "VO"
    compact = re.sub(r"[^a-z0-9]+", "", text)
    subtitled = "vos" in compact or "v.o.s" in text
    if subtitled:
        in_spanish = "vose" in compact or any(marker in text for marker in ("cast", "espanol", "spanish", "esp"))
        return "VOSE" if in_spanish else "VOS"
    if compact.startswith("vo"):
        return "VO"
    return ""


def version_from_language(audio: str, subtitles: str) -> str:
    """Derive the version from an audio line and a subtitles line.

    For the listings that print "Idioma: Inglés" and "Subtítulos: Castellano"
    instead of a version label.

    Args:
        audio: The audio language as printed ("Inglés", "Castellano (doblada)", "Castellano").
        subtitles: The subtitle language as printed, or "" when there is none.

    Returns:
        DOB when dubbed; "" for a Spanish-language film without subtitles; VOSE for an original version
        with Spanish subtitles; VOS for one with other subtitles; VO for one without.
    """
    audio_text = _fold(audio)
    if "doblad" in audio_text:
        return "DOB"
    if any(marker in audio_text for marker in ("castellano", "espanol", "spanish", "valenciano", "catalan")):
        return ""
    if not subtitles.strip():
        return "VO"
    subtitles_text = _fold(subtitles)
    return "VOSE" if any(marker in subtitles_text for marker in ("castellano", "espanol", "spanish", "espa")) else "VOS"


def split_title(label: str) -> tuple[str, str, str]:
    """Split a listing title that carries its version and format in parentheses.

    "Dune: Parte Tres (VOS español) (IMAX)" gives ("Dune: Parte Tres", "VOSE",
    "IMAX"); "PRIMAVERA (2026)" keeps its year, because a parenthetical that is
    neither a version nor a format belongs to the title. "(Digital)" names the
    plain screening and is dropped.

    Args:
        label: The title as the listing prints it.

    Returns:
        (title, version, format); the version and the format are "" for a plain screening.
    """
    title = " ".join(label.split())
    version = ""
    formats: list[str] = []
    while True:
        match = _TRAILING_GROUP.search(title)
        if not match:
            break
        group = match.group(1).strip()
        found = normalise_version(group)
        if found:
            version = version or found
        elif _fold(group) in PLAIN_FORMATS:
            pass
        elif any(marker in _fold(group) for marker in FORMAT_MARKERS):
            formats.append(group)
        else:
            break
        title = title[: match.start()].rstrip()
    if version:
        title = _LEADING_VERSION.sub("", title).strip()
    return title, version, " / ".join(reversed(formats))


def make_session(*, title: str, cinema: str, city: str, day: str, time: str, source: str, **extra: Any) -> dict[str, Any] | None:
    """Assemble one session dictionary, or None when it lacks what makes it a session.

    Args:
        title: Film title.
        cinema: Cinema name.
        city: City or town, spelled the same whatever the source ("Valencia" is "València").
        day: Screening day as YYYY-MM-DD.
        time: Start time as HH:MM.
        source: Site the session was read from.
        **extra: Any other field of ``CinemaSession``; the empty ones are left out.

    Returns:
        The record, with the text fields stripped, or None when the title, the cinema, the city, the day
        or the time is missing.
    """
    title = " ".join(title.split())
    city = CITY_ALIASES.get(city.strip().casefold(), city.strip())
    if not (title and day and time and cinema.strip() and city):
        return None
    record: dict[str, Any] = {"title": title, "cinema": cinema.strip(), "city": city.strip(), "date": day, "time": time, "source": source}
    record.update({key: value.strip() if isinstance(value, str) else value for key, value in extra.items() if value not in (None, "")})
    return record
