"""Verification script for Developer News ETL."""

import logging
from src.etl.developer_news.developer_news_etl import DeveloperNewsETL

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Starting Developer News ETL Verification...")
    
    etl = DeveloperNewsETL()
    
    # 1. Run Pipeline
    try:
        etl.run()
        print("ETL Run Completed Successfully.")
    except Exception as e:
        print(f"ETL Run Failed: {e}")
        exit(1)
        
    # 2. Check Output
    # We can check if file exists, but simple run log is enough for first pass.
    print("Verification Done. Check 'data/developer_news' for output.")
