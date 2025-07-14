#!/usr/bin/env python3
"""
Run both Valencia Events and Cinema ETL processes.

This script demonstrates the refactored Valencia ETLs:
1. Valencia Events ETL - Extracts events from visitvalencia.com
2. Enhanced Cinema ETL - Extracts movie showtimes from eCartelera.com

Usage:
    python run_valencia_etls.py
    or
    uv run python run_valencia_etls.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.etl.news.valencia_events_etl import ValenciaEventsETL
from src.etl.entertainment.cinema_ecartelera_improved_etl import CinemaECarteleraImprovedETL
from src.utils.logging import get_logger

logger = get_logger("ValenciaETLRunner")


def run_valencia_events_etl():
    """Run the Valencia Events ETL."""
    logger.info("=" * 60)
    logger.info("🌆 Starting Valencia Events ETL")
    logger.info("=" * 60)
    
    try:
        etl = ValenciaEventsETL()
        metrics = etl.run()
        
        logger.info("✅ Valencia Events ETL completed successfully!")
        logger.info(f"📊 Results: {metrics.records_extracted} extracted → {metrics.records_transformed} transformed → {metrics.records_loaded} loaded")
        logger.info(f"⏱️  Duration: {metrics.duration_seconds:.1f} seconds")
        logger.info(f"📄 Data saved to: data/valencia_events/output/")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Valencia Events ETL failed: {e}")
        return False


def run_cinema_etl():
    """Run the Enhanced Cinema ETL."""
    logger.info("=" * 60)
    logger.info("🎬 Starting Enhanced Cinema ETL")
    logger.info("=" * 60)
    
    try:
        etl = CinemaECarteleraImprovedETL()
        metrics = etl.run()
        
        logger.info("✅ Enhanced Cinema ETL completed successfully!")
        logger.info(f"📊 Results: {metrics.records_extracted} extracted → {metrics.records_transformed} transformed → {metrics.records_loaded} loaded")
        logger.info(f"⏱️  Duration: {metrics.duration_seconds:.1f} seconds")
        logger.info(f"📄 Data saved to: data/cinema_ecartelera_improved/output/")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Enhanced Cinema ETL failed: {e}")
        return False


def main():
    """Run both Valencia ETL processes."""
    logger.info("🚀 Starting Valencia ETL Suite")
    logger.info("This will run both Valencia Events and Cinema ETL processes")
    logger.info("")
    
    results = {}
    
    # Run Valencia Events ETL
    results['valencia_events'] = run_valencia_events_etl()
    
    logger.info("")
    
    # Run Cinema ETL
    results['cinema'] = run_cinema_etl()
    
    # Final summary
    logger.info("=" * 60)
    logger.info("📈 FINAL SUMMARY")
    logger.info("=" * 60)
    
    logger.info(f"Valencia Events ETL: {'✅ SUCCESS' if results['valencia_events'] else '❌ FAILED'}")
    logger.info(f"Enhanced Cinema ETL: {'✅ SUCCESS' if results['cinema'] else '❌ FAILED'}")
    
    if all(results.values()):
        logger.info("🎉 All ETL processes completed successfully!")
        logger.info("🌐 You can now view the data in the dashboard at: http://localhost:7777")
        logger.info("📂 Navigate to the 'Valencia Events' tab to see both Events and Cinema subtabs")
    else:
        logger.info("⚠️  Some ETL processes failed. Check the logs above for details.")
    
    logger.info("")
    logger.info("📊 Data Locations:")
    logger.info("  • Valencia Events: data/valencia_events/output/valencia_events.json")
    logger.info("  • Cinema Showtimes: data/cinema_ecartelera_improved/output/cinema_showtimes.json")
    logger.info("")


if __name__ == "__main__":
    main()