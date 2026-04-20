"""CoinGecko API ETL Implementation.

Extracts real-time cryptocurrency snapshots and market cap rankings.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from src.etl.base import BaseETL
from src.exceptions.etl import LoadError
from src.utils.logging import get_logger
from src.etl.proxy_manager import ProxyManager
from src.models.crypto_model import CryptoAsset


class CoinGeckoETL(BaseETL):
    """CoinGecko ETL for monitoring cryptocurrency altcoin trends."""

    def __init__(self, **kwargs):
        """Initialize CoinGecko ETL."""
        super().__init__(
            name="coingecko",
            description="Tracks cryptocurrency market assets from CoinGecko API",
            **kwargs,
        )
        self.logger = get_logger("ETL.CoinGecko")
        self.endpoints = {
            "markets": "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1&sparkline=false"
        }
        self.proxy_manager = ProxyManager()

    def extract(self) -> list[dict[str, Any]]:
        """Extract data from CoinGecko REST API."""
        self.logger.info("Extracting data from CoinGecko API")
        extracted_data = []

        try:
            session = self.proxy_manager.get_session(retries=3)
            headers = {
                "User-Agent": "WatchtowerBot/1.0 (Crypto Market Sentinel)",
                "Accept": "application/json"
            }
            res = session.get(self.endpoints["markets"], headers=headers, timeout=30)
            res.raise_for_status()
            
            markets_data = res.json()
            for c in markets_data:
                c["data_type"] = "crypto_asset"
                extracted_data.append(c)
                
            self.metrics.records_extracted += len(markets_data)

        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            self.metrics.records_failed += 1

        return extracted_data

    def transform(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Transform CoinGecko API data via Pydantic model validation."""
        self.logger.info(f"Transforming {len(data)} CoinGecko records")
        transformed = []
        for record in data:
            try:
                # Pydantic native schema validation
                asset = CryptoAsset(**record)
                transformed.append(asset.model_dump(mode="json"))
                self.metrics.records_transformed += 1
            except Exception as e:
                self.logger.error(f"Transform failed for record {record.get('id')}: {e}")
                self.metrics.records_failed += 1
            
        return transformed

    def load(self, data: list[dict[str, Any]]) -> None:
        """Load CoinGecko data to output directory."""
        if not data:
            self.logger.info("No CoinGecko data to load.")
            return

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"coingecko_{timestamp}.json"
        latest_file = self.output_dir / "coingecko_latest.json"

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            with open(latest_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            
            self.metrics.records_loaded = len(data)
            self.logger.info(f"Successfully saved {len(data)} items to {latest_file}")
            
        except OSError as e:
            self.logger.error(f"Failed to save info: {e}")
            raise LoadError(f"Failed to save data: {e}", destination=str(output_file), destination_type="file") from e
        except Exception as e:
            raise LoadError(f"Unexpected error: {e}", destination=str(output_file), destination_type="file") from e

if __name__ == "__main__":
    etl = CoinGeckoETL()
    etl.run()
