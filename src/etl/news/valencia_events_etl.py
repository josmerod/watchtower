"""Valencia Events ETL - Refactored to use BaseETL framework."""

import json
import re
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from src.constants.etl import SCRAPER_DEFAULT_USER_AGENT
from src.etl.base import BaseETL
from src.models.base import TimestampedModel

# Dynamic year matching — prevents the recurring "hardcoded year" bug.
_NOW = datetime.now()
_VALID_YEARS = {str(_NOW.year), str(_NOW.year + 1), str(_NOW.year - 1)}

# Date normalisation helpers ---------------------------------------------------
#
# Each source exposes dates differently: visitvalencia cards print Spanish text
# like "17/08/2026 - 30/08/2026", Eventbrite embeds a schema.org ItemList with
# ISO startDate/endDate per item, and Meetup embeds a JSON-LD array of Events
# with full ISO timestamps ("2026-08-28T18:30:00.000Z"). Everything is
# normalised to plain ISO calendar dates (YYYY-MM-DD) — the format the
# dashboard tab's _parse_event_date and the .ics exporter accept directly.

_ISO_DATE_RE = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
_ES_DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")


def _has_valid_year(text: str) -> bool:
    """Check if text contains a plausible event year (current, next, or prev)."""
    return any(y in text for y in _VALID_YEARS)


def _to_iso_date(raw: Any) -> str:
    """Normalise a raw date value to an ISO calendar date (YYYY-MM-DD).

    Accepts Spanish DD/MM/YYYY, ISO YYYY-MM-DD and full ISO timestamps;
    timezone suffixes (``+02:00``, ``Z``) and bracketed zone names are
    ignored, so timed events collapse to their calendar date.

    Args:
        raw: Raw date value; non-strings are coerced, falsy values yield "".

    Returns:
        YYYY-MM-DD string, or "" when no plausible date can be extracted.
    """
    text = str(raw or "").strip()
    if not text:
        return ""
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


def _parse_dates_from_text(text: Any) -> tuple[str, str]:
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
        iso = _to_iso_date(token)
        if iso:
            tokens.append(iso)
    if not tokens:
        return "", ""
    # Deduplicate preserving order: a repeated identical date is a one-day
    # event, not a range.
    unique = list(dict.fromkeys(tokens))
    return unique[0], unique[1] if len(unique) > 1 else ""


def _iter_jsonld_items(soup: BeautifulSoup) -> Iterator[dict[str, Any]]:
    """Yield every object embedded in the page's application/ld+json blocks.

    Handles blocks holding a single object, an array of objects, or an object
    with a @graph. Malformed blocks are skipped silently.

    Args:
        soup: Parsed page.

    Yields:
        Individual schema.org node dictionaries.
    """
    for block in soup.find_all("script", type="application/ld+json"):
        raw = block.string or block.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        queue = data if isinstance(data, list) else [data]
        for node in queue:
            if not isinstance(node, dict):
                continue
            graph = node.get("@graph")
            if isinstance(graph, list):
                yield from (item for item in graph if isinstance(item, dict))
            else:
                yield node


def _jsonld_location(node: dict[str, Any]) -> str:
    """Best-effort human-readable location from a schema.org event node.

    Args:
        node: schema.org Event (or ItemList item) dictionary.

    Returns:
        "street, city" (or whichever parts exist), "" when no location.
    """
    location = node.get("location")
    if isinstance(location, str):
        return location
    if not isinstance(location, dict):
        return ""
    address = location.get("address")
    if isinstance(address, str):
        return address
    if isinstance(address, dict):
        parts = [address.get("streetAddress"), address.get("addressLocality")]
        return ", ".join(str(part) for part in parts if part)
    return str(location.get("name") or "")


class ValenciaEvent(TimestampedModel):
    """Model for Valencia events."""

    title: str
    url: str = ""
    source: str = "visitvalencia.com"
    category: str = ""
    description: str = ""
    start_date: str = ""
    end_date: str = ""
    date_text: str = ""
    metadata: dict[str, Any] = {}


