"""Verification script for Developer News ETL."""

import logging
import json
from pathlib import Path
from src.etl.developer_news.developer_news_etl import DeveloperNewsETL

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Starting Developer News ETL Verification...")
    
    etl = DeveloperNewsETL()
    
    # 1. Run Pipeline
    etl.enable_deduplication = False # Disable deduplication to test enrichment in isolation
    try:
        metrics = etl.run()
        print(f"ETL Run Completed. Success: {metrics.is_successful}")
    except Exception as e:
        print(f"ETL Run Failed: {e}")
        exit(1)
        
    if metrics.records_loaded > 0:
        # Check output file
        output_dir = Path("data/developer_news/output")
        latest_file = output_dir / "latest_news.json"
        
        if latest_file.exists():
            with open(latest_file, "r") as f:
                data = json.load(f)
                first_item = data[0]
                print(f"\nVerifying First Item: {first_item.get('title')}")
                ai_sum = first_item.get('ai_summary') or "N/A"
                print(f"AI Summary: {ai_sum[:50]}...")
                print(f"AI Insight: {first_item.get('ai_insight')}")
                print(f"AI Tags: {first_item.get('ai_tags')}")
                
                if first_item.get("ai_summary") and first_item.get("ai_insight"):
                    print("✅ PASS: AI Enrichment Successful")
                else:
                    print("❌ FAIL: AI Enrichment Missing")
        else:
            print("❌ FAIL: No output file found")
    else:
        print("⚠️ WARNING: No records loaded (API might be down or rate limited)")
    # We can check if file exists, but simple run log is enough for first pass.
    print("Verification Done. Check 'data/developer_news' for output.")
