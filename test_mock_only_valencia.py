#!/usr/bin/env python3
"""Mock-only test for Valencia tech ETL - no RSS feeds."""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add the src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from etl.events.tech_conference_etl import TechConferenceETL


def test_mock_only():
    """Test with only mock data - no RSS feeds."""
    print("🚀 Mock-Only Valencia Tech ETL Test")
    print("=" * 45)
    
    # Initialize ETL
    etl = TechConferenceETL(
        name="valencia_mock_test",
        max_events_per_source=10,
        days_ahead=180
    )
    
    # Disable ALL RSS feeds by clearing feed lists
    for source_name, config in etl.data_sources.items():
        # Clear all possible feed lists
        config["verified_feeds"] = []
        config["working_feeds"] = []
        config["platform_feeds"] = []
        config["tech_community_feeds"] = []
        config["real_academic_sources"] = []
        config["university_feeds"] = []
        config["news_sources"] = []
        config["oss_feeds"] = []
        config["local_feeds"] = []
        config["innovation_hubs"] = []
        config["valencia_sources"] = []
        config["conference_aggregators"] = []
    
    print("🔒 All RSS feeds disabled - using only mock data")
    print()
    
    try:
        # Test extraction (mock data only)
        print("📥 Extracting mock events...")
        raw_events = etl.extract()
        print(f"✅ Extracted {len(raw_events)} mock events")
        
        if len(raw_events) == 0:
            print("❌ No mock events found!")
            return False
        
        # Show sources
        source_counts = {}
        for event in raw_events:
            source = event.get("source_name", "unknown")
            source_counts[source] = source_counts.get(source, 0) + 1
        
        print("\n📊 Mock events by source:")
        for source, count in sorted(source_counts.items()):
            print(f"   {source}: {count} events")
        
        # Test transformation
        print(f"\n🔄 Transforming {len(raw_events)} events...")
        transformed_events = etl.transform(raw_events)
        print(f"✅ Transformed {len(transformed_events)} events")
        
        # Analyze Valencia focus
        valencia_local = 0
        virtual_events = 0
        nearby_events = 0
        
        for event in transformed_events:
            if event.is_virtual:
                virtual_events += 1
            elif event.venue and "valencia" in str(event.venue.city).lower():
                valencia_local += 1
            else:
                nearby_events += 1
        
        print(f"\n📍 Valencia focus analysis:")
        print(f"   Valencia local events: {valencia_local}")
        print(f"   Virtual events (accessible): {virtual_events}")
        print(f"   Other locations: {nearby_events}")
        print(f"   Total events: {len(transformed_events)}")
        
        valencia_percentage = (valencia_local / len(transformed_events) * 100) if transformed_events else 0
        virtual_percentage = (virtual_events / len(transformed_events) * 100) if transformed_events else 0
        
        print(f"\n📈 Coverage metrics:")
        print(f"   Valencia coverage: {valencia_percentage:.1f}%")
        print(f"   Virtual accessibility: {virtual_percentage:.1f}%")
        print(f"   Combined Valencia relevance: {valencia_percentage + virtual_percentage:.1f}%")
        
        # Show sample events
        print(f"\n📋 Sample Valencia-focused events:")
        valencia_samples = [e for e in transformed_events if not e.is_virtual and e.venue and "valencia" in str(e.venue.city).lower()]
        virtual_samples = [e for e in transformed_events if e.is_virtual]
        
        for i, event in enumerate(valencia_samples[:3]):
            print(f"\n   🏢 Local #{i+1}: {event.name}")
            print(f"      📅 {event.start_date}")
            print(f"      📍 {event.venue.city if event.venue else 'Unknown'}")
            print(f"      🏷️  {event.event_type}")
            print(f"      ⭐ Quality: {event.quality_score:.1f}")
        
        for i, event in enumerate(virtual_samples[:3]):
            print(f"\n   💻 Virtual #{i+1}: {event.name}")
            print(f"      📅 {event.start_date}")
            print(f"      🌐 {event.virtual_platform or 'Online'}")
            print(f"      🏷️  {event.event_type}")
            print(f"      ⭐ Quality: {event.quality_score:.1f}")
        
        # Test recommendations
        print(f"\n🎯 Testing recommendation system...")
        valencia_dev_profile = {
            "interests": ["python", "machine learning", "web development", "startup"],
            "location": "valencia, spain",
            "budget": 150.0
        }
        
        recommendations = etl.generate_event_recommendations(valencia_dev_profile, transformed_events)
        print(f"✅ Generated {len(recommendations)} personalized recommendations")
        
        if recommendations:
            print(f"\n🌟 Top recommendations for Valencia developer:")
            for i, rec in enumerate(recommendations[:3]):
                event = rec["event"]
                score = rec["recommendation_score"]
                reason = rec["recommendation_reason"]
                print(f"\n   {i+1}. {event['name']} (Score: {score:.1f})")
                print(f"      💡 {reason}")
        
        # Test data saving
        print(f"\n💾 Testing data persistence...")
        etl.load(transformed_events)
        print("✅ Data saved successfully")
        
        # Final validation
        print(f"\n✅ Mock-only test completed successfully!")
        print(f"📊 Summary:")
        print(f"   • {len(transformed_events)} total events processed")
        print(f"   • {valencia_local} Valencia local events")
        print(f"   • {virtual_events} virtual events")
        print(f"   • {len(recommendations)} personalized recommendations")
        
        # Quality checks
        if valencia_local < 5:
            print(f"⚠️  Warning: Only {valencia_local} Valencia local events")
        
        if virtual_events < 5:
            print(f"⚠️  Warning: Only {virtual_events} virtual events")
        
        avg_quality = sum(e.quality_score for e in transformed_events) / len(transformed_events)
        print(f"📈 Average event quality score: {avg_quality:.1f}/100")
        
        return True
        
    except Exception as e:
        print(f"❌ Mock test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_mock_only()
    sys.exit(0 if success else 1) 