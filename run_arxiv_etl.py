#!/usr/bin/env python
"""
Script to run the ArXiv ETL pipeline to collect and process AI/ML research papers.
"""
import sys
import os
import argparse
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.etl.arxiv.arxiv_etl import ArxivETL
from src.utils.logging import get_logger

def main():
    """Run the ArXiv ETL pipeline with command line arguments."""
    logger = get_logger("run_arxiv_etl")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run ArXiv ETL pipeline for AI/ML papers")
    parser.add_argument("--days", type=int, default=7, help="Number of days back to fetch papers (default: 7)")
    parser.add_argument("--max-results", type=int, default=100, help="Maximum number of papers to fetch (default: 100)")
    parser.add_argument("--clusters", type=int, default=8, help="Number of clusters for paper classification (default: 8)")
    args = parser.parse_args()
    
    # Log start
    logger.info(f"Starting ArXiv ETL run at {datetime.now()}")
    logger.info(f"Parameters: days_back={args.days}, max_results={args.max_results}, clusters={args.clusters}")
    
    # Initialize and run the ETL
    try:
        etl = ArxivETL(
            days_back=args.days,
            max_results=args.max_results,
            n_clusters=args.clusters
        )
        etl.run()
        logger.info("ArXiv ETL run completed successfully")
    except Exception as e:
        logger.error(f"ArXiv ETL run failed: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 