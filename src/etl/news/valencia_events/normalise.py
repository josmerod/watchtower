"""One raw record → what the tab and the API read.

:func:`normalise_record` is the only place where a record is completed, and it
completes it from what the record already says: the clock the source printed
becomes an aware datetime in ``Europe/Madrid``, the category hint becomes a
value of the vocabulary, the address becomes a zone, the price text becomes a
number. Nothing is looked up and nothing is guessed — a date, a time, a venue
or a price the source did not give stays empty (T-193).

The two readable forms follow T-178: ``start_local`` is what the tab prints
(``sáb 28/11/2026 · 18:00``); ``start_at`` is the ISO form for machines.
"""

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from src.etl.news.valencia_events.categories import fold, normalise_category
from src.etl.news.valencia_events.dates import MADRID, Moments, build_moments, date_from_iso, format_local, iso, parse_local_moment, parse_moment
from src.etl.news.valencia_events.stamps import Stamps
from src.etl.news.valencia_events.zones import venue_in_title, zone_of
from src.utils.text import html_to_text, plain_excerpt

DESCRIPTION_LIMIT = 400
# A record whose span covers the whole year is a permanent offering (a museum, a
# nightly show), not a dated event: it is tagged so the tab can leave it out.
PERMANENT_MIN_DAYS = 360
PERMANENT_TAG = "permanente"
ONLINE_TAG = "online"

# "... gratuita en València", "Visitas gratuitas", "Entrance free": the title itself says so.
_FREE_TITLE_RE = re.compile(r"\bgratuit[oa]s?\b|\bgratis\b|\b(?:entry|admission|entrance)\s+(?:is\s+)?free\b|\bfor free\b|\bfree (?:entry|admission)\b", re.IGNORECASE)
# "12", "12,50", "12.50", "1.234,56", "1 234,56" (a point or a space between groups of three digits)
_AMOUNT = r"(\d{1,3}(?:[.\s]\d{3})+(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?)"
_THOUSANDS_RE = re.compile(r"\d{1,3}(?:\.\d{3})+")
_RANGE_RE = re.compile(rf"{_AMOUNT}\s*(?:–|—|-|a)\s*{_AMOUNT}")
_FROM_RE = re.compile(rf"desde\s*{_AMOUNT}", re.IGNORECASE)
_SINGLE_RE = re.compile(rf"^(?:€|\$|£)?\s*{_AMOUNT}\s*(?:€|eur|euros?|usd|\$|gbp|£)?\s*$", re.IGNORECASE)
_FREE_RE = re.compile(r"^(gratis|gratuito|gratuita|free|entrada gratuita)\b", re.IGNORECASE)
_CURRENCY_RE = re.compile(r"(euros?|eur|usd|gbp|[€$£])", re.IGNORECASE)
_CURRENCIES = {"€": "EUR", "EUR": "EUR", "EURO": "EUR", "EUROS": "EUR", "USD": "USD", "$": "USD", "GBP": "GBP", "£": "GBP"}
# Meetup descriptions carry light Markdown: links, bold, headings.
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MARKDOWN_MARK_RE = re.compile(r"(\*\*|__|^#+\s*|`+)", re.MULTILINE)


@dataclass(frozen=True)
class Price:
    """What the source says about the price; ``price`` None means unknown, never free."""

    price: float | None
    price_max: float | None
    currency: str
    is_free: bool | None


def canonical_url(url: Any) -> str:
    """A link as one form, so the same page from two sources compares equal."""
    text = str(url or "").strip()
    if not text:
        return ""
    parts = urlsplit(text)
    if not parts.scheme:
        return text
    host = parts.netloc.lower()
    host = host[4:] if host.startswith("www.") else host
    path = parts.path[:-1] if parts.path.endswith("/") and len(parts.path) > 1 else parts.path
    return urlunsplit((parts.scheme.lower(), host, path, "", ""))


