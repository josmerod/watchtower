"""Run All Deals ETL Script

This script runs all deal ETL modules to collect comprehensive data
from bundle sites, music platforms, and bargain hunting sources.

Usage:
    python src/etl/deals/run_all_deals.py
"""

import os
import sys
from datetime import datetime

# Add the project root to the path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

from src.etl.deals.bargain_hunter_etl import BargainHunterETL
from src.etl.deals.book_deals_etl import BookDealsETL
from src.etl.deals.bundle_deals_etl import BundleDealsETL
from src.etl.deals.crypto_finance_deals_etl import CryptoFinanceDealsETL
from src.etl.deals.educational_deals_etl import EducationalDealsETL
from src.etl.deals.fashion_retail_deals_etl import FashionRetailDealsETL
from src.etl.deals.hardware_tech_deals_etl import HardwareTechDealsETL
from src.etl.deals.health_fitness_deals_etl import HealthFitnessDealsETL
from src.etl.deals.music_deals_etl import MusicDealsETL
from src.etl.deals.software_deals_etl import SoftwareDealsETL
from src.etl.deals.travel_deals_etl import TravelDealsETL
from src.utils.logging import get_logger

# Initialize logger
logger = get_logger("AllDealsETL")


def run_all_deals_etl():
    """Run all deal ETL processes."""
    start_time = datetime.now()
    logger.info("Starting comprehensive deals data collection...")

    etl_modules = [
        ("Bundle Deals", BundleDealsETL),
        ("Music Deals", MusicDealsETL),
        ("Bargain Hunter", BargainHunterETL),
        ("Educational Deals", EducationalDealsETL),
        ("Book Deals", BookDealsETL),
        ("Software Deals", SoftwareDealsETL),
        ("Travel Deals", TravelDealsETL),
        ("Crypto & Finance", CryptoFinanceDealsETL),
        ("Fashion & Retail", FashionRetailDealsETL),
        ("Health & Fitness", HealthFitnessDealsETL),
        ("Hardware & Tech", HardwareTechDealsETL),
    ]

    results = {}
    total_records = 0

    for name, etl_class in etl_modules:
        try:
            logger.info(f"\n{'=' * 50}")
            logger.info(f"Running {name} ETL...")
            logger.info(f"{'=' * 50}")

            etl = etl_class()
            metrics = etl.run()

            # Get record count from the ETL metrics
            record_count = metrics.records_loaded

            if metrics.is_successful or record_count > 0:
                results[name] = {"status": "success", "records": record_count}
                total_records += record_count
                logger.info(
                    f"[OK] {name} ETL completed successfully ({record_count} records)"
                )
            else:
                results[name] = {"status": "failed", "records": 0}
                logger.error(f"[FAIL] {name} ETL failed")

        except Exception as e:
            results[name] = {"status": "error", "records": 0}
            logger.error(f"[ERROR] {name} ETL error: {e}")

    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    logger.info(f"\n{'=' * 60}")
    logger.info("DEALS ETL SUMMARY")
    logger.info(f"{'=' * 60}")
    logger.info(f"Total execution time: {duration:.2f} seconds")
    logger.info(f"Total records collected: {total_records}")
    logger.info("")

    for name, result in results.items():
        status_symbol = "[OK]" if result["status"] == "success" else "[FAIL]"
        logger.info(
            f"{status_symbol} {name}: {result['status'].upper()} ({result['records']} records)"
        )

    successful_etls = sum(1 for r in results.values() if r["status"] == "success")
    logger.info(f"\nSuccess rate: {successful_etls}/{len(etl_modules)} ETL modules")

    if successful_etls == len(etl_modules):
        logger.info("SUCCESS: All deal ETL processes completed successfully!")
        logger.info("Data is ready for the dashboard at:")
        logger.info("  - Bundle deals: data/deals/bundle_deals.json")
        logger.info("  - Music deals: data/deals/music_deals.json")
        logger.info("  - Bargain deals: data/deals/bargain_deals.json")
        logger.info("  - Educational deals: data/deals/educational_deals.json")
        logger.info("  - Book deals: data/deals/book_deals.json")
        logger.info("  - Software deals: data/deals/software_deals.json")
        logger.info("  - Travel deals: data/deals/travel_deals.json")
        logger.info("  - Crypto & Finance deals: data/deals/crypto_finance_deals.json")
        logger.info("  - Fashion & Retail deals: data/deals/fashion_retail_deals.json")
        logger.info("  - Health & Fitness deals: data/deals/health_fitness_deals.json")
        logger.info("  - Hardware & Tech deals: data/deals/hardware_tech_deals.json")
        return True
    else:
        logger.warning("WARNING: Some ETL processes failed. Check logs for details.")
        return False


if __name__ == "__main__":
    success = run_all_deals_etl()
    sys.exit(0 if success else 1)
