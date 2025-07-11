# Use Case: Itch.io Trending Games

"""Fetch trending games from itch.io and save to JSON and CSV."""

import sys
import os
from datetime import datetime, timezone
import requests
import pandas as pd
from bs4 import BeautifulSoup

# Add the project root to the path for imports
from src.utils.logging import get_logger
from src.utils.file_system import ensure_directories, get_project_root

logger = get_logger("ItchIo_Trending_ETL")
ITC_URL = "https://itch.io/games/top-sellers"  # Changed to use top sellers page


def get_itchio_trending() -> None:
    """
    Fetches trending games from itch.io and saves them as JSON and CSV.

    Extracted values:
    - title: game title
    - author: game developer/creator
    - price: game price
    - url: game URL on itch.io
    - fetched_at: ISO timestamp when the ETL was run
    """
    logger.info("Fetching itch.io trending games")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(ITC_URL, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find game items on the page
        game_items = soup.find_all('div', class_='game_cell')
        
        logger.debug(f"Found {len(game_items)} game items on the page")
        
        if not game_items:
            # Try alternative selector
            game_items = soup.find_all('a', class_='game_link')
            logger.debug(f"Using alternative selector, found {len(game_items)} items")
        
    except Exception as e:
        logger.error(f"Error fetching itch.io trending games: {e}")
        # Create empty data to avoid breaking the data service
        trending_list = []
        df = pd.DataFrame(trending_list)
        output_dir = os.path.join(get_project_root(), "data/games")
        ensure_directories(["data/games"])
        json_path = os.path.join(output_dir, "itchio_trending.json")
        csv_path = os.path.join(output_dir, "itchio_trending.csv")
        df.to_json(json_path, orient="records")
        df.to_csv(csv_path, index=False, sep="|")
        logger.info("Created empty itch.io trending files due to fetch error")
        return

    trending_list = []
    fetched_at = datetime.now(timezone.utc).isoformat()
    
    for item in game_items[:20]:  # Limit to top 20 games
        try:
            # Extract game information
            title_elem = item.find('div', class_='game_title') or item.find('div', class_='title')
            title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
            
            author_elem = item.find('div', class_='game_author') or item.find('div', class_='game_author_name')
            author = author_elem.get_text(strip=True) if author_elem else "Unknown Author"
            
            price_elem = item.find('div', class_='price_value') or item.find('span', class_='price')
            price = price_elem.get_text(strip=True) if price_elem else "Free"
            
            # Get the link
            link_elem = item.find('a') if item.name != 'a' else item
            url = link_elem.get('href', '') if link_elem else ''
            if url and not url.startswith('http'):
                url = f"https://itch.io{url}"
            
            trending_list.append({
                "title": title,
                "author": author,
                "price": price,
                "link": url,
                "fetched_at": fetched_at
            })
            
        except Exception as e:
            logger.warning(f"Error processing game item: {e}")
            continue

    if not trending_list:
        logger.warning("No trending games found")
        # Create empty files to maintain consistency with data structure
        try:
            output_dir = os.path.join(get_project_root(), "data/games")
            ensure_directories(["data/games"])

            json_path = os.path.join(output_dir, "itchio_trending.json")
            csv_path = os.path.join(output_dir, "itchio_trending.csv")

            # Create empty JSON and CSV files
            with open(json_path, 'w') as f:
                f.write('[]')
            
            with open(csv_path, 'w') as f:
                f.write('title|author|price|link|fetched_at\n')  # Header only

            logger.info(f"Empty itch.io trending files created at {json_path} and {csv_path}")
        except Exception as e:
            logger.error(f"Error creating empty itch.io trending files: {e}")
        return

    df = pd.DataFrame(trending_list)
    
    # Only sort if DataFrame is not empty and has required columns
    if not df.empty and "title" in df.columns:
        df = df.sort_values(by="title")
    else:
        logger.warning("DataFrame is empty or missing 'title' column, skipping sort")

    output_dir = os.path.join(get_project_root(), "data/games")
    ensure_directories(["data/games"])

    json_path = os.path.join(output_dir, "itchio_trending.json")
    csv_path = os.path.join(output_dir, "itchio_trending.csv")

    df.to_json(json_path, orient="records")
    logger.info(f"Itch.io trending games saved to {json_path}")
    df.to_csv(csv_path, index=False, sep="|")
    logger.info(f"Itch.io trending games saved to {csv_path}")


if __name__ == "__main__":
    get_itchio_trending() 