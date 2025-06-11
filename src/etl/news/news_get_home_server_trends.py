# src/etl/news/news_get_home_server_trends.py
import os
import json
import sys
import time
import csv
from datetime import datetime
import requests
import re
import hashlib
from typing import Dict, List, Any, Optional

# Add the project root to the path
from utils.logging import get_logger
from utils.file_system import ensure_directories, get_project_root
from models.home_server import HomeServerTrendItem # Assuming the model is created

logger = get_logger("HomeServerTrendsETL")

AWESOME_SELFHOSTED_URL = "https://raw.githubusercontent.com/awesome-selfhosted/awesome-selfhosted/master/README.md"
AWESOME_HOME_AUTOMATION_URL = "https://raw.githubusercontent.com/frenck/awesome-home-automation/main/README.md"

# Define categories of interest for awesome-selfhosted
AWESOME_SELFHOSTED_CATEGORIES = [
    "Media Streaming - Multimedia Streaming",
    "Internet of Things (IoT)",
    "File Transfer & Synchronization",
    "Personal Dashboards",
    "Self-hosting Solutions",
    "Analytics",
    "Automation"
]

# Define categories of interest for awesome-home-automation
# Example categories, actual ones will depend on the list's structure
HOME_AUTOMATION_CATEGORIES = [
    "Software Platforms", # Placeholder
    "Voice Assistants",   # Placeholder
    "Gateways and Hubs",  # Placeholder
    "DIY Solutions",      # Placeholder
    "Home Automation Software", # Example from actual list inspection (if possible)
    "Software",           # General category often found
    "Hubs and Gateways",  # Variation
    "Lighting",           # Common HA category
    "Climate Control",    # Common HA category
    "Security",           # Common HA category
    "Assistants"          # Common HA category
]


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Watchtower-ETL/1.0 (HomeServer Trends)',
        'Accept': 'text/plain',
    })
    return session

# Renamed and parameterized
def fetch_markdown_content(session: requests.Session, url: str, source_name_for_log: str) -> Optional[str]:
    logger.info(f"Fetching markdown from {url} for source: {source_name_for_log}")
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching markdown from {url} for source {source_name_for_log}: {e}")
        return None

def parse_markdown(markdown_content: str, target_categories: List[str], source_name: str) -> List[Dict[str, Any]]:
    logger.info(f"Parsing markdown content from source: {source_name}")
    items = []
    current_category = None

    # More flexible category regex (H2 or H3)
    category_regex = re.compile(r"^(?:##|###)\s+(.+)$", re.MULTILINE)
    # Regex to capture list items: - [Name](URL) - Description. `License` `Tag`
    # This regex is complex and might need refinement.
    # It tries to capture: name, url, description (until ` (backtick) or end of line),
    # and optionally license and other tags in backticks.
    item_regex = re.compile(
        r"^\s*-\s*\[([^]]+)\]\(([^)]+)\)\s*-\s*([^`\n]+(?:\s+[^`\n]+)*?)\s*" # Name, URL, Description
        r"(?:`([^`]+)`\s*)?"  # Optional License
        r"(?:`([^`]+)`\s*)?"  # Optional second Tag (e.g., Language/Docker)
        r"(?:`([^`]+)`\s*)?"  # Optional third Tag
        r".*$", # Ignore anything else on the line
        re.MULTILINE
    )

    for line in markdown_content.splitlines():
        cat_match = category_regex.match(line)
        if cat_match:
            category_name = cat_match.group(1).strip()
            # Clean up potential markdown formatting from category name (e.g., links)
            category_name = re.sub(r'\[([^]]+)\]\([^)]+\)', r'\1', category_name) # Remove links, keep text
            category_name = category_name.replace('`', '').strip() # Remove backticks

            if category_name in target_categories:
                current_category = category_name
                logger.debug(f"Source '{source_name}': Switched to category: {current_category}")
            else:
                # If the line was a header but not in target_categories, reset current_category
                current_category = None
            continue

        if current_category:
            item_match = item_regex.match(line)
            if item_match:
                name = item_match.group(1).strip()
                url = item_match.group(2).strip()
                description = item_match.group(3).strip().rstrip('.') # Remove trailing dots for consistency

                tags = []
                if item_match.group(4): tags.append(item_match.group(4).strip())
                if item_match.group(5): tags.append(item_match.group(5).strip())
                if item_match.group(6): tags.append(item_match.group(6).strip())

                item_id = hashlib.md5(f"{name}_{url}".encode('utf-8')).hexdigest()

                items.append({
                    "id": item_id,
                    "name": name,
                    "url": url,
                    "description": description,
                    "category": current_category,
                    "tags": tags if tags else None,
                    "source": source_name, # Ensure source is correctly attributed
                    "added_date": datetime.utcnow()
                })

    logger.info(f"Parsed {len(items)} items from source '{source_name}' from selected categories.")
    return items

