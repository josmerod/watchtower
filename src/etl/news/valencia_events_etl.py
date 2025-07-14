"""Valencia Events ETL - Refactored to use BaseETL framework."""

import json
import time
from datetime import datetime
from typing import Any, List

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel

from src.etl.base import BaseETL
from src.models.base import TimestampedModel


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
    """ETL for Valencia events from visitvalencia.com."""
    
    def __init__(self):
        super().__init__(
            name="valencia_events",
            description="Extract Valencia events from visitvalencia.com",
            max_retries=3,
            retry_delay=5
        )
    
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
            lambda tag: tag.name
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

        self.logger.debug(f"Approach 1: Found {len(event_blocks)} event blocks")

        for block in event_blocks:
            try:
                title_element = block.find(["h2", "h3"])
                title = title_element.text.strip() if title_element else ""

                # Extract date
                date_element = block.find(
                    string=lambda t: t
                    and isinstance(t, str)
                    and ("Del" in t or "al" in t or "2025" in t)
                )
                date_text = date_element.strip() if date_element else ""

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
                        if any(
                            c in class_text.lower()
                            for c in ["música", "exposición", "deporte"]
                        ):
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
            potential_entries = soup.find_all(
                class_=lambda x: x
                and isinstance(x, str)
                and (x.startswith("###") or "event" in x.lower())
            )

            # If that doesn't work, try a more general approach
            if not potential_entries:
                # Look for sections that likely contain event information
                potential_entries = soup.find_all(
                    lambda tag: tag.name in ["article", "div", "section"]
                    and tag.find(["h3", "h2", "h4"])
                )

            event_entries.extend(potential_entries)

            # Also try with HTML structure seen in the example
            event_items = soup.find_all(
                lambda tag: tag.name
                and tag.get_text()
                and (
                    "exposición" in tag.get_text().lower()
                    or "música" in tag.get_text().lower()
                    or "2025" in tag.get_text()
                )
            )

            event_entries.extend(event_items)

            self.logger.debug(
                f"Approach 2: Found {len(event_entries)} potential event entries"
            )

            for entry in event_entries:
                try:
                    # Extract title
                    title_element = entry.find(["h3", "h2", "h4"])
                    if not title_element and entry.name in ["h3", "h2", "h4"]:
                        title_element = entry

                    title = title_element.text.strip() if title_element else ""

                    # Extract date - look for date pattern
                    date_text = ""
                    date_element = entry.find(
                        string=lambda t: t
                        and isinstance(t, str)
                        and ("Del" in t or "al" in t or "2025" in t)
                    )

                    if date_element:
                        date_text = date_element.strip()
                    else:
                        # Try looking at sibling elements
                        next_sibling = entry.next_sibling
                        while next_sibling and not date_text:
                            if hasattr(next_sibling, "text") and isinstance(
                                next_sibling.text, str
                            ):
                                if (
                                    "Del" in next_sibling.text
                                    or "al" in next_sibling.text
                                    or "2025" in next_sibling.text
                                ):
                                    date_text = next_sibling.text.strip()
                            next_sibling = next_sibling.next_sibling

                    # Extract URL
                    event_url = ""
                    link = entry.find("a") or (
                        entry.parent.find("a") if entry.parent else None
                    )
                    if link:
                        event_url = link.get("href", "")
                        if event_url and not event_url.startswith("http"):
                            event_url = f"https://www.visitvalencia.com{event_url}"

                    # Extract category if possible
                    category = ""
                    if entry.get("class"):
                        class_text = " ".join(
                            entry.get("class")
                            if isinstance(entry.get("class"), list)
                            else [entry.get("class")]
                        )
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
                        if (
                            sibling != heading
                            and hasattr(sibling, "text")
                            and isinstance(sibling.text, str)
                        ):
                            sibling_text = sibling.text.strip()
                            if (
                                "Del" in sibling_text
                                or "al" in sibling_text
                                or "2025" in sibling_text
                            ):
                                date_text = sibling_text
                                break

                    # If no date found, look for a date in the parent text
                    if not date_text and hasattr(parent, "text"):
                        parent_text = parent.text
                        date_parts = [
                            part
                            for part in parent_text.split("\n")
                            if "Del" in part or "al" in part or "2025" in part
                        ]
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

        self.logger.info(
            f"Retrieved {len(events)} events from Valencia website for {date}"
        )
        return events

    def extract(self) -> List[dict]:
        """Extract events from Valencia website for current and next month."""
        # Get current and next month
        current_month, next_month = self.get_current_and_next_month()
        self.logger.info(f"Fetching events for {current_month} and {next_month}")
        
        all_events = []
        
        # Get events for current month
        try:
            current_month_events = self.get_valencia_events(current_month)
            all_events.extend(current_month_events)
        except Exception as e:
            self.logger.error(f"Failed to fetch current month events: {e}")
        
        # Get events for next month
        try:
            next_month_events = self.get_valencia_events(next_month)
            all_events.extend(next_month_events)
        except Exception as e:
            self.logger.error(f"Failed to fetch next month events: {e}")
        
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

                # Try multiple date formats
                if "Del" in date_info and "al" in date_info:
                    parts = date_info.split("al")
                    start_part = parts[0].replace("Del", "").strip()
                    end_part = parts[1].strip()
                    start_date = start_part
                    end_date = end_part
                elif "2025" in date_info:
                    # Try to extract date with 2025 year
                    date_parts = [
                        part.strip() for part in date_info.split() if "2025" in part
                    ]
                    if date_parts:
                        start_date = date_parts[0]
                        if len(date_parts) > 1:
                            end_date = date_parts[1]

                # Clean up titles (sometimes they contain the event type)
                title = event.get("title", "").strip()

                # If no category but it's in the description, use that
                category = event.get("category", "").strip()
                description = event.get("description", "").strip()

                if not category and description:
                    lower_desc = description.lower()
                    for cat in [
                        "exposición",
                        "música",
                        "gastronomía",
                        "espectáculo",
                        "deporte",
                        "naturaleza",
                        "fiestas",
                        "festival",
                    ]:
                        if cat in lower_desc:
                            category = cat
                            break

                # Sometimes description and category are swapped
                if not description and category and len(category) > 15:
                    description = category
                    category = ""

                    # Try to extract category from description
                    lower_desc = description.lower()
                    for cat in [
                        "exposición",
                        "música",
                        "gastronomía",
                        "espectáculo",
                        "deporte",
                        "naturaleza",
                        "fiestas",
                        "festival",
                    ]:
                        if cat in lower_desc:
                            category = cat
                            break

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
        for title, group in event_groups.items():
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

    def transform(self, data: List[dict]) -> List[ValenciaEvent]:
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
    
    def load(self, data: List[ValenciaEvent]) -> None:
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
            encoding="utf-8"
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