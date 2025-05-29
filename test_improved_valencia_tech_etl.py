#!/usr/bin/env python3
"""Test script for the improved Valencia tech conference ETL."""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add the src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from etl.events.tech_conference_etl import TechConferenceETL


def test_improved_etl():
    """Test the improved tech conference ETL with better RSS handling."""
    print("🧪 Testing Improved Valencia Tech Conference ETL")
    print("=" * 60)
    
    # Initialize ETL
    etl = TechConferenceETL(
        name="valencia_tech_test_improved",
        max_events_per_source=5,  # Reduced for testing
        days_ahead=180
    )
    
    print(f"📍 Target locations:")
    print(f"   Primary: {etl.target_locations['primary'][:5]}...")
    print(f"   Nearby: {etl.target_locations['nearby'][:3]}...")
    print()
    
    print("🔍 Data sources configuration:")
    for source_name, config in etl.data_sources.items():
        if config.get("enabled"):
            feed_count = len(config.get("verified_feeds", [])) + \
                        len(config.get("working_feeds", [])) + \
                        len(config.get("platform_feeds", [])) + \
                        len(config.get("real_academic_sources", [])) + \
                        len(config.get("news_sources", [])) + \
                        len(config.get("oss_feeds", [])) + \
                        len(config.get("local_feeds", []))
            print(f"   ✅ {source_name}: {feed_count} feeds")
        else:
            print(f"   ❌ {source_name}: disabled")
    print()
    
    try:
        # Test extraction
        print("📥 Starting extraction...")
        raw_events = etl.extract()
        print(f"✅ Extracted {len(raw_events)} raw events")
        
        # Analyze by source
        source_counts = {}
        for event in raw_events:
            source = event.get("source_name", "unknown")
            source_counts[source] = source_counts.get(source, 0) + 1
        
        print("\n📊 Events by source:")
        for source, count in sorted(source_counts.items()):
            print(f"   {source}: {count} events")
        
        # Test transformation
        print("\n🔄 Starting transformation...")
        transformed_events = etl.transform(raw_events)
        print(f"✅ Transformed {len(transformed_events)} events")
        
        # Analyze transformed events
        valencia_local = sum(1 for e in transformed_events if not e.is_virtual and e.venue and "valencia" in str(e.venue.city).lower())
        virtual_events = sum(1 for e in transformed_events if e.is_virtual)
        nearby_events = len(transformed_events) - valencia_local - virtual_events
        
        print(f"\n📍 Event distribution:")
        print(f"   Valencia local: {valencia_local}")
        print(f"   Virtual/Online: {virtual_events}")
        print(f"   Nearby locations: {nearby_events}")
        print(f"   Total: {len(transformed_events)}")
        
        # Event types
        event_types = {}
        for event in transformed_events:
            event_type = str(event.event_type)
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        print(f"\n🏷️ Event types:")
        for event_type, count in sorted(event_types.items()):
            print(f"   {event_type}: {count}")
        
        # Quality metrics
        if transformed_events:
            avg_quality = sum(e.quality_score for e in transformed_events) / len(transformed_events)
            avg_relevance = sum(e.relevance_score for e in transformed_events) / len(transformed_events)
            avg_networking = sum(e.networking_score for e in transformed_events) / len(transformed_events)
            
            print(f"\n⭐ Quality metrics:")
            print(f"   Average quality score: {avg_quality:.1f}")
            print(f"   Average relevance score: {avg_relevance:.1f}")
            print(f"   Average networking score: {avg_networking:.1f}")
        
        # Show some sample events
        print(f"\n📋 Sample events:")
        for i, event in enumerate(transformed_events[:3]):
            print(f"\n   {i+1}. {event.name}")
            print(f"      Type: {event.event_type}")
            print(f"      Date: {event.start_date}")
            if event.venue:
                print(f"      Location: {event.venue.city}, {event.venue.country}")
            else:
                print(f"      Location: {'Virtual' if event.is_virtual else 'Unknown'}")
            print(f"      Virtual: {event.is_virtual}")
            print(f"      Topics: {', '.join(event.topics[:3])}{'...' if len(event.topics) > 3 else ''}")
            print(f"      Quality: {event.quality_score:.1f}")
        
        # Test loading
        print(f"\n💾 Testing data loading...")
        etl.load(transformed_events)
        print("✅ Data loading completed")
        
        # Test recommendations
        print(f"\n🎯 Testing recommendations...")
        valencia_developer_profile = {
            "interests": ["python", "machine learning", "web development", "startup"],
            "location": "valencia, spain",
            "budget": 100.0
        }
        
        recommendations = etl.generate_event_recommendations(
            valencia_developer_profile, 
            transformed_events
        )
        
        print(f"✅ Generated {len(recommendations)} recommendations")
        
        if recommendations:
            print(f"\n🌟 Top recommendations for Valencia developer:")
            for i, rec in enumerate(recommendations[:3]):
                event = rec["event"]
                score = rec["recommendation_score"]
                reason = rec["recommendation_reason"]
                print(f"\n   {i+1}. {event['name']} (Score: {score:.1f})")
                print(f"      {reason}")
        
        print(f"\n✅ Valencia Tech Conference ETL test completed successfully!")
        print(f"📈 Summary: {len(transformed_events)} events from {len(source_counts)} sources")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_improved_etl()
    sys.exit(0 if success else 1) 