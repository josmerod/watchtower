#!/usr/bin/env python3
"""Simple import test to debug the hanging issue."""

import sys
from pathlib import Path

# Add the src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("🔍 Testing simple import...")

try:
    print("Step 1: Importing ETL class...")
    from etl.events.tech_conference_etl import TechConferenceETL
    print("✅ Import successful")
    
    print("Step 2: Creating ETL instance...")
    etl = TechConferenceETL(name="test")
    print("✅ Instance created")
    
    print("Step 3: Checking data sources...")
    print(f"Data sources: {list(etl.data_sources.keys())}")
    
    print("✅ Simple import test completed successfully!")
    
except Exception as e:
    print(f"❌ Import test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("🎉 No hanging detected in import phase") 