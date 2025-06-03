#!/usr/bin/env python3
"""Test script for new ETLs implemented from brainstorm ideas.

This script tests the following new ETLs:
1. Meme Economics Tracker - Financial analysis of internet memes
2. Enhanced Free Games Intelligence - Comprehensive free game discovery
3. ADHD-Friendly Location Intelligence - Neurodivergent-friendly spaces
"""

import sys
import os
import asyncio
from datetime import datetime

# Add the project root to the path
def test_meme_economics_etl():
    """Test the Meme Economics ETL."""
    print("🐸 Testing Meme Economics ETL...")
    print("=" * 50)
    
    try:
        from src.etl.entertainment.meme_economics_etl import run_meme_economics_etl
        
        metrics = run_meme_economics_etl()
        
        print(f"✅ Meme Economics ETL completed successfully!")
        print(f"   Records extracted: {metrics.records_extracted}")
        print(f"   Records transformed: {metrics.records_transformed}")
        print(f"   Records loaded: {metrics.records_loaded}")
        print(f"   Duration: {metrics.duration_seconds:.2f} seconds")
        print(f"   Success rate: {metrics.success_rate:.1f}%")
        print("   📊 Meme market analysis complete! Check data/meme_economics/output/")
        
    except Exception as e:
        print(f"❌ Meme Economics ETL failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def test_enhanced_free_games_etl():
    """Test the Enhanced Free Games ETL."""
    print("🎮 Testing Enhanced Free Games ETL...")
    print("=" * 50)
    
    try:
        from src.etl.games.enhanced_free_games_etl import run_enhanced_free_games_etl
        
        metrics = run_enhanced_free_games_etl()
        
        print(f"✅ Enhanced Free Games ETL completed successfully!")
        print(f"   Records extracted: {metrics.records_extracted}")
        print(f"   Records transformed: {metrics.records_transformed}")
        print(f"   Records loaded: {metrics.records_loaded}")
        print(f"   Duration: {metrics.duration_seconds:.2f} seconds")
        print(f"   Success rate: {metrics.success_rate:.1f}%")
        print("   🎯 Free games intelligence ready! Check data/enhanced_free_games/output/")
        
    except Exception as e:
        print(f"❌ Enhanced Free Games ETL failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def test_adhd_friendly_locations_etl():
    """Test the ADHD-Friendly Locations ETL."""
    print("🧠 Testing ADHD-Friendly Locations ETL...")
    print("=" * 50)
    
    try:
        from src.etl.neurodivergent.adhd_friendly_locations_etl import run_adhd_friendly_locations_etl
        
        metrics = run_adhd_friendly_locations_etl()
        
        print(f"✅ ADHD-Friendly Locations ETL completed successfully!")
        print(f"   Records extracted: {metrics.records_extracted}")
        print(f"   Records transformed: {metrics.records_transformed}")
        print(f"   Records loaded: {metrics.records_loaded}")
        print(f"   Duration: {metrics.duration_seconds:.2f} seconds")
        print(f"   Success rate: {metrics.success_rate:.1f}%")
        print("   ✨ Neurodivergent location intelligence ready! Check data/adhd_friendly_locations/output/")
        
    except Exception as e:
        print(f"❌ ADHD-Friendly Locations ETL failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()


def main():
    """Run all new ETL tests."""
    print("🚀 Testing New Watchtower ETLs")
    print("Implementing random ideas from the brainstorm document!")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test all new ETLs
    test_meme_economics_etl()
    test_enhanced_free_games_etl()
    test_adhd_friendly_locations_etl()
    
    print("🎉 All ETL tests completed!")
    print("=" * 60)
    print("Summary of implemented ideas:")
    print("1. 📈 Meme Economics Tracker - Track memes like stock market")
    print("2. 🎮 Enhanced Free Games Intelligence - Never miss free games")
    print("3. 🧠 ADHD-Friendly Locations - Neurodivergent-friendly spaces")
    print()
    print("These ETLs follow the established Watchtower patterns and include:")
    print("- Comprehensive data extraction with mock implementations")
    print("- Advanced transformation with intelligent analysis")
    print("- Structured data loading with specialized datasets")
    print("- Proper error handling and logging")
    print("- Quality metrics and recommendation engines")
    print()
    print("Next steps:")
    print("- Run ETLs individually: python -m src.etl.entertainment.meme_economics_etl")
    print("- Add to main ETL scheduler")
    print("- Integrate with Streamlit dashboard")
    print("- Add real API integrations")


if __name__ == "__main__":
    main() 