from __future__ import annotations

"""ETL module for collecting active "General" threads from selected 4chan boards.

This ETL fetches each board's catalog via the official 4chan JSON API, filters
threads whose OP (subject or comment) contains the word "General" (case-
insensitive), and stores a consolidated list in the Watchtower data directory.

Output files (one dated and one `latest.json`) are written to
`data/4chan_generals/output/` so that Streamlit components can visualise the
information easily.
"""

import json
import re
import warnings
from pathlib import Path
from typing import Any, List

import requests
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning  # type: ignore

from src.etl.base import SimpleETL
from src.utils.logging import get_logger

# Filter out BeautifulSoup warnings for URL-like content
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)


class FourChanGeneralsETL(SimpleETL):
    """ETL for 4chan *General* threads."""

    CATALOG_URL = "https://a.4cdn.org/{board}/catalog.json"

    def __init__(self, boards: List[str] | None = None, **kwargs: Any):
        self.boards = boards or [
            "g",  # Technology
            "vg",  # Video Games Generals
            "t",  # Torrents/Technology
            "pol",  # Politically Incorrect
            "biz",  # Business & Finance
            "sci",  # Science & Math
            "tv",  # Television & Film
            "fit",  # Fitness
            "mu",  # Music
            "v",  # Video Games
            "k",  # Weapons
            "o",  # Auto
            "diy",  # Do It Yourself
            "his",  # History & Humanities
            "int",  # International
        ]
        super().__init__(name="4chan_generals", **kwargs)
        # Replace logger name to something shorter / clearer
        self.logger = get_logger("ETL.4chan_generals")

    # ------------------------------------------------------------------
    # Extract
    # ------------------------------------------------------------------
    def extract(self) -> List[dict[str, Any]]:  # noqa: D401
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
                    # Attach board identifier early – useful downstream
                    thread["board"] = board
                    extracted.append(thread)

        return extracted

    # ------------------------------------------------------------------
    # Transform
    # ------------------------------------------------------------------
    def transform(
        self, data: List[dict[str, Any]]
    ) -> List[dict[str, Any]]:  # noqa: D401
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
            comment_text = (
                BeautifulSoup(comment_html, "html.parser").get_text(" ", strip=True)
                if comment_html
                else ""
            )

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
    def load(self, data: List[dict[str, Any]]) -> None:  # noqa: D401
        """Persist results to JSON – dated and latest pointers."""
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
