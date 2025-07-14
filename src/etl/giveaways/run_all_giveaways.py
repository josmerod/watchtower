"""Run All Giveaways ETL Script

This script runs all giveaway ETL modules to collect comprehensive data
from Reddit, free games platforms, and educational sources.

Usage:
    python src/etl/giveaways/run_all_giveaways.py
"""

import os
import sys
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from src.utils.logging import get_logger
from src.etl.giveaways.reddit_giveaways_etl import RedditGiveawaysETL
from src.etl.giveaways.free_games_etl import FreeGamesETL
from src.etl.giveaways.free_courses_etl import FreeCoursesETL

# Initialize logger
logger = get_logger("AllGiveawaysETL")

def run_all_giveaways_etl():
    """Run all giveaway ETL processes."""
    start_time = datetime.now()
    logger.info("Starting comprehensive giveaways data collection...")
    
    etl_modules = [
        ("Reddit Giveaways", RedditGiveawaysETL),
        ("Free Games", FreeGamesETL),
        ("Free Courses", FreeCoursesETL)
    ]
    
    results = {}
    total_records = 0
    
    for name, etl_class in etl_modules:
        try:
            logger.info(f"\n{'='*50}")
            logger.info(f"Running {name} ETL...")
            logger.info(f"{'='*50}")
            
            etl = etl_class()
            success = etl.run()
            
            if success:
                # Get record count from the ETL metrics if available
                record_count = getattr(etl, '_last_load_count', 0)
                results[name] = {"status": "success", "records": record_count}
                total_records += record_count
                logger.info(f"✅ {name} ETL completed successfully ({record_count} records)")
            else:
                results[name] = {"status": "failed", "records": 0}
                logger.error(f"❌ {name} ETL failed")
                
        except Exception as e:
            results[name] = {"status": "error", "records": 0}
            logger.error(f"❌ {name} ETL error: {e}")
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info(f"\n{'='*60}")
    logger.info("GIVEAWAYS ETL SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total execution time: {duration:.2f} seconds")
    logger.info(f"Total records collected: {total_records}")
    logger.info("")
    
    for name, result in results.items():
        status_emoji = "✅" if result["status"] == "success" else "❌"
        logger.info(f"{status_emoji} {name}: {result['status'].upper()} ({result['records']} records)")
    
    successful_etls = sum(1 for r in results.values() if r["status"] == "success")
    logger.info(f"\nSuccess rate: {successful_etls}/{len(etl_modules)} ETL modules")
    
    if successful_etls == len(etl_modules):
        logger.info("🎉 All giveaway ETL processes completed successfully!")
        logger.info("Data is ready for the dashboard at:")
        logger.info("  - Reddit giveaways: data/giveaways/reddit_giveaways.json")
        logger.info("  - Free games: data/giveaways/free_games.json") 
        logger.info("  - Free courses: data/giveaways/free_courses.json")
        return True
    else:
        logger.warning("⚠️ Some ETL processes failed. Check logs for details.")
        return False

if __name__ == "__main__":
    success = run_all_giveaways_etl()
    sys.exit(0 if success else 1)