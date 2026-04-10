import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.etl.base import BaseETL
from src.utils.file_system import ensure_directories
from src.utils.logging import get_logger

logger = get_logger("AudibleReleasesETL")

class AudibleReleasesETL(BaseETL[dict[str, Any], dict[str, Any]]):
    """ETL to scrape Audible New Releases and format them for the Scavenging tab."""

    def __init__(self):
        super().__init__(
            name="audible_releases",
            description="Scrapes Audible New Releases (latest 30 days) into the Scavenging ecosystem",
            enable_checkpointing=True,
            max_retries=3,
            retry_delay=5
        )
        self.base_url = "https://www.audible.es/newreleases?audible_programs=21870165031&feature_six_browse-bin=18385686031&feature_six_browse-bin=18385668031&feature_twelve_browse-bin=18385638031&feature_twelve_browse-bin=18385639031&publication_date=20260215-20260315&sort=pubdate-desc-rank"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
        }

    def _get_soup(self, page: int) -> BeautifulSoup:
        """Fetch and parse a specific page."""
        url = self.base_url + f"&page={page}"
        response = requests.get(url, headers=self.headers, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")

    def extract(self) -> list[dict[str, Any]]:
        """Extract books across pages until no more products are found."""
        all_products = []
        page = 1
        max_limit = 25 # the maximum observed page depth in testing

        while page <= max_limit:
            self.logger.info(f"Scraping Audible releases page {page}...")
            try:
                soup = self._get_soup(page)
            except Exception as e:
                self.logger.error(f"Failed fetching page {page}: {e}")
                break

            products = soup.find_all('li', class_='productListItem')
            if not products:
                self.logger.info("No more products found, stopping extraction.")
                break

            for p in products:
                title_span = p.find('h3', class_='bc-heading')
                if not title_span:
                    continue
                a_tag = title_span.find('a')
                title = a_tag.text.strip() if a_tag else title_span.text.strip()
                link = "https://www.audible.es" + a_tag['href'] if a_tag and 'href' in a_tag.attrs else ""
                
                author_span = p.find('li', class_='authorLabel')
                author = author_span.text.replace('De:', '').strip() if author_span else ""
                
                narrator_span = p.find('li', class_='narratorLabel')
                narrator = narrator_span.text.replace('Narrado por:', '').strip() if narrator_span else ""

                runtime_span = p.find('li', class_='runtimeLabel')
                runtime = runtime_span.text.replace('Duración:', '').strip() if runtime_span else ""
                
                date_span = p.find('li', class_='releaseDateLabel')
                date_str = date_span.text.replace('Fecha de publicación:', '').strip() if date_span else ""
                
                lang_span = p.find('li', class_='languageLabel')
                lang = lang_span.text.replace('Idioma:', '').strip() if lang_span else ""

                all_products.append({
                    "title": title,
                    "link": link,
                    "author": author,
                    "narrator": narrator,
                    "runtime": runtime,
                    "published_str": date_str,
                    "language": lang
                })

            page += 1

        self.logger.info(f"Extracted {len(all_products)} total products from Audible.")
        return all_products

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Format the data to fit the Scavenging tab expectation."""
        transformed = []
        
        for item in data:
            # Reformat the fields into the unified scavenging model
            # expected keys: title, link, published, summary, category, source
            
            # Summary parsing: combine Author, Narrator, Runtime, Language
            summary_parts = []
            if item.get("author"): summary_parts.append(f"👨‍💻 Autor: {item['author']}")
            if item.get("narrator"): summary_parts.append(f"🎙️ Narrador: {item['narrator']}")
            if item.get("runtime"): summary_parts.append(f"⏱️ {item['runtime']}")
            if item.get("language"): summary_parts.append(f"🌐 {item['language']}")
            summary = " | ".join(summary_parts)

            # Date fallback: we try to parse typical Spanish dates casually if needed, 
            # or just rely on passing it raw. For Scavenging table sorting, isoformat is better,
            # but usually it's e.g. "15-03-26". Let's attempt standard parsing.
            pub_date = item.get("published_str", "")
            iso_date = datetime.utcnow().isoformat()
            if pub_date:
                try:
                    # e.g., "15-03-26" -> d-m-y
                    day, month, year = pub_date.split("-")
                    dt = datetime(int(f"20{year}"), int(month), int(day), tzinfo=timezone.utc)
                    iso_date = dt.isoformat()
                except Exception:
                    # Keep fallback current UTC date if it fails to parse
                    pass
            
            # The Scavenging tab also likes price and deal_type if available. 
            # We'll set deal_type to "Audiobook" and price to "Included" since they are in the sub.
            transformed.append({
                "title": item.get("title", "Unknown Title"),
                "link": item.get("link", ""),
                "published": iso_date,
                "summary": summary,
                "category": "audible",
                "source": "audible_releases_etl",
                "deal_type": "Audiobook",
                "price": "Included",
                "currency": "-"
            })

        self.logger.info(f"Transformed {len(transformed)} products for Scavenging layout.")
        return transformed

    def load(self, data: list[dict[str, Any]]) -> None:
        """Write out to data/scavenging/audible_rss_entries.json."""
        if not data:
            self.logger.warning("No data to load for Audible Releases.")
            return

        dest_dir = Path(self.data_dir).parent.parent / "data" / "scavenging"
        ensure_directories([str(dest_dir)])

        json_file = dest_dir / "audible_rss_entries.json"
        csv_file = dest_dir / "audible_rss_entries.csv"

        try:
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Saved {len(data)} entries to {json_file}")
        except Exception as e:
            self.logger.error(f"Failed creating JSON: {e}")

        try:
            df = pd.DataFrame(data)
            df.to_csv(csv_file, index=False, encoding="utf-8")
        except Exception as e:
            self.logger.error(f"Failed creating CSV: {e}")

if __name__ == "__main__":
    AudibleReleasesETL().run()
