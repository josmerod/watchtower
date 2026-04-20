"""Semantic Scholar ETL Implementation.

Monitors AI and Machine Learning research papers, citations, and trends.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from src.etl.base import BaseETL
from src.exceptions.etl import LoadError
from src.utils.logging import get_logger
from src.etl.proxy_manager import ProxyManager


class SemanticScholarETL(BaseETL):
    """Semantic Scholar ETL for tracking AI research and citations."""

    def __init__(self, **kwargs):
        """Initialize Semantic Scholar ETL."""
        super().__init__(
            name="semantic_scholar",
            description="Tracks fundamental AI and ML research via Semantic Scholar Graph API",
            **kwargs,
        )
        self.logger = get_logger("ETL.SemanticScholar")
        # Search for recent AI/LLM papers
        self.endpoints = {
            "search": "https://api.semanticscholar.org/graph/v1/paper/search?query=large+language+models+OR+machine+learning&limit=50&fields=title,authors,abstract,publicationDate,citationCount,url,isOpenAccess"
        }
        self.proxy_manager = ProxyManager()

    def extract(self) -> list[dict[str, Any]]:
        """Extract data from Semantic Scholar Graph API."""
        self.logger.info("Extracting data from Semantic Scholar API")
        extracted_data = []

        try:
            session = self.proxy_manager.get_session(retries=3, backoff_factor=1.5)
            headers = {"User-Agent": "WatchtowerBot/1.0 (Research AI Monitor)"}
            
            # Extract Papers
            res_papers = session.get(self.endpoints["search"], headers=headers, timeout=30)
            res_papers.raise_for_status()
            
            papers_data = res_papers.json().get("data", [])
            for p in papers_data:
                p["data_type"] = "paper"
                extracted_data.append(p)
                
            self.metrics.records_extracted += len(papers_data)

        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            self.metrics.records_failed += 1

        return extracted_data

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform Semantic Scholar API data."""
        self.logger.info(f"Transforming {len(data)} Semantic Scholar records")
        transformed = []
        for record in data:
            try:
                # Formatting authors
                authors = [a.get("name") for a in record.get("authors", []) if a.get("name")]
                
                transformed.append({
                    "id": record.get("paperId"),
                    "title": record.get("title"),
                    "abstract": record.get("abstract"),
                    "url": record.get("url"),
                    "authors": authors,
                    "published": record.get("publicationDate"),
                    "citations": record.get("citationCount", 0),
                    "is_open_access": record.get("isOpenAccess", False),
                    "data_type": "paper"
                })
                self.metrics.records_transformed += 1
            except Exception as e:
                self.logger.error(f"Transform failed for record: {e}")
                self.metrics.records_failed += 1
            
        return transformed

    def load(self, data: list[dict[str, Any]]) -> None:
        """Load Semantic Scholar data to output directory."""
        if not data:
            self.logger.info("No Semantic Scholar data to load.")
            return

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"semanticscholar_{timestamp}.json"
        latest_file = self.output_dir / "semanticscholar_latest.json"

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            with open(latest_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            
            self.metrics.records_loaded = len(data)
            self.logger.info(f"Successfully saved {len(data)} records to {latest_file}")
            
        except OSError as e:
            self.logger.error(f"Failed to save info to {output_file}: {e}")
            raise LoadError(f"Failed to save data: {e}", destination=str(output_file), destination_type="file") from e
        except Exception as e:
            raise LoadError(f"Unexpected error: {e}", destination=str(output_file), destination_type="file") from e

if __name__ == "__main__":
    etl = SemanticScholarETL()
    etl.run()
