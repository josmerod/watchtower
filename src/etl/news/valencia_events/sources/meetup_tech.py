"""Meetup.com, technology meetups in València.

`https://www.meetup.com/es-ES/find/?location=es--Valencia&categoryId=546&source=EVENTS`
— HTML, one request. The search page of the Tech category embeds a JSON-LD
array of schema.org Events with full UTC timestamps, name, link, description,
venue and the group in the link path. The general Valencia search (the legacy
``meetup.com`` source) mixes socials with everything else and is cut to twenty
events, so the technology meetups deserve a page of their own.

The category page also lists online events of groups from anywhere: only the
events held in València, or run by a València group (its path ends in
``valencia``), are kept. Those are ``tech`` by construction.

The per-group RSS feeds (``https://www.meetup.com/<group>/events/rss/``) are
keyless and answer 200 to a plain client, but their items carry no event date
(only the publication date): the date would have to come from somewhere else,
so they are not used.

Verified 2026-11-28: 200, 304 KB, 12 JSON-LD events of which 6 are in València.
"""

import logging
import re
from typing import Any
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from src.etl.news.valencia_events.dates import iso, parse_moment
from src.etl.news.valencia_events.http import fetch_page
from src.etl.news.valencia_events.jsonld import iter_jsonld_items, jsonld_is_online, jsonld_location, jsonld_offers, jsonld_venue
from src.etl.news.valencia_events.records import CITY_VALENCIA, build_record, clock_text
from src.utils.text import html_to_text

FIND_URL = "https://www.meetup.com/es-ES/find/?location=es--Valencia&categoryId=546&source=EVENTS"
SOURCE = "meetup.com/tech"
LABEL = "Meetup · tecnología"
MAX_EVENTS = 50

_GROUP_RE = re.compile(r"^https?://(?:www\.)?meetup\.com/([^/]+)/", re.IGNORECASE)
_CITY_RE = re.compile(r"val[eè]ncia", re.IGNORECASE)


def group_slug(url: str) -> str:
    """Meetup group a link belongs to (``valencia-codes``), "" for other links."""
    match = _GROUP_RE.match(url)
    return match.group(1) if match else ""


def is_in_valencia(location: str, url: str) -> bool:
    """True when the event is held in València or its group is a València group."""
    return bool(_CITY_RE.search(location)) or group_slug(url).lower().endswith("valencia")


def _host_of(url: str) -> str:
    """Lower-case host of a link."""
    return urlsplit(url).netloc.lower()


def parse(html: bytes) -> list[dict[str, Any]]:
    """Read the JSON-LD events of the page, kept to València.

    Args:
        html: Raw body of the search page.

    Returns:
        Raw records in page order; an event without a start timestamp, or held
        elsewhere by another city's group, is skipped.
    """
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict[str, Any]] = []
    for node in iter_jsonld_items(soup):
        if node.get("@type") != "Event":
            continue
        title = str(node.get("name") or "").strip()
        url = str(node.get("url") or "")
        start = parse_moment(node.get("startDate"))
        location = jsonld_location(node)
        if not title or start is None or not is_in_valencia(location, url) or _host_of(url) != "www.meetup.com":
            continue
        end = parse_moment(node.get("endDate"))
        if end is not None and end < start:
            end = None
        offers = jsonld_offers(node)
        online = jsonld_is_online(node)
        venue = "" if online else jsonld_venue(node)
        record = build_record(
            source=SOURCE,
            title=title,
            url=url,
            start_date=start.date(),
            end_date=end.date() if end is not None and end.date() > start.date() else None,
            date_text=str(node.get("startDate") or ""),
            start_time=clock_text(start.strftime("%H:%M")),
            end_time=clock_text(end.strftime("%H:%M")) if end is not None and end.date() == start.date() else "",
            category="tech",
            description=html_to_text(str(node.get("description") or "")),
            venue=venue,
            address="" if online else location,
            city="" if online else CITY_VALENCIA,
            price_info=str(offers.get("price_info") or ""),
            is_free=offers.get("is_free"),
            tags=["online"] if online else [],
            metadata={
                "group": group_slug(url),
                "location": location,
                "online": online,
                "offers_availability": str(offers.get("offers_availability") or ""),
                "offers_url": str(offers.get("offers_url") or ""),
            },
        )
        record["start_datetime"] = iso(start)
        record["end_datetime"] = iso(end) if end is not None else ""
        records.append(record)
    return records[:MAX_EVENTS]


def fetch(logger: logging.Logger | None = None) -> list[dict[str, Any]]:
    """Fetch the Tech category search once and return the València meetups."""
    log = logger or logging.getLogger(__name__)
    log.info(f"Fetching technology meetups from {FIND_URL}")
    records = parse(fetch_page(FIND_URL))
    log.info(f"Retrieved {len(records)} technology meetups from Meetup")
    return records
