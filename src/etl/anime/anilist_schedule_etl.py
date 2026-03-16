import datetime
import json
import logging
import pathlib
import time
from typing import Any

import requests
from pydantic.json import pydantic_encoder

from src.etl.base import BaseETL, ETLError
from src.models.anime import AniListScheduleItem

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

API_URL = "https://graphql.anilist.co"
MODULE_OUTPUT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent.parent / "data" / "anime"


class AniListScheduleETL(BaseETL):
    def __init__(self, batch_size: int | None = None, enable_checkpointing: bool = False):
        super().__init__(
            name="anilist_schedule_etl",
            description="ETL process for Anime Airing Schedule from AniList.",
            batch_size=batch_size,
            enable_checkpointing=enable_checkpointing,
        )

        self.output_dir = MODULE_OUTPUT_DIR
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        super()._ensure_directories()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract(self) -> list[dict[str, Any]]:
        self.logger.info("Starting AniList Schedule extraction.")
        
        # We want to get the schedule from the beginning of today to the end of next week
        now = int(time.time())
        # Let's get the schedule for the next 7 days
        next_week = now + (7 * 24 * 60 * 60)
        
        query = """
        query ($page: Int, $perPage: Int, $airingAt_greater: Int, $airingAt_lesser: Int) {
          Page(page: $page, perPage: $perPage) {
            pageInfo {
              hasNextPage
              total
            }
            airingSchedules(airingAt_greater: $airingAt_greater, airingAt_lesser: $airingAt_lesser, sort: TIME) {
              id
              airingAt
              episode
              media {
                id
                title {
                  romaji
                  english
                  native
                }
                coverImage {
                  medium
                  large
                }
                siteUrl
              }
            }
          }
        }
        """
        
        all_schedules = []
        page = 1
        has_next_page = True
        
        while has_next_page:
            variables = {
                "page": page,
                "perPage": 50,
                "airingAt_greater": now,
                "airingAt_lesser": next_week
            }
            
            try:
                self.logger.info(f"Fetching AniList schedule page {page}...")
                response = requests.post(API_URL, json={"query": query, "variables": variables}, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                page_info = data.get("data", {}).get("Page", {}).get("pageInfo", {})
                schedules = data.get("data", {}).get("Page", {}).get("airingSchedules", [])
                
                all_schedules.extend(schedules)
                has_next_page = page_info.get("hasNextPage", False)
                page += 1
                
                # Respect rate limits, optionally delay
                time.sleep(0.5)
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Failed to fetch from AniList API: {e}")
                self.metrics.error_count += 1
                break
                
        self.metrics.records_extracted = len(all_schedules)
        return all_schedules

    def transform(self, data: list[dict[str, Any]]) -> list[AniListScheduleItem]:
        self.logger.info("Starting AniList schedule transformation.")
        transformed = []
        
        for item in data:
            try:
                media = item.get("media", {})
                title = media.get("title", {})
                cover = media.get("coverImage", {})
                
                schedule_item = AniListScheduleItem(
                    id=item["id"],
                    airing_at=item["airingAt"],
                    episode=item["episode"],
                    media_id=media.get("id", 0),
                    title_romaji=title.get("romaji"),
                    title_english=title.get("english"),
                    title_native=title.get("native"),
                    cover_image_medium=cover.get("medium"),
                    cover_image_large=cover.get("large"),
                    site_url=media.get("siteUrl")
                )
                transformed.append(schedule_item)
            except Exception as e:
                self.logger.error(f"Error transforming schedule item: {e}")
                self.metrics.records_failed += 1
                
        self.metrics.records_transformed = len(transformed)
        return transformed

    def load(self, data: list[AniListScheduleItem]) -> None:
        self.logger.info("Starting AniList schedule loading.")
        if not data:
            self.logger.info("No data to save.")
            return

        file_path = self.output_dir / "anilist_schedule.json"
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(
                    [item.model_dump(by_alias=True) for item in data],
                    f,
                    indent=2,
                    default=pydantic_encoder,
                )
            self.metrics.records_loaded = len(data)
            self.logger.info(f"Successfully saved {len(data)} items to {file_path}")
        except OSError as e:
            self.logger.error(f"Failed to save data: {e}")
            self.metrics.error_count += 1
            raise Exception(f"Failed to save schedule data: {e}") from e


if __name__ == "__main__":
    logger.info("Starting AniList Schedule ETL script execution.")
    try:
        etl_instance = AniListScheduleETL()
        etl_instance.run()
        logger.info("AniList Schedule ETL script finished successfully.")
    except ETLError as e:
        logger.error(f"ETL process failed: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred during ETL execution: {e}", exc_info=True)
