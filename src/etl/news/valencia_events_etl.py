"""Valencia Events ETL - Refactored to use BaseETL framework."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from src.etl.base import BaseETL
from src.models.base import TimestampedModel

# Dynamic year matching — prevents the recurring "hardcoded year" bug.
_NOW = datetime.now()
_VALID_YEARS = {str(_NOW.year), str(_NOW.year + 1), str(_NOW.year - 1)}


def _has_valid_year(text: str) -> bool:
    """Check if text contains a plausible event year (current, next, or prev)."""
    return any(y in text for y in _VALID_YEARS)


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
        response = requests.get(url, timeout=30)
        response.raise_for_status()  # Raise exception for HTTP errors

        # Parse HTML content
        self.logger.debug("Parsing HTML content")
        soup = BeautifulSoup(response.content, "html.parser")

        # Find all event items based on the provided HTML structure
        # The events appear to be in a list with each event having h3 headers
        events = []

        # APPROACH 1: Based on the example HTML, events seem to be contained in
        # elements with specific text in their titles
        event_blocks = soup.find_all(
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
            except Exception as e:
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
                except Exception as e:
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
                except Exception as e:
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

            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            events = []

            # Look for event cards in Meetup's search results
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

                except Exception as e:
                    self.logger.error(f"Error parsing Meetup event: {e}")
                    continue

            self.logger.info(f"Found {len(events)} events from Meetup.com")
            return events

        except Exception as e:
            self.logger.error(f"Error fetching Meetup events: {e}")
            return []

    def get_eventbrite_events(self) -> list[dict]:
        """Fetch events from Eventbrite for Valencia."""
        try:
            self.logger.info("Fetching events from Eventbrite")

            # Eventbrite API would require API key, so we'll use web scraping
            url = "https://www.eventbrite.es/d/spain--valencia/all-events/"

            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

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

                except Exception as e:
                    self.logger.error(f"Error parsing Eventbrite event: {e}")
                    continue

            self.logger.info(f"Found {len(events)} events from Eventbrite")
            return events

        except Exception as e:
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
        except Exception as e:
            self.logger.error(f"Failed to fetch visitvalencia.com events: {e}")

        # 2. Get events from Meetup.com
        try:
            meetup_events = self.get_meetup_events()
            all_events.extend(meetup_events)
            self.logger.info(f"Retrieved {len(meetup_events)} events from meetup.com")
        except Exception as e:
            self.logger.error(f"Failed to fetch meetup.com events: {e}")

        # 3. Get events from Eventbrite
        try:
            eventbrite_events = self.get_eventbrite_events()
            all_events.extend(eventbrite_events)
            self.logger.info(f"Retrieved {len(eventbrite_events)} events from eventbrite.com")
        except Exception as e:
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
                # Parse dates from text if available
                date_info = event.get("date_text", "")
                start_date = ""
                end_date = ""

                # Enhanced date parsing for Spanish format

                # Pattern 1: "Del DD/MM/YYYY al DD/MM/YYYY" (with optional extra spaces)
                del_al_pattern = re.search(
                    r"Del\s+(\d{1,2}/\d{1,2}/\d{4})\s*al\s+(\d{1,2}/\d{1,2}/\d{4})",
                    date_info,
                    re.IGNORECASE,
                )
                if del_al_pattern:
                    start_date = del_al_pattern.group(1)
                    end_date = del_al_pattern.group(2)
                # Pattern 2: "Del DD/MM/YYYY" (single date)
                elif re.search(r"Del\s+(\d{1,2}/\d{1,2}/\d{4})", date_info, re.IGNORECASE):
                    del_pattern = re.search(r"Del\s+(\d{1,2}/\d{1,2}/\d{4})", date_info, re.IGNORECASE)
                    start_date = del_pattern.group(1) if del_pattern else ""
                # Pattern 3: "Fecha: Del DD/MM/YYYY al DD/MM/YYYY" (with "Fecha:" prefix)
                elif re.search(
                    r"Fecha:\s*Del\s+(\d{1,2}/\d{1,2}/\d{4})\s*al\s+(\d{1,2}/\d{1,2}/\d{4})",
                    date_info,
                    re.IGNORECASE,
                ):
                    fecha_pattern = re.search(
                        r"Fecha:\s*Del\s+(\d{1,2}/\d{1,2}/\d{4})\s*al\s+(\d{1,2}/\d{1,2}/\d{4})",
                        date_info,
                        re.IGNORECASE,
                    )
                    start_date = fecha_pattern.group(1) if fecha_pattern else ""
                    end_date = fecha_pattern.group(2) if fecha_pattern else ""
                # Pattern 4: Look for any dates in YYYY-MM-DD or DD/MM/YYYY format
                elif re.search(r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}", date_info):
                    date_matches = re.findall(r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}", date_info)
                    if date_matches:
                        start_date = date_matches[0]
                        if len(date_matches) > 1:
                            end_date = date_matches[1]
                # Pattern 5: Look for month names and years
                elif re.search(
                    r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)",
                    date_info,
                    re.IGNORECASE,
                ):
                    # Keep the original text if it contains month names
                    pass

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

                processed_event = {
                    "title": title,
                    "url": event.get("url", ""),
                    "source": event.get("source", "visitvalencia.com"),
                    "category": category,
                    "description": description,
                    "start_date": start_date,
                    "end_date": end_date,
                    "date_text": date_info,
                    "metadata": {
                        "api_source": "valencia_scraper",
                        "processed_at": datetime.now().isoformat(),
                    },
                }
                processed_events.append(processed_event)
                self.logger.debug(f"Processed event: {processed_event['title']}")

            except Exception as e:
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
            except Exception as e:
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
    except Exception as e:
        etl.logger.error(f"ETL failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
