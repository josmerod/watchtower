import json
import os
import sys
import time
from datetime import datetime
from typing import Any

import requests
from bs4 import BeautifulSoup

# Add the project root to the path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("ValenciaEventsETL")


def get_current_and_next_month():
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


def get_valencia_events(
    date: str, max_retries: int = 3, retry_delay: int = 5
) -> list[dict[str, Any]]:
    """Fetches events from the Valencia tourism website for a specific month.

    Args:
        date: Month in YYYY-MM format
        max_retries: Maximum number of retry attempts on connection failure
        retry_delay: Delay in seconds between retry attempts

    Returns:
        List of event dictionaries
    """
    url = f"https://www.visitvalencia.com/agenda-valencia?date={date}"

    logger.info(f"Fetching events from {url}")

    for attempt in range(max_retries):
        try:
            # Send GET request to the webpage with increased timeout
            response = requests.get(url, timeout=30)
            response.raise_for_status()  # Raise exception for HTTP errors

            # Parse HTML content
            logger.debug("Parsing HTML content")
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

            logger.debug(f"Approach 1: Found {len(event_blocks)} event blocks")

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
                    url = link.get("href", "") if link else ""
                    if url and not url.startswith("http"):
                        url = f"https://www.visitvalencia.com{url}"

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
                                "url": url,
                                "date_text": date_text,
                                "category": category,
                                "description": description,
                                "source": "visitvalencia.com",
                            }
                        )
                        logger.debug(f"Approach 1: Extracted event: {title}")
                except Exception as e:
                    logger.error(f"Error in Approach 1 parsing event: {e!s}")
                    continue

            # APPROACH 2: Look for specific event pattern from the example
            if not events:
                logger.debug("Trying Approach 2: Looking for specific event patterns")
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

                logger.debug(
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
                        url = ""
                        link = entry.find("a") or (
                            entry.parent.find("a") if entry.parent else None
                        )
                        if link:
                            url = link.get("href", "")
                            if url and not url.startswith("http"):
                                url = f"https://www.visitvalencia.com{url}"

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
                                    "url": url,
                                    "date_text": date_text,
                                    "category": category,
                                    "description": description,
                                    "source": "visitvalencia.com",
                                }
                            )
                            logger.debug(f"Approach 2: Extracted event: {title}")
                    except Exception as e:
                        logger.error(f"Error in Approach 2 parsing event: {e!s}")
                        continue

            # APPROACH 3: Direct extraction from the observed pattern in the HTML source
            if not events:
                logger.debug("Trying Approach 3: Direct extraction from HTML pattern")
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
                        url = ""
                        link = heading.find("a") or parent.find("a")
                        if link:
                            url = link.get("href", "")
                            if url and not url.startswith("http"):
                                url = f"https://www.visitvalencia.com{url}"

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
                                "url": url,
                                "date_text": date_text,
                                "category": category,
                                "description": description,
                                "source": "visitvalencia.com",
                            }
                        )
                        logger.debug(f"Approach 3: Extracted event: {title}")
                    except Exception as e:
                        logger.error(f"Error in Approach 3 parsing event: {e!s}")
                        continue

            logger.info(
                f"Retrieved {len(events)} events from Valencia website for {date}"
            )
            return events

        except requests.exceptions.RequestException as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e!s}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(
                    f"Error fetching data from Valencia website after {max_retries} attempts: {e!s}"
                )
                return []


def process_valencia_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Process and transform Valencia events into a standardized format.

    Args:
        events: List of raw event dictionaries from the Valencia website

    Returns:
        List of processed event dictionaries
    """
    logger.info(f"Processing {len(events)} Valencia events")
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
            logger.debug(f"Processed event: {processed_event['title']}")

        except Exception as e:
            logger.error(f"Error processing event: {e!s}")
            continue

    logger.info(f"Successfully processed {len(processed_events)} events")
    return processed_events


def remove_duplicates(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate events based on title, merging data to create more complete records.

    Args:
        events: List of event dictionaries

    Returns:
        List of unique event dictionaries with merged data
    """
    logger.info(f"Removing duplicates from {len(events)} events")

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

    logger.info(f"Removed {len(events) - len(unique_events)} duplicate events")
    return unique_events


def main():
    """Main function to fetch and process Valencia events."""
    logger.info("Starting Valencia events ETL process")
    try:
        # Ensure output directory exists
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data/valencia_events")

        # Create directories manually if they don't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Also try with the utility function
        ensure_directories(["data/valencia_events"])

        # Get current and next month
        current_month, next_month = get_current_and_next_month()
        logger.info(f"Fetching events for {current_month} and {next_month}")

        # Get events for current month
        current_month_events = get_valencia_events(current_month)

        # Get events for next month
        next_month_events = get_valencia_events(next_month)

        # Combine events from both months
        all_events = current_month_events + next_month_events

        if not all_events:
            logger.warning("No events retrieved, ETL process cannot continue")
            return

        # Process the events
        processed_events = process_valencia_events(all_events)

        # Remove duplicates
        unique_events = remove_duplicates(processed_events)

        # Save to JSON file
        output_file = os.path.join(output_dir, "valencia_events.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(unique_events, f, indent=2, ensure_ascii=False)
        logger.debug(f"Saved JSON data to {output_file}")

        # Also save as CSV for easier viewing
        csv_file = os.path.join(output_dir, "valencia_events.csv")
        import pandas as pd

        pd.DataFrame(unique_events).to_csv(csv_file, index=False, encoding="utf-8")
        logger.debug(f"Saved CSV data to {csv_file}")

        logger.info(
            f"Saved {len(unique_events)} processed events to {output_file} and {csv_file}"
        )

    except Exception as e:
        logger.error(f"Error in Valencia events ETL process: {e!s}", exc_info=True)


if __name__ == "__main__":
    logger.info("Valencia events ETL script started")
    # Run the main function
    main()
    logger.info("Valencia events ETL script completed")