class ValenciaEventsETL(BaseETL[dict, ValenciaEvent]):
    """ETL for Valencia events from multiple sources."""

    def __init__(self):
        super().__init__(
            name="valencia_events",
            description="Extract Valencia events from multiple sources (visitvalencia.com, meetup.com, eventbrite)",
            max_retries=3,
            retry_delay=5,
        )
        # Override output directory to write directly to main data directory
        self.output_dir = Path("data/valencia_events")

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
        url = f"https://www.visitvalencia.com/agenda-valencia?date={date}"
        self.logger.info(f"Fetching events from {url}")

        # Send GET request to the webpage with increased timeout
        response = requests.get(url, headers={"User-Agent": SCRAPER_DEFAULT_USER_AGENT}, timeout=30)
        response.raise_for_status()  # Raise exception for HTTP errors

        # Parse HTML content
        self.logger.debug("Parsing HTML content")
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
                start_date, end_date = _parse_dates_from_text(date_text)

                link = card.select_one("a.standard-card__link") or card.find("a", href=True)
                event_url = ""
                if link is not None:
                    href = link.get("href", "")
                    if href:
                        event_url = href if href.startswith("http") else f"https://www.visitvalencia.com{href}"

                events.append(
                    {
                        "title": title,
                        "url": event_url,
                        "date_text": date_text,
                        "start_date": start_date,
                        "end_date": end_date,
                        "category": "",
                        "description": "",
                        "source": "visitvalencia.com",
                    }
                )
            except Exception as e:  # broad by design: BeautifulSoup DOM extraction from messy external HTML
                self.logger.error(f"Error parsing standard-card event: {e!s}")
                continue

        self.logger.debug(f"Approach 0: extracted {len(events)} events from standard cards")

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

        self.logger.debug(f"Approach 1: Found {len(event_blocks)} event blocks")

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
                event_url = link.get("href", "") if link else ""
                if event_url and not event_url.startswith("http"):
                    event_url = f"https://www.visitvalencia.com{event_url}"

                # Extract category
                category = ""
                category_tags = block.find_all(["span", "div"], class_=True)
                for tag in category_tags:
                    if tag.get("class") and isinstance(tag.get("class"), list):
                        class_text = " ".join(tag.get("class"))
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
                            "source": "visitvalencia.com",
                        }
                    )
                    self.logger.debug(f"Approach 1: Extracted event: {title}")
            except Exception as e:  # broad by design: BeautifulSoup DOM extraction from messy external HTML
                self.logger.error(f"Error in Approach 1 parsing event: {e!s}")
                continue

        # APPROACH 2: Look for specific event pattern from the example
        if not events:
            self.logger.debug("Trying Approach 2: Looking for specific event patterns")
            # Based on the provided HTML, events might be listed with a specific structure
            event_entries = []

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

            self.logger.debug(f"Approach 2: Found {len(event_entries)} potential event entries")

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
                        event_url = link.get("href", "")
                        if event_url and not event_url.startswith("http"):
                            event_url = f"https://www.visitvalencia.com{event_url}"

                    # Extract category if possible
                    category = ""
                    if entry.get("class"):
                        class_text = " ".join(entry.get("class") if isinstance(entry.get("class"), list) else [entry.get("class")])
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
                                "source": "visitvalencia.com",
                            }
                        )
                        self.logger.debug(f"Approach 2: Extracted event: {title}")
                except Exception as e:  # broad by design: BeautifulSoup DOM extraction from messy external HTML
                    self.logger.error(f"Error in Approach 2 parsing event: {e!s}")
                    continue

        # APPROACH 3: Direct extraction from the observed pattern in the HTML source
        if not events:
            self.logger.debug("Trying Approach 3: Direct extraction from HTML pattern")
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
                    parent = heading.parent

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
                        event_url = link.get("href", "")
                        if event_url and not event_url.startswith("http"):
                            event_url = f"https://www.visitvalencia.com{event_url}"

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
                            "source": "visitvalencia.com",
                        }
                    )
                    self.logger.debug(f"Approach 3: Extracted event: {title}")
                except Exception as e:  # broad by design: BeautifulSoup DOM extraction from messy external HTML
                    self.logger.error(f"Error in Approach 3 parsing event: {e!s}")
                    continue

        self.logger.info(f"Retrieved {len(events)} events from Valencia website for {date}")
        return events

    def get_meetup_events(self) -> list[dict]:
        """Fetch events from Meetup.com for Valencia."""
        try:
            self.logger.info("Fetching events from Meetup.com")

            # Note: Meetup.com requires API key for full access
            # For now, we'll use web scraping approach
            url = "https://www.meetup.com/es-ES/find/?location=es--Valencia&source=EVENTS"

            headers = {"User-Agent": SCRAPER_DEFAULT_USER_AGENT}

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Primary: Meetup embeds a JSON-LD array of schema.org Events with
            # full ISO startDate/endDate (UTC) plus name/url/description. The
            # interactive event cards render client-side, so the static-HTML
            # card scraping further below only acts as a fallback.
            jsonld_events: list[dict[str, Any]] = []
            for node in _iter_jsonld_items(soup):
                if node.get("@type") != "Event" or not str(node.get("name") or "").strip():
                    continue
                title = str(node.get("name")).strip()
                jsonld_events.append(
                    {
                        "title": title,
                        "url": str(node.get("url") or ""),
                        "date_text": str(node.get("startDate") or ""),
                        "start_date": _to_iso_date(node.get("startDate")),
                        "end_date": _to_iso_date(node.get("endDate")),
                        "category": "meetup",
                        "description": str(node.get("description") or "").strip(),
                        "source": "meetup.com",
                        "metadata": {"location": _jsonld_location(node)},
                    }
                )

            if jsonld_events:
                self.logger.info(f"Found {len(jsonld_events)} events from Meetup.com JSON-LD")
                return jsonld_events[:20]

            events = []

            # Fallback: look for event cards in Meetup's search results
            event_cards = soup.find_all("div", {"data-testid": "event-card"})

            for card in event_cards[:20]:  # Limit to first 20 events
                try:
                    title_element = card.find("h3") or card.find("h2")
                    title = title_element.text.strip() if title_element else ""

                    if not title:
                        continue

                    # Extract date information
                    date_element = card.find("time") or card.find(
                        "span",
                        string=lambda t: t and ("202" in t or "ene" in t.lower() or "feb" in t.lower()),
                    )
                    date_text = date_element.get("datetime", "") if date_element else ""
                    if not date_text and date_element:
                        date_text = date_element.text.strip()

                    # Extract URL
                    link = card.find("a")
                    event_url = ""
                    if link and "href" in link.attrs:
                        href = link["href"]
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
                                "source": "meetup.com",
                            }
                        )

                except Exception as e:  # broad by design: BeautifulSoup DOM extraction from messy external HTML
                    self.logger.error(f"Error parsing Meetup event: {e}")
                    continue

            self.logger.info(f"Found {len(events)} events from Meetup.com")
            return events

        except Exception as e:  # broad by design: whole source fetch wrapper (network + scraping)
            self.logger.error(f"Error fetching Meetup events: {e}")
            return []

    def get_eventbrite_events(self) -> list[dict]:
        """Fetch events from Eventbrite for Valencia."""
        try:
            self.logger.info("Fetching events from Eventbrite")

            # Eventbrite API would require API key, so we'll use web scraping
            url = "https://www.eventbrite.es/d/spain--valencia/all-events/"

            headers = {"User-Agent": SCRAPER_DEFAULT_USER_AGENT}

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Primary: Eventbrite embeds a schema.org ItemList in JSON-LD whose
            # ListItem entries carry ISO startDate/endDate, name, url and
            # location per event — far more reliable than the JS-rendered cards.
            jsonld_events: list[dict[str, Any]] = []
            for node in _iter_jsonld_items(soup):
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
                    jsonld_events.append(
                        {
                            "title": title,
                            "url": str(item.get("url") or ""),
                            "date_text": str(item.get("startDate") or ""),
                            "start_date": _to_iso_date(item.get("startDate")),
                            "end_date": _to_iso_date(item.get("endDate")),
                            "category": category,
                            "description": str(item.get("description") or "").strip(),
                            "source": "eventbrite.com",
                            "metadata": {"location": _jsonld_location(item)},
                        }
                    )
                if jsonld_events:
                    break  # only the first ItemList matters

            if jsonld_events:
                self.logger.info(f"Found {len(jsonld_events)} events from Eventbrite JSON-LD")
                return jsonld_events[:15]

            events = []

            # Look for event cards
            event_cards = soup.find_all("div", class_=lambda x: x and "event-card" in x.lower())

            # If that doesn't work, look for event listings
            if not event_cards:
                event_cards = soup.find_all(
                    "div",
                    class_=lambda x: x and any(term in x.lower() for term in ["event", "card", "listing"]),
                )

            for card in event_cards[:15]:  # Limit to first 15 events
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
                        href = link["href"]
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
                                "source": "eventbrite.com",
                            }
                        )

                except Exception as e:  # broad by design: BeautifulSoup DOM extraction from messy external HTML
                    self.logger.error(f"Error parsing Eventbrite event: {e}")
                    continue

            self.logger.info(f"Found {len(events)} events from Eventbrite")
            return events

        except Exception as e:  # broad by design: whole source fetch wrapper (network + scraping)
            self.logger.error(f"Error fetching Eventbrite events: {e}")
            return []

    def extract(self) -> list[dict]:
        """Extract events from multiple sources for Valencia."""
        self.logger.info("Starting multi-source Valencia events extraction")

        all_events = []

        # 1. Get events from visitvalencia.com (current and next month)
        try:
            current_month, next_month = self.get_current_and_next_month()
            self.logger.info(f"Fetching events for {current_month} and {next_month}")

            # Get events for current month
            current_month_events = self.get_valencia_events(current_month)
            all_events.extend(current_month_events)

            # Get events for next month
            next_month_events = self.get_valencia_events(next_month)
            all_events.extend(next_month_events)

            self.logger.info(f"Retrieved {len(current_month_events) + len(next_month_events)} events from visitvalencia.com")
        except Exception as e:  # broad by design: per-source fetch wrapper (network + scraping)
            self.logger.error(f"Failed to fetch visitvalencia.com events: {e}")

        # 2. Get events from Meetup.com
        try:
            meetup_events = self.get_meetup_events()
            all_events.extend(meetup_events)
            self.logger.info(f"Retrieved {len(meetup_events)} events from meetup.com")
        except Exception as e:  # broad by design: per-source fetch wrapper (network + scraping)
            self.logger.error(f"Failed to fetch meetup.com events: {e}")

        # 3. Get events from Eventbrite
        try:
            eventbrite_events = self.get_eventbrite_events()
            all_events.extend(eventbrite_events)
            self.logger.info(f"Retrieved {len(eventbrite_events)} events from eventbrite.com")
        except Exception as e:  # broad by design: per-source fetch wrapper (network + scraping)
            self.logger.error(f"Failed to fetch eventbrite.com events: {e}")

        self.logger.info(f"Total events collected from all sources: {len(all_events)}")
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

                # Clean up titles (sometimes they contain the event type)
                title = event.get("title", "").strip()

                # Enhanced category and description extraction
                category = event.get("category", "").strip()
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
                        if keyword in lower_title:
                            category = cat
                            break

                # Try to extract category from description if still not found
                if not category and description:
                    lower_desc = description.lower()
                    for keyword, cat in category_keywords.items():
                        if keyword in lower_desc:
                            category = cat
                            break

                # Enhanced description extraction - if description is empty, use title context
                if not description and title:
                    # Extract meaningful description from title if it's long enough
                    if len(title) > 30:
                        # Look for descriptive parts after common prefixes
                        desc_parts = title.split(":")
                        if len(desc_parts) > 1:
                            description = desc_parts[1].strip()
                        else:
                            desc_parts = title.split("-")
                            if len(desc_parts) > 1:
                                description = desc_parts[1].strip()

                # Final fallback - ensure we have some description
                if not description:
                    description = title

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
                    "metadata": metadata,
                }
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
        event_groups = {}
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

    def transform(self, data: list[dict]) -> list[ValenciaEvent]:
        """Transform raw events into structured models."""
        if not data:
            return []

        # Process events
        processed_events = self.process_valencia_events(data)

        # Remove duplicates
        unique_events = self.remove_duplicates(processed_events)

        # Convert to models
        models = []
        for event in unique_events:
            try:
                models.append(ValenciaEvent(**event))
            except (ValueError, TypeError) as e:
                self.logger.error(f"Failed to create model for event: {e}")
                continue

        return models

    def load(self, data: list[ValenciaEvent]) -> None:
        """Save events to JSON and CSV files."""
        if not data:
            self.logger.info("No data to load")
            return

        # Convert to dictionaries
        data_dicts = [event.model_dump() for event in data]

        # Save JSON
        json_file = self.output_dir / "valencia_events.json"
        json_file.write_text(
            json.dumps(data_dicts, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        self.logger.info(f"Saved {len(data_dicts)} events to {json_file}")

        # Save CSV
        try:
            import pandas as pd

            csv_file = self.output_dir / "valencia_events.csv"
            pd.DataFrame(data_dicts).to_csv(csv_file, index=False, encoding="utf-8")
            self.logger.info(f"Saved CSV to {csv_file}")
        except ImportError:
            self.logger.warning("Pandas not available, skipping CSV export")


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
