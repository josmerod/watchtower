import requests
import datetime
import os
import pandas as pd
import json
import logging
import sys

# Add project root to sys.path to allow imports from src
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils.logging import get_logger
from src.utils.file_system import ensure_directories, get_project_root

# Constants
RAWG_API_URL = "https://api.rawg.io/api/games"
# TODO: Replace "YOUR_RAWG_API_KEY" with your actual RAWG API key
# or set it as an environment variable named RAWG_API_KEY.
API_KEY = os.getenv("RAWG_API_KEY", "YOUR_RAWG_API_KEY")
OUTPUT_DIR = "data/games"
JSON_FILE = os.path.join(OUTPUT_DIR, "new_releases.json")
CSV_FILE = os.path.join(OUTPUT_DIR, "new_releases.csv")
DAYS_PAST = 30
DAYS_FUTURE = 90
MIN_METACRITIC_SCORE = 70

# Setup logging
logger = get_logger(__name__)

if API_KEY == "YOUR_RAWG_API_KEY":
    logger.warning("RAWG_API_KEY is not set. Please set it as an environment variable or in the script.")

def fetch_games(page_num: int, params: dict) -> dict | None:
    """
    Fetches a page of game data from the RAWG API.

    Args:
        page_num: The page number to fetch.
        params: Dictionary of API parameters (key, dates, ordering, metacritic).

    Returns:
        A dictionary containing the JSON response from the API or None if an error occurs.
    """
    request_params = params.copy()
    request_params['page'] = page_num
    try:
        response = requests.get(RAWG_API_URL, params=request_params, timeout=10) # 10 second timeout
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        return response.json()
    except requests.exceptions.Timeout:
        logger.error(f"Request timed out while fetching page {page_num}.")
        return None
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred while fetching page {page_num}: {http_err} - Status Code: {response.status_code}")
        if response.status_code == 401:
            logger.error("Unauthorized: Check your RAWG_API_KEY.")
        elif response.status_code == 404:
            logger.error(f"Resource not found for page {page_num}. This might indicate no more pages.")
        return None
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Error during request for page {page_num}: {req_err}")
        return None
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON response for page {page_num}.")
        return None

def process_games_data(games_raw_data: list) -> list:
    """
    Processes raw game data from the API response.

    Args:
        games_raw_data: A list of game objects from the API.

    Returns:
        A list of processed and filtered game dictionaries.
    """
    processed_games = []
    if not games_raw_data:
        return processed_games

    for game in games_raw_data:
        metacritic_score = game.get('metacritic')
        # Filter out games with no Metacritic score or score below MIN_METACRITIC_SCORE
        # The API should already filter by metacritic score, but this is a safeguard.
        if metacritic_score is None or metacritic_score < MIN_METACRITIC_SCORE:
            continue

        platforms = [p['platform']['name'] for p in game.get('platforms', []) if p.get('platform')]
        genres = [g['name'] for g in game.get('genres', [])]

        processed_game = {
            'id': game.get('id'),
            'name': game.get('name'),
            'released': game.get('released'),
            'platforms': platforms,
            'genres': genres,
            'metacritic': metacritic_score,
            'description_raw': game.get('description_raw', f"https://rawg.io/games/{game.get('slug')}"), # Fallback to link if no description
            'rawg_link': f"https://rawg.io/games/{game.get('slug')}"
        }
        processed_games.append(processed_game)

    logger.info(f"Processed {len(processed_games)} games out of {len(games_raw_data)} raw entries.")
    return processed_games

