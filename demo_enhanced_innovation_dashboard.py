#!/usr/bin/env python3
"""
Demo script showcasing the Enhanced Innovation & Tech Dashboard improvements.

This script demonstrates the key features and visualizations that have been
enhanced in the Technology Adoption Intelligence system.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from src.web.fullstreamlit.utils.enhanced_data_service import UltraOptimizedDataService
from src.utils.logging import get_logger


async def demo_enhanced_dashboard():
    """Demonstrate the enhanced dashboard features."""
    logger = get_logger("enhanced_dashboard_demo")
    
    print("🚀 Enhanced Innovation & Tech Dashboard Demo")
    print("=" * 60)
    
    # Initialize enhanced data service
    print("\n1. Initializing Enhanced Data Service...")
    data_service = UltraOptimizedDataService(logger)
    print("   ✅ UltraOptimizedDataService initialized")
    
    # Load technology radar data
    print("\n2. Loading Technology Adoption Intelligence...")
    radar_data = await data_service.get_technology_radar()
    
    if 'error' in radar_data:
        print(f"   ❌ Error: {radar_data['error']}")
        return
    
    print("   ✅ Technology intelligence loaded successfully!")
    
    # Display key metrics
    print("\n3. Key Intelligence Metrics:")
    print("-" * 40)
    
    battles = radar_data.get('framework_battles', {})
    predictions = radar_data.get('adoption_predictions', {})
    recommendations = radar_data.get('recommendation_engine', {})
    market_intel = radar_data.get('market_intelligence', {})
    
    print(f"   📊 Framework Battles Analyzed: {len(battles)} categories")
    print(f"   🔮 Technology Predictions: {len(predictions)} technologies")
    print(f"   💎 Investment Recommendations: {len(recommendations.get('top_recommendations', []))}")
    print(f"   🎯 Market Intelligence: {len(market_intel.get('overall_trends', []))} trends")
    print(f"   🎖️  Overall Confidence: {radar_data.get('confidence_score', 0):.1%}")
    
    # Framework battle winners
    print("\n4. Framework Battle Championship Results:")
    print("-" * 50)
    
    for category, battle_data in battles.items():
        winner = battle_data.get('winner', 'Unknown')
        runner_up = battle_data.get('runner_up', 'Unknown')
        rising_star = battle_data.get('rising_star', 'Unknown')
        confidence = battle_data.get('confidence_score', 0)
        
        print(f"   🏆 {category.title()} Category:")
        print(f"      Winner: {winner}")
        print(f"      Runner-up: {runner_up}")
        print(f"      Rising Star: {rising_star}")
        print(f"      Confidence: {confidence:.1%}")
        print()
    
    # Top predictions
    print("5. Top Technology Predictions:")
    print("-" * 40)
    
    # Sort predictions by growth potential
    sorted_predictions = sorted(
        predictions.items(),
        key=lambda x: x[1].get('expected_growth_percentage', 0),
        reverse=True
    )
    
    for tech_name, prediction in sorted_predictions[:5]:
        current = prediction.get('current_score', 0)
        predicted = prediction.get('predicted_score', 0)
        growth = prediction.get('expected_growth_percentage', 0)
        trend = prediction.get('trend_direction', 'stable')
        confidence = prediction.get('confidence', 0)
        
        trend_emoji = {
            'explosive': '🚀',
            'rising': '📈',
            'stable': '➡️',
            'declining': '📉'
        }.get(trend, '❓')
        
        print(f"   {trend_emoji} {tech_name}:")
        print(f"      Current Score: {current:.1f}")
        print(f"      Predicted Score: {predicted:.1f}")
        print(f"      Growth: {growth:+.1f}%")
        print(f"      Confidence: {confidence:.1%}")
        print()
    
    # Investment recommendations
    investment_grades = recommendations.get('investment_grades', {})
    
    print("6. Investment Intelligence:")
    print("-" * 30)
    
    strong_buys = investment_grades.get('strong_buy', [])
    buys = investment_grades.get('buy', [])
    holds = investment_grades.get('hold', [])
    avoids = investment_grades.get('avoid', [])
    
    print(f"   🚀 Strong Buy: {len(strong_buys)} technologies")
    print(f"   📈 Buy: {len(buys)} technologies")
    print(f"   ⏸️  Hold: {len(holds)} technologies")
    print(f"   🚨 Avoid: {len(avoids)} technologies")
    
    if strong_buys:
        print("\n   Top Strong Buy Recommendations:")
        for rec in strong_buys[:3]:
            print(f"      • {rec.get('technology', 'Unknown')}")
            print(f"        {rec.get('reason', 'No reason provided')}")
    
    # Market intelligence insights
    print("\n7. Market Intelligence Insights:")
    print("-" * 40)
    
    overall_trends = market_intel.get('overall_trends', [])
    category_insights = market_intel.get('category_insights', {})
    
    if overall_trends:
        print("   📊 Market Trends:")
        for trend in overall_trends:
            print(f"      • {trend}")
    
    if category_insights:
        print("\n   🎯 Category Insights:")
        for category, insight_data in category_insights.items():
            insight = insight_data.get('insight', 'No insight available')
            leader = insight_data.get('market_leader', 'Unknown')
            confidence = insight_data.get('confidence', 0)
            
            print(f"      {category.title()}: {insight}")
            print(f"         Leader: {leader} (Confidence: {confidence:.1%})")
    
    # Dashboard features summary
    print("\n8. Enhanced Dashboard Features:")
    print("-" * 40)
    print("   🎯 Interactive Technology Radar Chart")
    print("   ⚔️  Framework Battle Visualizations")
    print("   📈 Adoption Trend Predictions")
    print("   🔍 Market Intelligence Dashboard")
    print("   💎 Investment Intelligence Hub")
    print("   🎨 Beautiful gradient cards and styling")
    print("   📊 Multiple chart types (radar, scatter, sunburst)")
    print("   🔄 Real-time data integration")
    print("   🎛️  Interactive filters and controls")
    print("   📱 Responsive design")
    
    # Data sources
    print("\n9. Data Sources Integration:")
    print("-" * 35)
    data_sources = radar_data.get('data_sources', [])
    for source in data_sources:
        print(f"   ✅ {source.replace('_', ' ').title()}")
    
    print(f"\n   📅 Last Updated: {radar_data.get('last_updated', 'Unknown')}")
    
    print("\n" + "=" * 60)
    print("🎉 Enhanced Innovation & Tech Dashboard Demo Complete!")
    print("\nKey Improvements:")
    print("• Advanced AI-powered technology analysis")
    print("• Interactive radar and battle visualizations")
    print("• Investment-grade recommendations")
    print("• Real-time data from GitHub and DEV community")
    print("• Modern, gradient-rich UI design")
    print("• Comprehensive market intelligence")
    print("\n🌐 Access the dashboard at: http://localhost:8501")
    print("   Navigate to the '🚀 Innovation' tab to see all features!")


if __name__ == "__main__":
    asyncio.run(demo_enhanced_dashboard()) 