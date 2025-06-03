#!/usr/bin/env python3
"""Quick test script for Valencia tech conference ETL - focuses on mock data."""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add the src directory to path
from etl.events.tech_conference_etl import TechConferenceETL


def test_quick_valencia_etl():
    """Quick test focusing on mock data and basic functionality."""
    print("⚡ Quick Valencia Tech Conference ETL Test")
    print("=" * 50)
    
    # Initialize ETL with limited real feeds
    etl = TechConferenceETL(
        name="valencia_tech_quick_test",
        max_events_per_source=3,  # Very limited for speed
        days_ahead=180
    )
    
    # Disable potentially problematic sources for quick test
    quick_sources = {
        "spanish_tech_events": True,  # Has good mock data
        "european_tech_conferences": False,  # May have slow feeds
        "global_virtual_events": True,  # Has good mock data  
        "academic_research_events": False,  # May have slow feeds
        "tech_news_events": False,  # May have slow feeds
        "open_source_events": False,  # May have slow feeds
        "developer_platforms": False,  # May have slow feeds
        "valencia_local_sources": True   # Local mock data
    }
    
    # Update source configuration for speed
    for source_name, enabled in quick_sources.items():
        if source_name in etl.data_sources:
            etl.data_sources[source_name]["enabled"] = enabled
    
    print("🔍 Quick test configuration:")
    enabled_sources = [name for name, enabled in quick_sources.items() if enabled]
    print(f"   Enabled sources: {', '.join(enabled_sources)}")
    print()
    
    try:
        # Test extraction (mostly mock data)
        print("📥 Starting quick extraction...")
        raw_events = etl.extract()
        print(f"✅ Extracted {len(raw_events)} raw events")
        
        # Show breakdown by source
        source_counts = {}
        for event in raw_events:
            source = event.get("source_name", "unknown")
            source_counts[source] = source_counts.get(source, 0) + 1
        
        print("\n📊 Events by source:")
        for source, count in sorted(source_counts.items()):
            print(f"   {source}: {count} events")
        
        if len(raw_events) == 0:
            print("⚠️  No events extracted - this indicates a problem with the mock data")
            return False
        
        # Test transformation
        print("\n🔄 Testing transformation...")
        transformed_events = etl.transform(raw_events)
        print(f"✅ Transformed {len(transformed_events)} events")
        
        # Analyze results
        valencia_local = sum(1 for e in transformed_events 
                           if not e.is_virtual and e.venue and "valencia" in str(e.venue.city).lower())
        virtual_events = sum(1 for e in transformed_events if e.is_virtual)
        nearby_events = len(transformed_events) - valencia_local - virtual_events
        
        print(f"\n📍 Event distribution:")
        print(f"   Valencia local: {valencia_local}")
        print(f"   Virtual/Online: {virtual_events}")
        print(f"   Nearby locations: {nearby_events}")
        print(f"   Total: {len(transformed_events)}")
        
        # Show sample events
        print(f"\n📋 Sample events:")
        for i, event in enumerate(transformed_events[:5]):
            location = "Virtual" if event.is_virtual else f"{event.venue.city if event.venue else 'Unknown'}"
            print(f"   {i+1}. {event.name}")
            print(f"      📅 {event.start_date}")
            print(f"      📍 {location}")
            print(f"      🏷️  {event.event_type}")
            print(f"      ⭐ Quality: {event.quality_score:.1f}")
            print()
        
        # Test recommendations quickly
        print("🎯 Testing recommendations...")
        valencia_profile = {
            "interests": ["python", "machine learning", "startup"],
            "location": "valencia, spain",
            "budget": 100.0
        }
        
        recommendations = etl.generate_event_recommendations(valencia_profile, transformed_events)
        print(f"✅ Generated {len(recommendations)} recommendations")
        
        if recommendations:
            print(f"\n🌟 Top recommendations:")
            for i, rec in enumerate(recommendations[:3]):
                event = rec["event"]
                score = rec["recommendation_score"]
                print(f"   {i+1}. {event['name']} (Score: {score:.1f})")
        
        # Quick load test
        print(f"\n💾 Testing data save...")
        etl.load(transformed_events)
        print("✅ Data saved successfully")
        
        print(f"\n✅ Quick test completed successfully!")
        print(f"📈 Results: {len(transformed_events)} events processed")
        
        # Validation checks
        if len(transformed_events) < 10:
            print("⚠️  Warning: Less than 10 events found - may need more data sources")
        
        if valencia_local == 0:
            print("⚠️  Warning: No Valencia local events found")
        
        if virtual_events == 0:
            print("⚠️  Warning: No virtual events found")
        
        return True
        
    except Exception as e:
        print(f"❌ Quick test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_quick_valencia_etl()
    sys.exit(0 if success else 1) 