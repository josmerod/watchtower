"""Meetup.com events in València: the JSON-LD the search page embeds, with the static cards as fallback.

Moved unchanged from ``valencia_events_etl.py`` (T-143): the URL, the headers,
the parsers and the records are the ones that ran before; only the home
changed, so the existing tests keep describing this source.
"""

import logging
from typing import Any

import requests
from bs4 import BeautifulSoup

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.etl.news.valencia_events.dates import to_iso_date
from src.etl.news.valencia_events.dom import href_str, is_meetup_date_text
from src.etl.news.valencia_events.jsonld import iter_jsonld_items, jsonld_location, jsonld_offers, jsonld_venue

FIND_URL = "https://www.meetup.com/es-ES/find/?location=es--Valencia&source=EVENTS"
SOURCE = "meetup.com"
MAX_EVENTS = 20


def fetch_events(logger: logging.Logger | None = None) -> list[dict]:
    """Fetch events from Meetup.com for Valencia.

    A failure of the whole fetch is logged and yields an empty list, as it did
    before the move.
    """
    log = logger or logging.getLogger(__name__)
    try:
        log.info("Fetching events from Meetup.com")

        # Note: Meetup.com requires API key for full access
        # For now, we'll use web scraping approach
        url = FIND_URL

        headers = {"User-Agent": SCRAPER_DEFAULT_USER_AGENT}

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Primary: Meetup embeds a JSON-LD array of schema.org Events with
        # full ISO startDate/endDate (UTC) plus name/url/description. The
        # interactive event cards render client-side, so the static-HTML
        # card scraping further below only acts as a fallback.
        jsonld_events: list[dict[str, Any]] = []
        for node in iter_jsonld_items(soup):
            if node.get("@type") != "Event" or not str(node.get("name") or "").strip():
                continue
            title = str(node.get("name")).strip()
            offers = jsonld_offers(node)
            jsonld_events.append(
                {
                    "title": title,
                    "url": str(node.get("url") or ""),
                    "date_text": str(node.get("startDate") or ""),
                    "start_date": to_iso_date(node.get("startDate")),
                    "end_date": to_iso_date(node.get("endDate")),
                    "category": "meetup",
                    "description": str(node.get("description") or "").strip(),
                    "source": SOURCE,
                    "venue": jsonld_venue(node),
                    "price_info": str(offers.get("price_info") or ""),
                    "is_free": offers.get("is_free"),
                    "metadata": {
                        "location": jsonld_location(node),
                        "offers_availability": str(offers.get("offers_availability") or ""),
                        "offers_url": str(offers.get("offers_url") or ""),
                    },
                }
            )

        if jsonld_events:
            log.info(f"Found {len(jsonld_events)} events from Meetup.com JSON-LD")
            return jsonld_events[:MAX_EVENTS]

        events = []

        # Fallback: look for event cards in Meetup's search results
        event_cards = soup.find_all("div", {"data-testid": "event-card"})

        for card in event_cards[:MAX_EVENTS]:  # Limit to first 20 events
            try:
                title_element = card.find("h3") or card.find("h2")
                title = title_element.text.strip() if title_element else ""

                if not title:
                    continue

                # Extract date information
                date_element = card.find("time") or card.find(  # type: ignore[call-overload]  # bs4 accepts name+string together at runtime; stubs force string=None when name is given
                    "span",
                    string=is_meetup_date_text,
                )
                date_text = date_element.get("datetime", "") if date_element else ""
                if not date_text and date_element:
                    date_text = date_element.text.strip()

                # Extract URL
                link = card.find("a")
                event_url = ""
                if link and "href" in link.attrs:
                    href = href_str(link)
                    if href.startswith("/"):
                        event_url = f"https://meetup.com{href}"
                    else:
                        event_url = href

                # Extract description/location
                desc_element = card.find("p")
                description = desc_element.text.strip() if desc_element else ""

                # Category - try to infer from title/description
                category = "meetup"
                if any(word in title.lower() for word in ["tech", "tecnología", "programming", "desarrollo"]):
                    category = "tecnología"
                elif any(word in title.lower() for word in ["música", "music", "concierto"]):
                    category = "música"

                if title:
                    events.append(
                        {
                            "title": title,
                            "url": event_url,
                            "date_text": date_text,
                            "category": category,
                            "description": description,
                            "source": SOURCE,
                        }
                    )

            except Exception as e:  # broad by design: BeautifulSoup DOM extraction from messy external HTML
                log.error(f"Error parsing Meetup event: {e}")
                continue

        log.info(f"Found {len(events)} events from Meetup.com")
        return events

    except Exception as e:  # broad by design: whole source fetch wrapper (network + scraping)
        log.error(f"Error fetching Meetup events: {e}")
        return []