def event_id(source: str, url: str, title: str, start_date: str, start_time: str = "") -> str:
    """Stable id of an event: its page, its title, its day and its clock.

    The title is part of the identity because one page can list several events
    on the same day (two fairs of Feria Valencia share a web site). It is
    folded, so that a change of case or accents does not make an event look new.
    """
    folded_title = fold(" ".join(title.split()))
    identity = f"{url}|{folded_title}" if url else f"{source}|{folded_title}"
    digest = hashlib.sha1(f"{identity}|{start_date}|{start_time}".encode(), usedforsecurity=False).hexdigest()
    return digest[:16]


def _amount(text: str) -> float | None:
    """``"12,50"`` → 12.5, ``"1.234,56"`` → 1234.56, ``"10"`` → 10.0; None when it is not a number.

    Both marks are the Spanish way (a point for thousands, a comma for decimals). A lone comma is a
    decimal mark; a lone point between groups of three digits is a thousands mark.
    """
    text = text.strip().replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif _THOUSANDS_RE.fullmatch(text):
        text = text.replace(".", "")
    else:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def parse_price(price_info: Any, is_free: Any = None) -> Price:
    """Read the price text a source prints.

    Args:
        price_info: As printed: ``Gratis``, ``Desde 3 €``, ``12,50 - 25 €``, ``10 USD``, ``""``.
        is_free: What the source stated about being free, when it stated it.

    Returns:
        The price. A text that cannot be read leaves the amount unknown; the
        ``is_free`` the source stated is kept either way.
    """
    stated = is_free if isinstance(is_free, bool) else None
    if stated is True:
        return Price(0.0, None, "EUR", True)
    text = html_to_text(str(price_info or "")).strip()
    if not text:
        return Price(None, None, "", stated)
    if _FREE_RE.match(text):
        return Price(0.0, None, "EUR", True)
    currency_match = _CURRENCY_RE.search(text)
    currency = _CURRENCIES.get(currency_match.group(1).upper(), "") if currency_match else "EUR"
    found = _RANGE_RE.search(text)
    if found:
        low, high = _amount(found.group(1)), _amount(found.group(2))
        if low is not None and high is not None:
            return Price(low, high, currency, low == 0.0 and high == 0.0)
    found = _FROM_RE.search(text)
    if found:
        low = _amount(found.group(1))
        if low is not None:
            return Price(low, None, currency, low == 0.0)
    single = _SINGLE_RE.match(text)
    if single:
        value = _amount(single.group(1))
        if value is not None:
            return Price(value, None, currency, value == 0.0)
    return Price(None, None, "", stated)


def plain_description(raw: Any, title: str) -> str:
    """The description as a plain excerpt; "" when it is empty or only repeats the title."""
    text = html_to_text(str(raw or ""))
    text = _MARKDOWN_LINK_RE.sub(r"\1", text)
    text = re.sub(r"\s+", " ", _MARKDOWN_MARK_RE.sub(" ", text)).strip()
    clean_title = re.sub(r"\s+", " ", title).strip()
    if not text or text.casefold() == clean_title.casefold():
        return ""
    return plain_excerpt(text, DESCRIPTION_LIMIT)


