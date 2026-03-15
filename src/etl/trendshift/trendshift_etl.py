"""TrendShift ETL Pipeline.

Scrapes trending developer repositories from trendshift.io and outputs
JSON for Knowledge Garden consumption.
"""

import json
import os
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from src.etl.base import BaseETL

TRENDSHIFT_URL = "https://trendshift.io/"


class TrendShiftETL(BaseETL):
    """ETL pipeline for TrendShift.io trending repositories.

    Scrapes the main page for trending developer repos, extracting
    name, description, stars, and GitHub URL.
    """

    def __init__(
        self,
        name: str = "trendshift",
        **kwargs,
    ):
        super().__init__(name=name, **kwargs)

    def extract(self) -> list[dict]:
        """Scrape trending repos from trendshift.io."""
        self.logger.info(f"Fetching trending repos from {TRENDSHIFT_URL}")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

        try:
            response = requests.get(TRENDSHIFT_URL, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch TrendShift page: {e}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        repos: list[dict] = []

        # TrendShift lists repos as cards/links — try common selectors
        # The site uses <a> tags with repo info inside cards
        for link in soup.select("a[href*='github.com']"):
            href = link.get("href", "")
            if "github.com" not in href:
                continue

            # Extract text content as title fallback
            title = link.get_text(strip=True) or href.split("/")[-1]

            repos.append({
                "url": href if href.startswith("http") else f"https://github.com{href}",
                "title": title,
                "raw_html": str(link),
            })

        # Fallback: try generic card-based extraction if <a> links are empty
        if not repos:
            self.logger.info("Primary selector found nothing, trying broader extraction…")
            for card in soup.select("[class*='repo'], [class*='card'], [class*='item']"):
                link_tag = card.find("a", href=True)
                if not link_tag:
                    continue
                href = link_tag.get("href", "")
                title_tag = card.find(["h2", "h3", "h4", "a"])
                title = title_tag.get_text(strip=True) if title_tag else href

                desc_tag = card.find("p")
                description = desc_tag.get_text(strip=True) if desc_tag else ""

                repos.append({
                    "url": href if href.startswith("http") else f"https://trendshift.io{href}",
                    "title": title,
                    "description": description,
                })

        self.logger.info(f"Extracted {len(repos)} trending repos")
        self.metrics.records_extracted = len(repos)
        return repos

    def transform(self, data: list[dict]) -> list[dict]:
        """Normalise scraped data into Knowledge Garden format.

        Args:
            data: Raw scraped repo dicts.

        Returns:
            Normalised article dicts.
        """
        seen_urls: set[str] = set()
        transformed: list[dict] = []

        for repo in data:
            url = repo.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            title = repo.get("title", "Unknown")
            # If title is generic (e.g. "GitHub"), derive from URL
            if title in ("GitHub", "Unknown", "") and "github.com" in url:
                parts = url.rstrip("/").split("/")
                # Extract owner/repo from URL like https://github.com/owner/repo
                if len(parts) >= 5:
                    title = f"{parts[-2]}/{parts[-1]}"
                elif len(parts) >= 4:
                    title = parts[-1]

            transformed.append({
                "title": title,
                "url": url,
                "description": repo.get("description", ""),
                "published_at": datetime.utcnow().isoformat(),
                "source": "TrendShift",
            })

        self.logger.info(f"Transformed {len(transformed)} repos (deduped)")
        self.metrics.records_transformed = len(transformed)
        return transformed

    def load(self, data: list[dict]) -> None:
        """Write trending repos to JSON."""
        if not data:
            self.logger.warning("No data to load.")
            return

        os.makedirs(self.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        ts_path = os.path.join(self.output_dir, f"trendshift_{timestamp}.json")
        with open(ts_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        latest_path = os.path.join(self.output_dir, "latest.json")
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Saved {len(data)} repos → {latest_path}")
        self.metrics.records_loaded = len(data)


if __name__ == "__main__":
    etl = TrendShiftETL()
    etl.run()
