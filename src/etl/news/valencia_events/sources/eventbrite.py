"""Eventbrite events in València: the schema.org ItemList the listing embeds, with the cards as fallback.

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
from src.etl.news.valencia_events.dom import href_str
from src.etl.news.valencia_events.jsonld import iter_jsonld_items, jsonld_location, jsonld_offers, jsonld_venue

LISTING_URL = "https://www.eventbrite.es/d/spain--valencia/all-events/"
SOURCE = "eventbrite.com"
MAX_EVENTS = 15


def fetch_events(logger: logging.Logger | None = None) -> list[dict]:
    """Fetch events from Eventbrite for Valencia.

    A failure of the whole fetch is logged and yields an empty list, as it did
    before the move.
    """
    log = logger or logging.getLogger(__name__)
    try:
        log.info("Fetching events from Eventbrite")

        # Eventbrite API would require API key, so we'll use web scraping
        url = LISTING_URL

        headers = {"User-Agent": SCRAPER_DEFAULT_USER_AGENT}

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Primary: Eventbrite embeds a schema.org ItemList in JSON-LD whose
        # ListItem entries carry ISO startDate/endDate, name, url and
        # location per event — far more reliable than the JS-rendered cards.
        jsonld_events: list[dict[str, Any]] = []
        for node in iter_jsonld_items(soup):
            if node.get("@type") != "ItemList":
                continue
            for list_item in node.get("itemListElement") or []:
                if not isinstance(list_item, dict):
                    continue
                item = list_item.get("item")
                if not isinstance(item, dict):
                    continue
                title = str(item.get("name") or "").strip()
                if not title:
                    continue
                category = "eventbrite"
                if any(word in title.lower() for word in ["tech", "tecnología", "startup"]):
                    category = "tecnología"
                elif any(word in title.lower() for word in ["música", "concierto", "festival"]):
                    category = "música"
                offers = jsonld_offers(item)
                jsonld_events.append(
                    {
                        "title": title,
                        "url": str(item.get("url") or ""),
                        "date_text": str(item.get("startDate") or ""),
                        "start_date": to_iso_date(item.get("startDate")),
                        "end_date": to_iso_date(item.get("endDate")),
                        "category": category,
                        "description": str(item.get("description") or "").strip(),
                        "source": SOURCE,
                        "venue": jsonld_venue(item),
                        "price_info": str(offers.get("price_info") or ""),
                        "is_free": offers.get("is_free"),
                        "metadata": {
                            "location": jsonld_location(item),
                            "offers_availability": str(offers.get("offers_availability") or ""),
                            "offers_url": str(offers.get("offers_url") or ""),
                        },
                    }
                )
            if jsonld_events:
                break  # only the first ItemList matters

        if jsonld_events:
            log.info(f"Found {len(jsonld_events)} events from Eventbrite JSON-LD")
            return jsonld_events[:MAX_EVENTS]

        events = []

        # Look for event cards
        event_cards = soup.find_all("div", class_=lambda x: x and "event-card" in x.lower())

        # If that doesn't work, look for event listings
        if not event_cards:
            event_cards = soup.find_all(
                "div",
                class_=lambda x: x and any(term in x.lower() for term in ["event", "card", "listing"]),
            )

        for card in event_cards[:MAX_EVENTS]:  # Limit to first 15 events
            try:
                title_element = card.find("h3") or card.find("h2") or card.find("h4")
                title = title_element.text.strip() if title_element else ""

                if not title:
                    continue

                # Extract date
                date_element = card.find("p", class_=lambda x: x and "date" in x.lower())
                date_text = date_element.text.strip() if date_element else ""

                # Extract URL
                link = card.find("a")
                event_url = ""
                if link and "href" in link.attrs:
                    href = href_str(link)
                    if href.startswith("/"):
                        event_url = f"https://eventbrite.com{href}"
                    else:
                        event_url = href

                # Extract description
                desc_element = card.find("p", class_=lambda x: x and "description" in x.lower())
                description = desc_element.text.strip() if desc_element else ""

                # Category
                category = "eventbrite"
                if any(word in title.lower() for word in ["tech", "tecnología", "startup"]):
                    category = "tecnología"
                elif any(word in title.lower() for word in ["música", "concierto", "festival"]):
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
                log.error(f"Error parsing Eventbrite event: {e}")
                continue

        log.info(f"Found {len(events)} events from Eventbrite")
        return events

    except Exception as e:  # broad by design: whole source fetch wrapper (network + scraping)
        log.error(f"Error fetching Eventbrite events: {e}")
        return []