def event_moments(event: Mapping[str, Any]) -> Moments:
    """When the event happens, from the dates, clocks or timestamps the record carries."""
    zoned_start = parse_moment(event.get("start_datetime"))
    if zoned_start is not None:
        return Moments(zoned_start, parse_moment(event.get("end_datetime")), all_day=False)
    start_date = str(event.get("start_date") or "")
    # The legacy JSON-LD sources keep the full start timestamp in date_text (Meetup's are UTC).
    # It places the event better than the calendar day: down to the hour, and on the day it is
    # in Spain when the evening there is already the next day.
    moment = parse_moment(event.get("date_text")) or parse_local_moment(event.get("date_text"))
    if moment is not None:
        last = date_from_iso(event.get("end_date"))
        end = datetime.combine(last + timedelta(days=1), time(0, 0), tzinfo=MADRID) if last is not None and last > moment.date() else None
        return Moments(moment, end, all_day=False)
    return build_moments(start_date, str(event.get("end_date") or ""), start_time=str(event.get("start_time") or ""), end_time=str(event.get("end_time") or ""))


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalise_record(event: Mapping[str, Any], *, now: datetime, stamps: Stamps, source_label: str = "") -> dict[str, Any]:
    """Complete one processed record.

    Args:
        event: A record as ``process_valencia_events`` outputs it.
        now: The moment of the run, aware.
        stamps: Detection stamps of previous runs, by event id.
        source_label: Human name of the source, kept in the metadata.

    Returns:
        The fields of the stored event (a superset of ``ValenciaEvent``).
    """
    title = _text(event.get("title"))
    url = canonical_url(event.get("url"))
    source = _text(event.get("source"))
    raw_metadata = event.get("metadata")
    metadata = dict(raw_metadata) if isinstance(raw_metadata, dict) else {}
    tags = [_text(tag) for tag in (event.get("tags") or []) if _text(tag)]
    online = ONLINE_TAG in tags or bool(metadata.get("online"))
    start_date = _text(event.get("start_date"))
    end_date = _text(event.get("end_date"))
    start_time = _text(event.get("start_time"))
    end_time = _text(event.get("end_time"))

    moments = event_moments(event)
    start_day = date_from_iso(start_date)
    last_day = date_from_iso(end_date) or start_day
    if start_day is not None and last_day is not None and (last_day - start_day).days >= PERMANENT_MIN_DAYS and PERMANENT_TAG not in tags:
        tags.append(PERMANENT_TAG)

    description = plain_description(event.get("description"), title)
    category = normalise_category(_text(event.get("category")), title, description, default_category=_text(metadata.get("default_category")), url=url)

    venue = _text(event.get("venue"))
    location = _text(metadata.get("location"))
    address = _text(event.get("address")) or (location if location and location.casefold() != venue.casefold() else "")
    city = _text(event.get("city"))
    zone = zone_of(venue=venue, address=address, location=location, city=city, online=online)
    if not zone:
        named, named_zone = venue_in_title(title)
        if named:
            zone = named_zone
            metadata["zone_basis"] = "title"
            if not venue:
                venue = named
                metadata["venue_basis"] = "title"

    price = parse_price(event.get("price_info"), event.get("is_free"))
    if price.price is None and price.is_free is not False and _FREE_TITLE_RE.search(title):
        price = Price(0.0, None, "EUR", True)
        metadata["price_basis"] = "title"
    if online and ONLINE_TAG not in tags:
        tags.append(ONLINE_TAG)
    if source_label:
        metadata["source_label"] = source_label

    identifier = event_id(source, url, title, start_date, start_time)
    stamp = stamps.get(identifier)
    first = (parse_moment(stamp["first_detected_at"]) if stamp else None) or now
    return {
        "title": title,
        "url": url,
        "source": source,
        "category": category,
        "description": description,
        "start_date": start_date,
        "end_date": end_date,
        "date_text": _text(event.get("date_text")),
        "venue": venue,
        "price_info": _text(event.get("price_info")),
        "is_free": price.is_free,
        "metadata": metadata,
        "event_id": identifier,
        "start_time": start_time if not moments.all_day else "",
        "end_time": end_time if not moments.all_day else "",
        "all_day": moments.all_day,
        "start_at": iso(moments.start) if moments.start else "",
        "end_at": iso(moments.end) if moments.end else "",
        "start_local": format_local(moments.start, with_time=not moments.all_day) if moments.start else "",
        "end_local": readable_end(moments, end_date, end_time),
        "address": address,
        "city": city,
        "zone": zone,
        "tags": tags,
        "price": price.price,
        "price_max": price.price_max,
        "currency": price.currency,
        "first_detected_at": iso(first),
        "first_detected_local": format_local(first, with_time=True),
        "last_seen_at": iso(now),
    }


def readable_end(moments: Moments, end_date: str, end_time: str) -> str:
    """The end as it is shown (T-178): the last day for a span, the clock when there is one, "" for a single day."""
    end = moments.end
    if end is None:
        return ""
    if end_time:
        return format_local(end, with_time=True)
    if end.time() == time(0, 0):
        # The end is the midnight after the last day: that day, not the next one, is what happened.
        return format_local(end - timedelta(days=1), with_time=False) if end_date else ""
    return format_local(end, with_time=True)