def get_new_releases():
    """
    Main function to fetch, process, and save new game releases.
    """
    logger.info("Starting get_new_releases function.")
    all_processed_games = []

    start_date = (datetime.date.today() - datetime.timedelta(days=DAYS_PAST)).strftime('%Y-%m-%d')
    end_date = (datetime.date.today() + datetime.timedelta(days=DAYS_FUTURE)).strftime('%Y-%m-%d')

    params = {
        'key': API_KEY,
        'dates': f'{start_date},{end_date}',
        'ordering': '-released', # Order by release date, newest first
        'metacritic': f'{MIN_METACRITIC_SCORE},100' # Metacritic score range
    }

    # If no API key is provided, create empty files and return
    if API_KEY == "YOUR_RAWG_API_KEY":
        logger.warning("No RAWG API key provided, cannot fetch new releases data")
        try:
            project_root_path = get_project_root()
            output_path = os.path.join(project_root_path, OUTPUT_DIR)
            ensure_directories([output_path])

            json_output_file = os.path.join(output_path, "new_releases.json")
            csv_output_file = os.path.join(output_path, "new_releases.csv")

            # Create empty JSON and CSV files
            with open(json_output_file, 'w') as f:
                f.write('[]')
            
            with open(csv_output_file, 'w') as f:
                f.write('id|name|released|platforms|genres|metacritic|description_raw|rawg_link\n')  # Header only

            logger.info(f"Empty new releases files created at {json_output_file} and {csv_output_file}")
        except Exception as e:
            logger.error(f"Error creating empty new releases files: {e}")
        return
    
    # Proceed with API calls if key is available
    current_page = 1
    max_pages = 10  # Safety limit for pagination

    while current_page <= max_pages:
        logger.info(f"Fetching page {current_page} of game releases...")
        raw_response = fetch_games(page_num=current_page, params=params)

        if raw_response and 'results' in raw_response:
            games_data = raw_response['results']
            if not games_data:
                logger.info("No more game data found on this page.")
                break # No more results

            processed_data = process_games_data(games_data)
            all_processed_games.extend(processed_data)
            logger.info(f"Fetched and processed {len(processed_data)} games from page {current_page}. Total processed: {len(all_processed_games)}")

            # Check for next page
            if raw_response.get('next'):
                current_page += 1
            else:
                logger.info("No 'next' page found. Ending pagination.")
                break
        else:
            logger.warning(f"No data received or error in fetching page {current_page}. Ending process.")
            break

        if current_page > max_pages:
            logger.warning(f"Reached maximum page limit ({max_pages}). Stopping.")
            break

    if not all_processed_games:
        logger.info("No games found or processed. Creating empty files.")
        try:
            project_root_path = get_project_root()
            output_path = os.path.join(project_root_path, OUTPUT_DIR)
            ensure_directories([output_path])

            json_output_file = os.path.join(output_path, "new_releases.json")
            csv_output_file = os.path.join(output_path, "new_releases.csv")

            # Create empty JSON and CSV files
            with open(json_output_file, 'w') as f:
                f.write('[]')
            
            with open(csv_output_file, 'w') as f:
                f.write('id|name|released|platforms|genres|metacritic|description_raw|rawg_link\n')  # Header only

            logger.info(f"Empty new releases files created at {json_output_file} and {csv_output_file}")
        except Exception as e:
            logger.error(f"Error creating empty new releases files: {e}")
        return

    # Save data
    try:
        # Ensure output directory exists
        project_root_path = get_project_root()
        output_path = os.path.join(project_root_path, OUTPUT_DIR)
        ensure_directories([output_path])

        json_output_file = os.path.join(output_path, "new_releases.json")
        csv_output_file = os.path.join(output_path, "new_releases.csv")

        df = pd.DataFrame(all_processed_games)

        # Save to JSON
        df.to_json(json_output_file, orient='records', indent=4, lines=False)
        logger.info(f"Successfully saved {len(df)} games to {json_output_file}")

        # Save to CSV
        df.to_csv(csv_output_file, sep='|', index=False)
        logger.info(f"Successfully saved {len(df)} games to {csv_output_file}")

    except Exception as e:
        logger.error(f"Error saving data: {e}")

if __name__ == "__main__":
    logger.info("Starting ETL process for new game releases.")
    get_new_releases()
    logger.info("ETL process for new game releases finished.")
