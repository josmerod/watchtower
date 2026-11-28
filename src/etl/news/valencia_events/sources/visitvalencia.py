"""Featured agenda of visitvalencia.com: one page per month, read with three fallback parsers.

Moved unchanged from ``valencia_events_etl.py`` (T-143): the URL, the headers,
the parsers and the records are the ones that ran before; only the home
changed, so the existing tests keep describing this source.
"""

import logging
import re
from datetime import datetime
from typing import Any, cast

import requests
from bs4 import BeautifulSoup, Tag

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.etl.news.valencia_events.dates import parse_dates_from_text
from src.etl.news.valencia_events.dom import href_str

BASE_URL = "https://www.visitvalencia.com"
SOURCE = "visitvalencia.com"

# Dynamic year matching — prevents the recurring "hardcoded year" bug.
_NOW = datetime.now()
_VALID_YEARS = {str(_NOW.year), str(_NOW.year + 1), str(_NOW.year - 1)}


def _has_valid_year(text: str) -> bool:
    """Check if text contains a plausible event year (current, next, or prev)."""
    return any(y in text for y in _VALID_YEARS)


def month_url(date: str) -> str:
    """Listing URL for a month given as YYYY-MM."""
    return f"{BASE_URL}/agenda-valencia?date={date}"


def fetch_month(date: str, logger: logging.Logger | None = None) -> list[dict[str, Any]]:
    """Fetches events from the Valencia tourism website for a specific month.

    Args:
        date: Month in YYYY-MM format
        logger: Where to log; a module logger when None.

    Returns:
        List of event dictionaries
    """
    log = logger or logging.getLogger(__name__)
    url = month_url(date)
    log.info(f"Fetching events from {url}")

    # Send GET request to the webpage with increased timeout
    response = requests.get(url, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=30)
    response.raise_for_status()  # Raise exception for HTTP errors

    # Parse HTML content
    log.debug("Parsing HTML content")
    soup = BeautifulSoup(response.content, "html.parser")

    # Find all event items based on the provided HTML structure
    # The events appear to be in a list with each event having h3 headers
    events = []

    # APPROACH 0 (primary): structured listing cards. The agenda renders each
    # event as a div.standard-card whose heading, link and date paragraph
    # ("17/08/2026 - 30/08/2026") carry stable BEM class names, so dates can
    # be read straight from the listing without extra requests.
    for card in soup.select("div.standard-card"):
        try:
            heading = card.select_one(".standard-card__heading") or card.find(["h2", "h3"])
            title = heading.get_text(strip=True) if heading else ""
            if not title:
                continue

            dates_element = card.select_one(".standard-card__dates")
            date_text = dates_element.get_text(" ", strip=True) if dates_element else ""
            start_date, end_date = parse_dates_from_text(date_text)

            link = card.select_one("a.standard-card__link") or card.find("a", href=True)
            event_url = ""
            if link is not None:
                href = href_str(link)
                if href:
                    event_url = href if href.startswith("http") else f"{BASE_URL}{href}"

            events.append(
                {
                    "title": title,
                    "url": event_url,
                    "date_text": date_text,
                    "start_date": start_date,
                    "end_date": end_date,
                    "category": "",
                    "description": "",
                    "source": SOURCE,
                }
            )
        except Exception as e:  # broad by design: BeautifulSoup DOM extraction from messy external HTML
            log.error(f"Error parsing standard-card event: {e!s}")
            continue

    log.debug(f"Approach 0: extracted {len(events)} events from standard cards")

    # APPROACH 1 (fallback): Based on the example HTML, events seem to be contained in
    # elements with specific text in their titles
    event_blocks = (
        soup.find_all(
            lambda tag: (
                tag.name
                and tag.find(["h2", "h3"])
                and tag.find(["h2", "h3"]).text
                and any(
                    x in tag.find(["h2", "h3"]).text
                    for x in [
                        "Exposición",
                        "Concierto",
                        "Festival",
                        "Visita",
                        "Descubre",
                        "Siente",
                    ]
                )
            )
        )
        if not events
        else []
    )

    log.debug(f"Approach 1: Found {len(event_blocks)} event blocks")

    for block in event_blocks:
        try:
            title_element = block.find(["h2", "h3"])
            title = title_element.text.strip() if title_element else ""

            # Extract date - improved logic
            date_text = ""

            # Look for date patterns in the block
            date_candidates = []

            # Pattern 1: Look for text containing "Del" and "al"
            for string in block.strings:
                text = string.strip()
                if "Del" in text and "al" in text and _has_valid_year(text):
                    date_candidates.append(text)

            # Pattern 2: Look for text containing "Fecha:"
            for string in block.strings:
                text = string.strip()
                if "Fecha:" in text and _has_valid_year(text):
                    date_candidates.append(text)

            # Pattern 3: Look for standalone date patterns
            for string in block.strings:
                text = string.strip()
                if re.search(r"\d{1,2}/\d{1,2}/\d{4}", text) and _has_valid_year(text):
                    date_candidates.append(text)

            # Use the best candidate (prefer longer, more complete date info)
            if date_candidates:
                # Sort by length (longer is usually more complete)
                date_candidates.sort(key=len, reverse=True)
                date_text = date_candidates[0]

            # Fallback: if no good date found, don't use title as date
            if not date_text:
                date_text = ""

            # Extract URL
            link = block.find("a")
            event_url = href_str(link) if link else ""
            if event_url and not event_url.startswith("http"):
                event_url = f"{BASE_URL}{event_url}"

            # Extract category
            category = ""
            category_tags = block.find_all(["span", "div"], class_=True)
            for tag in category_tags:
                classes = tag.get("class")
                if classes and isinstance(classes, list):
                    class_text = " ".join(classes)
                    if any(c in class_text.lower() for c in ["música", "exposición", "deporte"]):
                        category = tag.text.strip()
                        break

            # Extract description
            description = ""
            desc_element = block.find("p")
            if desc_element:
                description = desc_element.text.strip()

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
                log.debug(f"Approach 1: Extracted event: {title}")
        except Exception as e:  # broad by design: BeautifulSoup DOM extraction from messy external HTML
            log.error(f"Error in Approach 1 parsing event: {e!s}")
            continue

    # APPROACH 2: Look for specific event pattern from the example
    if not events:
        log.debug("Trying Approach 2: Looking for specific event patterns")
        # Based on the provided HTML, events might be listed with a specific structure
        event_entries: list[Tag] = []

        # Try finding events with the format from the example
        potential_entries = soup.find_all(class_=lambda x: x and isinstance(x, str) and (x.startswith("###") or "event" in x.lower()))

        # If that doesn't work, try a more general approach
        if not potential_entries:
            # Look for sections that likely contain event information
            potential_entries = soup.find_all(lambda tag: tag.name in ["article", "div", "section"] and tag.find(["h3", "h2", "h4"]))

        event_entries.extend(potential_entries)

        # Also try with HTML structure seen in the example
        event_items = soup.find_all(lambda tag: tag.name and tag.get_text() and ("exposición" in tag.get_text().lower() or "música" in tag.get_text().lower() or _has_valid_year(tag.get_text())))

        event_entries.extend(event_items)

        log.debug(f"Approach 2: Found {len(event_entries)} potential event entries")

        for entry in event_entries:
            try:
                # Extract title
                title_element = entry.find(["h3", "h2", "h4"])
                if not title_element and entry.name in ["h3", "h2", "h4"]:
                    title_element = entry

                title = title_element.text.strip() if title_element else ""

                # Extract date - look for date pattern
                date_text = ""
                date_element = entry.find(string=lambda t: t and isinstance(t, str) and ("Del" in t or "al" in t or _has_valid_year(t)))

                if date_element:
                    date_text = date_element.strip()
                else:
                    # Try looking at sibling elements
                    next_sibling = entry.next_sibling
                    while next_sibling and not date_text:
                        if hasattr(next_sibling, "text") and isinstance(next_sibling.text, str):
                            if "Del" in next_sibling.text or "al" in next_sibling.text or _has_valid_year(next_sibling.text):
                                date_text = next_sibling.text.strip()
                        next_sibling = next_sibling.next_sibling

                # Extract URL
                event_url = ""
                link = entry.find("a") or (entry.parent.find("a") if entry.parent else None)
                if link:
                    event_url = href_str(link)
                    if event_url and not event_url.startswith("http"):
                        event_url = f"{BASE_URL}{event_url}"

                # Extract category if possible
                category = ""
                entry_classes = entry.get("class")
                if entry_classes:
                    class_text = " ".join(entry_classes if isinstance(entry_classes, list) else [entry_classes])
                    for cat in [
                        "exposición",
                        "música",
                        "gastronomía",
                        "espectáculo",
                        "deporte",
                        "naturaleza",
                        "fiestas",
                    ]:
                        if cat in class_text.lower():
                            category = cat
                            break

                # If still no category, look for it in the text
                if not category:
                    for cat in [
                        "exposición",
                        "música",
                        "gastronomía",
                        "espectáculo",
                        "deporte",
                        "naturaleza",
                        "fiestas",
                    ]:
                        if cat in entry.get_text().lower():
                            category = cat
                            break

                # Extract description
                description = ""
                desc_element = entry.find("p")
                if desc_element:
                    description = desc_element.text.strip()

                if title and title not in [e["title"] for e in events]:
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
                    log.debug(f"Approach 2: Extracted event: {title}")
            except Exception as e:  # broad by design: BeautifulSoup DOM extraction from messy external HTML
                log.error(f"Error in Approach 2 parsing event: {e!s}")
                continue

    # APPROACH 3: Direct extraction from the observed pattern in the HTML source
    if not events:
        log.debug("Trying Approach 3: Direct extraction from HTML pattern")
        # Based on the example HTML, events might be structured with ### titles and date info below

        # Find all h3 elements with titles that might be events
        heading_elements = soup.find_all(["h3", "h2", "h4"])

        for heading in heading_elements:
            try:
                title = heading.text.strip()
                if not title or title in [e["title"] for e in events]:
                    continue

                # Look for date information in nearby elements
                date_text = ""
                # find_all over h2/h3/h4 headings always yields nested tags (only the
                # soup root has no parent); if that invariant ever broke, the broad
                # except below still catches the AttributeError — cast is typing-only.
                parent = cast(Tag, heading.parent)

                # Check for date text in siblings
                for sibling in list(parent.children):
                    if sibling != heading and hasattr(sibling, "text") and isinstance(sibling.text, str):
                        sibling_text = sibling.text.strip()
                        if "Del" in sibling_text or "al" in sibling_text or _has_valid_year(sibling_text):
                            date_text = sibling_text
                            break

                # If no date found, look for a date in the parent text
                if not date_text and hasattr(parent, "text"):
                    parent_text = parent.text
                    date_parts = [part for part in parent_text.split("\n") if "Del" in part or "al" in part or _has_valid_year(part)]
                    if date_parts:
                        date_text = date_parts[0].strip()

                # Get URL if there's a link
                event_url = ""
                link = heading.find("a") or parent.find("a")
                if link:
                    event_url = href_str(link)
                    if event_url and not event_url.startswith("http"):
                        event_url = f"{BASE_URL}{event_url}"

                # Try to determine category
                category = ""
                category_keywords = [
                    "exposición",
                    "música",
                    "gastronomía",
                    "espectáculo",
                    "deporte",
                    "naturaleza",
                    "fiestas",
                    "festival",
                ]

                for keyword in category_keywords:
                    if keyword in parent.get_text().lower():
                        category = keyword
                        break

                # Extract description
                description = ""
                desc_element = parent.find("p")
                if desc_element:
                    description = desc_element.text.strip()

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
                log.debug(f"Approach 3: Extracted event: {title}")
            except Exception as e:  # broad by design: BeautifulSoup DOM extraction from messy external HTML
                log.error(f"Error in Approach 3 parsing event: {e!s}")
                continue

    log.info(f"Retrieved {len(events)} events from Valencia website for {date}")
    return events
