#!/usr/bin/env python3
"""
Script to run the 4chan Generals ETL from the project root.
"""

import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def main():
    """Run the 4chan Generals ETL."""
    try:
        from etl.fourchan.fourchan_generals_etl import FourChanGeneralsETL
        
        print("Starting 4chan Generals ETL...")
        etl = FourChanGeneralsETL()
        metrics = etl.run()
        
        print(f"ETL completed successfully!")
        print(f"Records extracted: {metrics.records_extracted}")
        print(f"Records transformed: {metrics.records_transformed}")
        print(f"Records loaded: {metrics.records_loaded}")
        print(f"Duration: {metrics.duration_seconds:.2f} seconds")
        
    except Exception as e:
        print(f"Error running ETL: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 