#!/usr/bin/env python3
"""Script to run the AllKeyShop ETL process.
This script extracts game deals from AllKeyShop with different sorting criteria.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from etl.games.games_get_allkeyshop import get_allkeyshop
from utils.logging import get_logger


def main():
    """Main function to run AllKeyShop ETL."""
    logger = get_logger("AllKeyShopRunner")

    logger.info("🎮 Starting AllKeyShop ETL process...")
    logger.info(
        "This will scrape game deals from AllKeyShop with different sorting criteria:"
    )
    logger.info("  - Deal score (best deals first)")
    logger.info("  - Default sorting (newest deals)")
    logger.info("  - Price ascending (cheapest first, quality filtered)")
    logger.info("")
    logger.info("⏱️  This may take a few minutes depending on the number of pages...")

    try:
        # Run the ETL
        metrics = get_allkeyshop()

        # Display results
        logger.info("✅ AllKeyShop ETL completed successfully!")
        logger.info("📊 Metrics:")
        logger.info(f"  - Records extracted: {metrics.records_extracted}")
        logger.info(f"  - Records transformed: {metrics.records_transformed}")
        logger.info(f"  - Records loaded: {metrics.records_loaded}")
        logger.info(f"  - Records failed: {metrics.records_failed}")
        logger.info(f"  - Duration: {metrics.duration_seconds:.2f} seconds")
        logger.info(f"  - Success rate: {metrics.success_rate:.1f}%")

        if metrics.records_loaded > 0:
            logger.info("")
            logger.info("🎯 Data saved to:")
            logger.info("  - data/allkeyshop_games/output/latest_allkeyshop_games.json")
            logger.info("  - Timestamped files for historical tracking")
            logger.info("  - Filtered datasets (best deals, budget games, etc.)")
            logger.info("")
            logger.info("🚀 You can now view the data in the Streamlit dashboard!")
            logger.info("   Run: streamlit run src/web/fullstreamlit/app.py")
            logger.info("   Then go to the '🎯 AllKeyShop Deals' tab")
        else:
            logger.warning("⚠️  No data was loaded. Check the logs for errors.")

    except Exception as e:
        logger.error(f"❌ AllKeyShop ETL failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
