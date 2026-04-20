"""PapersWithCode ETL Implementation.

Monitors AI implementation reproducibility via PapersWithCode API.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from src.etl.base import BaseETL
from src.exceptions.etl import LoadError
from src.utils.logging import get_logger
from src.etl.proxy_manager import ProxyManager


class PapersWithCodeETL(BaseETL):
    """PapersWithCode ETL for tracking AI reproducibility."""

    def __init__(self, **kwargs):
        """Initialize PapersWithCode ETL."""
        super().__init__(
            name="paperswithcode",
            description="Tracks AI research implementation and reproducibility",
            **kwargs,
        )
        self.logger = get_logger("ETL.PapersWithCode")
        self.endpoints = {
            "papers": "https://paperswithcode.com/api/v1/papers/?items_per_page=50",
            "datasets": "https://paperswithcode.com/api/v1/datasets/?items_per_page=50",
        }
        self.proxy_manager = ProxyManager()

    def extract(self) -> list[dict[str, Any]]:
        """Extract data from PapersWithCode REST API."""
        self.logger.info("Extracting data from PapersWithCode API")
        extracted_data = []

        try:
            session = self.proxy_manager.get_session(retries=3, backoff_factor=1.5)
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Watchtower/1.0"}
            
            # Extract Papers
            res_papers = session.get(self.endpoints["papers"], headers=headers, timeout=30)
            res_papers.raise_for_status()
            papers_data = res_papers.json().get("results", [])
            for p in papers_data:
                p["data_type"] = "paper"
                extracted_data.append(p)
            self.metrics.records_extracted += len(papers_data)
            
            # Extract Datasets
            res_datasets = session.get(self.endpoints["datasets"], headers=headers, timeout=30)
            res_datasets.raise_for_status()
            datasets_data = res_datasets.json().get("results", [])
            for d in datasets_data:
                d["data_type"] = "dataset"
                extracted_data.append(d)
            self.metrics.records_extracted += len(datasets_data)

        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            self.metrics.records_failed += 1

        return extracted_data

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform PapersWithCode API data."""
        self.logger.info(f"Transforming {len(data)} PapersWithCode records")
        transformed = []
        for record in data:
            try:
                dtype = record.get("data_type")
                if dtype == "paper":
                    transformed.append({
                        "id": record.get("id"),
                        "title": record.get("title"),
                        "abstract": record.get("abstract"),
                        "url_pdf": record.get("url_pdf"),
                        "url_abs": record.get("url_abs"),
                        "authors": record.get("authors", []),
                        "published": record.get("published"),
                        "proceeding": record.get("proceeding"),
                        "data_type": "paper"
                    })
                elif dtype == "dataset":
                    transformed.append({
                        "id": record.get("id"),
                        "name": record.get("name"),
                        "url": record.get("url"),
                        "introduction_date": record.get("introduction_date"),
                        "data_type": "dataset"
                    })
                self.metrics.records_transformed += 1
            except Exception as e:
                self.logger.error(f"Transform failed for record: {e}")
                self.metrics.records_failed += 1
            
        return transformed

    def load(self, data: list[dict[str, Any]]) -> None:
        """Load PapersWithCode data to output directory."""
        if not data:
            self.logger.info("No PapersWithCode data to load.")
            return

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"paperswithcode_{timestamp}.json"
        latest_file = self.output_dir / "paperswithcode_latest.json"

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
    etl = PapersWithCodeETL()
    etl.run()
