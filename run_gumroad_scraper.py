#!/usr/bin/env python3
"""
Gumroad Free Products Scraper Runner

This script runs the Gumroad scraper ETL process to collect free products
from Gumroad's discover page using 'from' parameter pagination.
"""

import sys
import argparse
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.etl.goldigging.gumroad_scraper_etl import GumroadScraperETL
from src.utils.logging import get_logger

logger = get_logger("GumroadScraperRunner")


def main():
    """Main function to run the Gumroad scraper."""
    parser = argparse.ArgumentParser(
        description="Gumroad Free Products Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Regular run (500 items)
  python run_gumroad_scraper.py
  
  # First run (10000 items)
  python run_gumroad_scraper.py --first-run
  
  # Custom item limit
  python run_gumroad_scraper.py --max-items 1000
  
  # Debug mode
  python run_gumroad_scraper.py --debug
        """
    )
    
    parser.add_argument(
        "--first-run", 
        action="store_true", 
        help="Run first-time scraping (10000 items instead of 500)"
    )
    parser.add_argument(
        "--max-items", 
        type=int, 
        help="Override maximum items to scrape (default: 500 normal, 10000 first-run)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug logging"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Run without saving data (for testing)"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    if args.debug:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Debug logging enabled")
    
    # Display configuration
    max_items = args.max_items or (10000 if args.first_run else 500)
    run_type = "first run" if args.first_run else "regular run"
    
    logger.info(f"Starting Gumroad scraper - {run_type}")
    logger.info(f"Max items: {max_items}")
    if args.dry_run:
        logger.info("Dry run mode: No data will be saved")
    
    try:
        # Create and run the scraper
        scraper = GumroadScraperETL(
            first_run=args.first_run,
            max_items=args.max_items
        )
        
        if args.dry_run:
            logger.info("Dry run mode - would normally run scraper here")
            logger.info("Scraper configuration:")
            logger.info(f"  - Name: {scraper.name}")
            logger.info(f"  - Description: {scraper.description}")
            logger.info(f"  - Max items: {scraper.max_items}")
            logger.info(f"  - Base URL: {scraper.base_url}")
            logger.info(f"  - Checkpointing: {scraper.enable_checkpointing}")
            return
        
        # Run the scraper
        metrics = scraper.run()
        
        # Display results
        logger.info("=" * 50)
        logger.info("SCRAPER COMPLETED SUCCESSFULLY")
        logger.info("=" * 50)
        logger.info(f"Duration: {metrics.duration_seconds:.2f} seconds")
        logger.info(f"Records extracted: {metrics.records_extracted}")
        logger.info(f"Records transformed: {metrics.records_transformed}")
        logger.info(f"Records loaded: {metrics.records_loaded}")
        logger.info(f"Records failed: {metrics.records_failed}")
        logger.info(f"Success rate: {metrics.success_rate:.2f}%")
        
        if metrics.records_loaded > 0:
            logger.info(f"Data saved to: {scraper.output_dir}")
            logger.info("Files created:")
            logger.info("  - gumroad_free_products.json")
            logger.info("  - gumroad_free_products.csv")
            logger.info("  - scavenging format file")
        
    except KeyboardInterrupt:
        logger.warning("Scraper interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Scraper failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 