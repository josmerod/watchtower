"""ETL module for collecting active "General" threads from selected 4chan boards.

This ETL fetches each board's catalog via the official 4chan JSON API, filters
threads whose OP (subject or comment) contains the word "General" (case-
insensitive), and stores a consolidated list in the Watchtower data directory.

Output files (one dated and one `latest.json`) are written to
`data/4chan_generals/output/` for the dashboard's 4chan Generals tab.
"""

from __future__ import annotations

import json
import re
import warnings
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

from src.etl.base import SimpleETL
from src.utils.logging import get_logger

# Filter out BeautifulSoup warnings for URL-like content
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

# Canonical board list + descriptions. The dashboard tab imports these so a
# board is added/removed in exactly one place.
DEFAULT_BOARDS: dict[str, str] = {
    "g": "Technology - hardware, software, programming",
    "vg": "Video Games Generals - per-game general threads",
    "t": "Torrents/Technology - file sharing and tech",
    "pol": "Politically Incorrect - news and politics",
    "biz": "Business & Finance - markets, crypto, entrepreneurship",
    "sci": "Science & Math - research and study",
    "tv": "Television & Film - shows and movies",
    "fit": "Fitness - training and health",
    "mu": "Music - artists, genres, production",
    "v": "Video Games - gaming discussion",
    "k": "Weapons - firearms and militaria",
    "o": "Auto - cars and motorcycles",
    "diy": "Do It Yourself - home improvement, maker projects",
    "his": "History & Humanities - historical discussion",
    "int": "International - country/culture generals",
}


class FourChanGeneralsETL(SimpleETL):
    """ETL for 4chan *General* threads."""

    CATALOG_URL = "https://a.4cdn.org/{board}/catalog.json"

    def __init__(self, boards: list[str] | None = None, **kwargs: Any):
        self.boards = boards or list(DEFAULT_BOARDS.keys())
        super().__init__(name="4chan_generals", **kwargs)
        # Replace logger name to something shorter / clearer
        self.logger = get_logger("ETL.4chan_generals")

    # ------------------------------------------------------------------
    # Extract
    # ------------------------------------------------------------------
    def extract(self) -> list[dict[str, Any]]:
        """Retrieve raw thread data from each board's catalog."""
        self.logger.info("Extracting catalog data from 4chan API …")
        extracted: list[dict[str, Any]] = []

        for board in self.boards:
            url = self.CATALOG_URL.format(board=board)
            try:
                resp = requests.get(url, timeout=15)
                resp.raise_for_status()
                pages = resp.json()
            except Exception as exc:  # Broad catch -> logged & continue
                self.logger.error(f"Failed to fetch {url}: {exc}")
                continue

            for page in pages:
                for thread in page.get("threads", []):
                    # Attach board identifier early - useful downstream
                    thread["board"] = board
                    extracted.append(thread)

        return extracted

    # ------------------------------------------------------------------
    # Transform
    # ------------------------------------------------------------------
    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Filter *General* threads and clean up fields."""
        if not data:
            self.logger.warning("No data extracted – skipping transform phase.")
            return []

        transformed: list[dict[str, Any]] = []
        general_pattern = re.compile(r"\bgeneral\b", re.IGNORECASE)

        for item in data:
            combined_text = f"{item.get('sub', '')} {item.get('com', '')}"
            if not general_pattern.search(combined_text):
                continue  # Not a *General* thread

            board = item["board"]
            thread_id = item.get("no")
            if not thread_id:
                continue  # safety guard

            # Convert HTML comment to plain-text
            comment_html = item.get("com", "")
            comment_text = BeautifulSoup(comment_html, "html.parser").get_text(" ", strip=True) if comment_html else ""

            transformed.append(
                {
                    "board": board,
                    "thread_id": thread_id,
                    "subject": item.get("sub", ""),
                    "comment": comment_text,
                    "timestamp": item.get("time"),
                    "last_modified": item.get("last_modified"),
                    "replies": item.get("replies"),
                    "images": item.get("images"),
                    "url": f"https://boards.4chan.org/{board}/thread/{thread_id}",
                }
            )

        return transformed

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def load(self, data: list[dict[str, Any]]) -> None:
        """Persist results to JSON - dated and latest pointers."""
        if not data:
            self.logger.info("No *General* threads detected – nothing to load.")
            return

        # Call parent loader to persist time-stamped snapshot
        super().load(data)

        # Overwrite/update `latest.json` for quick access by Streamlit
        latest_path: Path = self.output_dir / "latest.json"
        latest_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        self.logger.info(f"Latest snapshot saved to {latest_path}")


if __name__ == "__main__":
    """Run the 4chan Generals ETL."""
    etl = FourChanGeneralsETL()
    try:
        metrics = etl.run()
        etl.logger.info(f"ETL completed successfully. Processed {metrics.records_extracted} records.")
    except Exception as e:
        etl.logger.error(f"ETL failed with error: {e}")
        raise
