"""Simple Valencia Events ETL - Clean implementation."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup


class SimpleValenciaEventsETL:
    """Simple ETL for Valencia events from visitvalencia.com."""

    def __init__(self):
        self.output_dir = Path("data/valencia_events")

    def get_months_to_fetch(self) -> list[str]:
        """Get current month and next two months in YYYY-MM format."""
        now = datetime.now()
        months = []

        # Current month
        current_month = f"{now.year}-{now.month:02d}"
        months.append(current_month)

        # Next month
        if now.month == 12:
            next_month = f"{now.year + 1}-01"
        else:
            next_month = f"{now.year}-{now.month + 1:02d}"
        months.append(next_month)

        # Month after next
        if now.month == 11:
            next_next_month = f"{now.year + 1}-01"
        elif now.month == 12:
            next_next_month = f"{now.year + 1}-02"
        else:
            next_next_month = f"{now.year}-{now.month + 2:02d}"
        months.append(next_next_month)

        print(f"Fetching events for months: {months}")
        return months

    def fetch_events_for_month(self, month: str) -> list[dict[str, Any]]:
        """Fetch events for a specific month from visitvalencia.com."""
        url = f"https://www.visitvalencia.com/agenda-valencia?date={month}"
        print(f"Fetching events from {url}")

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            return []

        soup = BeautifulSoup(response.content, "html.parser")
        events = []

        # Look for event cards - based on the HTML structure
        event_cards = soup.find_all("div", class_=lambda x: x and "event-card" in str(x).lower())

        if not event_cards:
            # Fallback: look for any div with event-like content
            event_cards = soup.find_all(
                "div",
                class_=lambda x: x and any(term in str(x).lower() for term in ["event", "card", "evento"]),
            )

        print(f"Found {len(event_cards)} potential event cards")

        for card in event_cards:
            try:
                # Extract title - look for h2, h3, h4
                title_element = card.find(["h2", "h3", "h4"])
                title = title_element.text.strip() if title_element else ""

                if not title:
                    continue

                # Extract date - look for date patterns
                date_text = ""
                date_element = card.find(string=lambda t: t and isinstance(t, str) and ("Del" in t or "al" in t or re.search(r"\d{1,2}/\d{1,2}/\d{4}", t)))

                if date_element:
                    date_text = date_element.strip()

                # Extract URL
                link = card.find("a")
                event_url = ""
                if link and link.get("href"):
                    href = link["href"]
                    if href.startswith("/"):
                        event_url = f"https://www.visitvalencia.com{href}"
                    elif href.startswith("http"):
                        event_url = href

                # Extract description
                desc_element = card.find("p")
                description = desc_element.text.strip() if desc_element else ""

                # Determine category
                category = "general"
                title_lower = title.lower()
                if any(word in title_lower for word in ["exposición", "exposicion"]):
                    category = "exposición"
                elif any(word in title_lower for word in ["concierto", "música", "music"]):
                    category = "música"
                elif any(word in title_lower for word in ["festival"]):
                    category = "festival"
                elif any(word in title_lower for word in ["teatro", "espectáculo"]):
                    category = "espectáculo"
                elif any(word in title_lower for word in ["deporte", "sports"]):
                    category = "deporte"

                if title:
                    event = {
                        "title": title,
                        "url": event_url,
                        "date_text": date_text,
                        "category": category,
                        "description": description,
                        "source": "visitvalencia.com",
                        "month": month,
                    }
                    events.append(event)
                    print(f"Extracted event: {title[:50]}...")

            except Exception as e:
                print(f"Error parsing event card: {e}")
                continue

        print(f"Found {len(events)} events for month {month}")
        return events

    def extract(self) -> list[dict]:
        """Extract events from visitvalencia.com for current and next two months."""
        all_events = []
        months = self.get_months_to_fetch()

        for month in months:
            try:
                month_events = self.fetch_events_for_month(month)
                all_events.extend(month_events)
            except Exception as e:
                print(f"Failed to fetch events for {month}: {e}")

        print(f"Total events extracted: {len(all_events)}")
        return all_events

    def process_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Process and clean the events data."""
        processed_events = []

        for event in events:
            try:
                # Parse dates from date_text
                date_text = event.get("date_text", "")
                start_date = ""
                end_date = ""

                # Pattern: "Del DD/MM/YYYY al DD/MM/YYYY"
                del_al_pattern = re.search(
                    r"Del\s+(\d{1,2}/\d{1,2}/\d{4})\s*al\s+(\d{1,2}/\d{1,2}/\d{4})",
                    date_text,
                    re.IGNORECASE,
                )
                if del_al_pattern:
                    start_date = del_al_pattern.group(1)
                    end_date = del_al_pattern.group(2)

                # Pattern: "Del DD/MM/YYYY"
                elif re.search(r"Del\s+(\d{1,2}/\d{1,2}/\d{4})", date_text, re.IGNORECASE):
                    del_pattern = re.search(r"Del\s+(\d{1,2}/\d{1,2}/\d{4})", date_text, re.IGNORECASE)
                    start_date = del_pattern.group(1) if del_pattern else ""

                processed_event = {
                    "title": event.get("title", "").strip(),
                    "url": event.get("url", ""),
                    "source": event.get("source", "visitvalencia.com"),
                    "category": event.get("category", "general"),
                    "description": event.get("description", "").strip(),
                    "start_date": start_date,
                    "end_date": end_date,
                    "date_text": date_text,
                    "metadata": {
                        "month": event.get("month"),
                        "processed_at": datetime.now().isoformat(),
                    },
                }

                processed_events.append(processed_event)

            except Exception as e:
                print(f"Error processing event: {e}")
                continue

        return processed_events

    def remove_duplicates(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate events based on title."""
        seen_titles = set()
        unique_events = []

        for event in events:
            title = event.get("title", "")
            if title not in seen_titles:
                seen_titles.add(title)
                unique_events.append(event)

        print(f"Removed {len(events) - len(unique_events)} duplicate events")
        return unique_events

    def transform(self, data: list[dict]) -> list[dict]:
        """Transform events data."""
        if not data:
            return []

        processed_events = self.process_events(data)
        unique_events = self.remove_duplicates(processed_events)

        return unique_events

    def load(self, data: list[dict]) -> None:
        """Save events to JSON file."""
        if not data:
            print("No data to load")
            return

        # Save JSON
        json_file = self.output_dir / "valencia_events.json"
        json_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        print(f"Saved {len(data)} events to {json_file}")

    def run(self) -> dict:
        """Run the complete ETL process."""
        print("Starting Valencia events ETL...")

        # Extract
        raw_events = self.extract()

        # Transform
        processed_events = self.transform(raw_events)

        # Load
        self.load(processed_events)

        return {
            "records_extracted": len(raw_events),
            "records_transformed": len(processed_events),
            "records_loaded": len(processed_events),
            "success": True,
        }


def main():
    """Main function to run Valencia events ETL."""
    etl = SimpleValenciaEventsETL()
    try:
        metrics = etl.run()
        print(f"ETL completed successfully. Metrics: {metrics}")
    except Exception as e:
        print(f"ETL failed: {e}")
        raise


if __name__ == "__main__":
    main()
