import datetime
import json
import logging
import os
import pathlib
import time
from typing import Dict, List, Optional, Any, Tuple

import requests
from pydantic.json import pydantic_encoder
from dotenv import load_dotenv

from src.etl.base import BaseETL, ETLError
from src.models.anime import AnimeItem

# Load environment variables from .env file
load_dotenv()

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

API_BASE_URL = "https://api.myanimelist.net/v2"
CLIENT_ID_ENV_VAR = "MAL_CLIENT_ID"
# Define OUTPUT_DIR at the module level for clarity, but it will be managed by the class instance
MODULE_OUTPUT_DIR = (
    pathlib.Path(__file__).resolve().parent.parent.parent.parent / "data" / "anime"
)

FIELDS_TO_REQUEST = "id,title,main_picture,synopsis,mean,rank,popularity,num_list_users,num_scoring_users,nsfw,media_type,status,genres,num_episodes,start_season,broadcast,source,average_episode_duration,rating,studios"


class MalETL(BaseETL):
    def __init__(
        self, batch_size: Optional[int] = None, enable_checkpointing: bool = False
    ):
        super().__init__(
            name="mal_anime_etl",
            description="ETL process for MyAnimeList anime data.",
            batch_size=batch_size,
            enable_checkpointing=enable_checkpointing,
        )

        self.client_id = os.getenv(CLIENT_ID_ENV_VAR)
        if not self.client_id:
            msg = f"{CLIENT_ID_ENV_VAR} environment variable not set. Please set it to your MyAnimeList API Client ID."
            logger.error(msg)
            raise ValueError(msg)

        # Override the output_dir from BaseETL to match specific requirements
        self.output_dir = MODULE_OUTPUT_DIR
        self._ensure_directories()  # Call BaseETL's method to create this updated output_dir

    def _ensure_directories(self) -> None:
        """Ensure all required directories exist, including the custom output_dir."""
        super()._ensure_directories()  # Creates self.data_dir, self.checkpoint_dir
        # self.output_dir is now MODULE_OUTPUT_DIR, ensure it also exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _make_request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Makes a GET request to the MyAnimeList API.
        """
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        url = f"{API_BASE_URL}{endpoint}"

        headers = {
            "X-MAL-CLIENT-ID": self.client_id,
            "User-Agent": "WatchtowerMALETL/1.0",
        }

        logger.info(f"Making request to {url} with params: {params}")

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error occurred: {e} - Response: {e.response.text}")
            self.metrics.error_count += 1
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception occurred: {e}")
            self.metrics.error_count += 1
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to decode JSON response: {e} - Response: {response.text if 'response' in locals() else 'N/A'}"
            )
            self.metrics.error_count += 1
        return None

    def _get_seasonal_anime_raw(
        self, year: int, season: str, limit: int = 100
    ) -> Optional[Dict[str, Any]]:
        """Fetches raw seasonal anime data."""
        endpoint = f"/anime/season/{year}/{season}"
        params = {
            "limit": limit,
            "sort": "anime_num_list_users",  # Sort by popularity
            "fields": FIELDS_TO_REQUEST,
        }
        return self._make_request(endpoint, params)

    def _get_ranked_anime_raw(
        self, ranking_type: str, limit: int = 100
    ) -> Optional[Dict[str, Any]]:
        """Fetches raw ranked anime data."""
        endpoint = "/anime/ranking"
        params = {
            "ranking_type": ranking_type,
            "limit": limit,
            "fields": FIELDS_TO_REQUEST,
        }
        return self._make_request(endpoint, params)

    def extract(self) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Extracts data from MyAnimeList API.
        Returns a dictionary containing raw data for different categories.
        """
        self.logger.info("Starting MAL data extraction.")
        extracted_data = {
            "seasonal": None,
            "popular": None,
            "favorite": None,
            "top_rated_all": None,
            "top_airing": None,
            "top_upcoming": None,
            "top_tv_series": None,
            "top_movies": None,
            "top_ova": None,
            "top_special": None,
        }

        # Determine current year and season
        now = datetime.datetime.now()
        current_year = now.year
        month = now.month
        if 1 <= month <= 3:
            current_season = "winter"
        elif 4 <= month <= 6:
            current_season = "spring"
        elif 7 <= month <= 9:
            current_season = "summer"
        else:  # 10, 11, 12
            current_season = "fall"

        logger.info(f"Fetching seasonal anime for {current_year} {current_season}.")
        extracted_data["seasonal"] = self._get_seasonal_anime_raw(
            current_year, current_season, limit=20
        )

        # Add a small delay to avoid hitting rate limits too quickly
        time.sleep(1)

        logger.info("Fetching top popular anime.")
        extracted_data["popular"] = self._get_ranked_anime_raw("bypopularity", limit=20)

        time.sleep(1)

        logger.info("Fetching top favorite anime.")
        extracted_data["favorite"] = self._get_ranked_anime_raw("favorite", limit=20)

        time.sleep(1)

        # Fetch comprehensive rankings for community recommendations
        logger.info("Fetching top rated anime (all time).")
        extracted_data["top_rated_all"] = self._get_ranked_anime_raw("all", limit=100)

        time.sleep(1)

        logger.info("Fetching top airing anime.")
        extracted_data["top_airing"] = self._get_ranked_anime_raw("airing", limit=50)

        time.sleep(1)

        logger.info("Fetching top upcoming anime.")
        extracted_data["top_upcoming"] = self._get_ranked_anime_raw(
            "upcoming", limit=50
        )

        time.sleep(1)

        logger.info("Fetching top TV series.")
        extracted_data["top_tv_series"] = self._get_ranked_anime_raw("tv", limit=100)

        time.sleep(1)

        logger.info("Fetching top movies.")
        extracted_data["top_movies"] = self._get_ranked_anime_raw("movie", limit=50)

        time.sleep(1)

        logger.info("Fetching top OVA.")
        extracted_data["top_ova"] = self._get_ranked_anime_raw("ova", limit=30)

        time.sleep(1)

        logger.info("Fetching top special episodes.")
        extracted_data["top_special"] = self._get_ranked_anime_raw("special", limit=30)

        self.metrics.records_extracted = sum(
            len(v.get("data", [])) for v in extracted_data.values() if v
        )
        return extracted_data

    def transform(
        self, data: Dict[str, Optional[Dict[str, Any]]]
    ) -> Dict[str, List[AnimeItem]]:
        """
        Transforms raw API data into lists of AnimeItem models.
        """
        self.logger.info("Starting MAL data transformation.")
        transformed_data: Dict[str, List[AnimeItem]] = {
            "seasonal": [],
            "popular": [],
            "favorite": [],
            "top_rated_all": [],
            "top_airing": [],
            "top_upcoming": [],
            "top_tv_series": [],
            "top_movies": [],
            "top_ova": [],
            "top_special": [],
        }

        for key, raw_response in data.items():
            if raw_response and "data" in raw_response:
                for item_entry in raw_response.get("data", []):
                    node_data = item_entry.get("node")
                    if node_data:
                        try:
                            # The 'rank' field in API is sometimes part of 'ranking' dict
                            # This was an error in earlier Pydantic model spec.
                            # For now, we assume 'rank' is directly in 'node_data' as per AnimeItem
                            # If API sends rank inside item_entry['ranking']['rank'], it needs adjustment
                            # For now, we proceed assuming fields in FIELDS_TO_REQUEST are at node level
                            anime = AnimeItem(**node_data)
                            transformed_data[key].append(anime)
                        except (
                            Exception
                        ) as e:  # Catch Pydantic validation errors or others
                            logger.error(
                                f"Error transforming item for {key}: {node_data.get('title', 'Unknown Title')}. Error: {e}"
                            )
                            self.metrics.records_failed += 1
            else:
                logger.warning(
                    f"No data or malformed response for '{key}' category during transformation."
                )

        self.metrics.records_transformed = sum(
            len(v) for v in transformed_data.values()
        )
        return transformed_data

    def load(self, data: Dict[str, List[AnimeItem]]) -> None:
        """
        Saves the transformed AnimeItem lists to JSON files.
        """
        self.logger.info("Starting MAL data loading.")
        self.output_dir.mkdir(parents=True, exist_ok=True)  # Ensure output_dir exists

        filenames = {
            "seasonal": "current_season_anime.json",
            "popular": "top_popular_anime.json",
            "favorite": "top_favorite_anime.json",
            "top_rated_all": "top_rated_all_time.json",
            "top_airing": "top_airing_anime.json",
            "top_upcoming": "top_upcoming_anime.json",
            "top_tv_series": "top_tv_series.json",
            "top_movies": "top_movies.json",
            "top_ova": "top_ova.json",
            "top_special": "top_special.json",
        }

        loaded_count = 0
        for key, anime_list in data.items():
            if not anime_list:
                logger.info(f"No data to save for {key}.")
                continue

            file_path = self.output_dir / filenames[key]
            logger.info(f"Saving {len(anime_list)} items for {key} to {file_path}")
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(
                        [item.model_dump(by_alias=True) for item in anime_list],
                        f,
                        indent=2,
                        default=pydantic_encoder,
                    )
                loaded_count += len(anime_list)
            except IOError as e:
                logger.error(f"Failed to save data for {key} to {file_path}: {e}")
                self.metrics.error_count += 1
                raise Exception(f"Failed to save data for {key}: {e}") from e
            except Exception as e:  # Catch any other unexpected errors during save
                logger.error(
                    f"An unexpected error occurred while saving data for {key} to {file_path}: {e}"
                )
                self.metrics.error_count += 1
                raise Exception(f"Unexpected error saving data for {key}: {e}") from e

        self.metrics.records_loaded = loaded_count
        if loaded_count == 0 and self.metrics.records_transformed > 0:
            logger.warning(
                "Data was transformed but nothing was loaded. Check for issues."
            )


if __name__ == "__main__":
    logger.info("Starting MyAnimeList ETL script execution.")
    try:
        # For local testing, you might want to load .env variables if MAL_CLIENT_ID is there
        # from dotenv import load_dotenv
        # load_dotenv()

        etl_instance = MalETL()
        etl_instance.run()  # This will call extract, transform, load
        logger.info("MyAnimeList ETL script finished successfully.")

    except ValueError as ve:  # Specifically for MAL_CLIENT_ID not set
        logger.critical(f"ETL run failed due to configuration error: {ve}")
        # No need to print again, already logged by MalETL constructor
    except ETLError as e:
        logger.error(f"ETL process failed: {e}", exc_info=True)
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during ETL execution: {e}", exc_info=True
        )