def process_items(raw_items: List[Dict[str, Any]]) -> List[HomeServerTrendItem]:
    logger.info(f"Processing {len(raw_items)} raw items into HomeServerTrendItem model")
    processed_items = []
    for item_data in raw_items:
        try:
            # Ensure URL is a string, as Pydantic's HttpUrl can be strict
            # and some links in awesome-lists might be relative or internal anchors.
            # For dashboard display, a string URL is generally fine.
            item_data["url"] = str(item_data["url"])
            trend_item = HomeServerTrendItem(**item_data)
            processed_items.append(trend_item)
        except Exception as e:
            logger.warning(f"Failed to process item {item_data.get('name')}: {e}")
            # Optionally, log the problematic item_data itself for debugging
            # logger.debug(f"Problematic item data: {item_data}")
    logger.info(f"Successfully processed {len(processed_items)} items.")
    return processed_items

def save_data(data: List[HomeServerTrendItem], output_dir: str) -> Dict[str, str]:
    ensure_directories([output_dir])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Convert Pydantic models to dicts for JSON/CSV serialization
    dict_data = [item.model_dump(mode='json') for item in data]

    json_file_path = os.path.join(output_dir, f"home_server_trends_{timestamp}.json")
    csv_file_path = os.path.join(output_dir, f"home_server_trends_{timestamp}.csv")
    latest_json_path = os.path.join(output_dir, "home_server_trends_latest.json")
    latest_csv_path = os.path.join(output_dir, "home_server_trends_latest.csv")

    try:
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(dict_data, f, indent=2, ensure_ascii=False)
        with open(latest_json_path, 'w', encoding='utf-8') as f:
            json.dump(dict_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Successfully saved JSON data to {json_file_path} and {latest_json_path}")

        if dict_data:
            fieldnames = dict_data[0].keys()
            # Ensure all dicts have the same keys for CSV, filling missing ones with None or empty string
            consistent_data = []
            for row_dict in dict_data:
                consistent_row = {key: row_dict.get(key) for key in fieldnames}
                consistent_data.append(consistent_row)

            for csv_path_item in [csv_file_path, latest_csv_path]:
                with open(csv_path_item, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(consistent_data)
            logger.info(f"Successfully saved CSV data to {csv_file_path} and {latest_csv_path}")
        else:
            logger.info("No data to save to CSV.")

    except IOError as e:
        logger.error(f"Error saving data: {e}")
        return {}

    return {
        "json_file": json_file_path,
        "csv_file": csv_file_path,
        "latest_json": latest_json_path,
        "latest_csv": latest_csv_path,
    }

def main():
    logger.info("Starting Home Server Trends ETL process")
    project_root = get_project_root()
    output_dir = os.path.join(project_root, "data", "home_server_trends")

    session = create_session()
    all_raw_items = []

    # Fetch and parse from awesome-selfhosted
    logger.info("Processing awesome-selfhosted list...")
    selfhosted_content = fetch_markdown_content(session, AWESOME_SELFHOSTED_URL, "awesome-selfhosted")
    if selfhosted_content:
        selfhosted_items = parse_markdown(selfhosted_content, AWESOME_SELFHOSTED_CATEGORIES, "awesome-selfhosted")
        all_raw_items.extend(selfhosted_items)
        logger.info(f"Fetched and parsed {len(selfhosted_items)} items from awesome-selfhosted.")
    else:
        logger.warning("Could not fetch or parse content from awesome-selfhosted.")

    # Fetch and parse from awesome-home-automation
    logger.info("Processing awesome-home-automation list...")
    home_auto_content = fetch_markdown_content(session, AWESOME_HOME_AUTOMATION_URL, "awesome-home-automation")
    if home_auto_content:
        # Attempt to determine actual categories if placeholder list is too generic
        # For now, we'll use the predefined HOME_AUTOMATION_CATEGORIES.
        # A more advanced version could try to dynamically extract H2/H3s from this new list.
        home_auto_items = parse_markdown(home_auto_content, HOME_AUTOMATION_CATEGORIES, "awesome-home-automation")
        all_raw_items.extend(home_auto_items)
        logger.info(f"Fetched and parsed {len(home_auto_items)} items from awesome-home-automation.")
    else:
        logger.warning("Could not fetch or parse content from awesome-home-automation.")

    if not all_raw_items:
        logger.error("No items collected from any source. Exiting.")
        return

    # De-duplication
    logger.info(f"Total items before de-duplication: {len(all_raw_items)}")
    seen_ids = set()
    unique_items = []
    for item in all_raw_items:
        if item['id'] not in seen_ids:
            unique_items.append(item)
            seen_ids.add(item['id'])
    logger.info(f"Total items after de-duplication: {len(unique_items)}")
    all_raw_items = unique_items # Replace all_raw_items with unique_items

    processed_items = process_items(all_raw_items)
    if not processed_items:
        logger.warning("No items could be processed into the data model after de-duplication. Exiting.")
        return

    file_paths = save_data(processed_items, output_dir)
    if file_paths:
        logger.info(f"Home Server Trends ETL completed successfully. Data saved to {output_dir}")
        logger.info(f"Files: {list(file_paths.values())}")
        logger.info(f"Total items processed: {len(processed_items)}")
    else:
        logger.error("Home Server Trends ETL failed during data saving.")

if __name__ == "__main__":
    main()
