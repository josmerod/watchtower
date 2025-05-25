#!/usr/bin/env python3
"""Test script for Technology Adoption Intelligence implementation.

This script tests the Technology Adoption Analyzer and Enhanced Data Service
to ensure they work correctly with the existing Watchtower infrastructure.
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from src.web.fullstreamlit.utils.enhanced_data_service import UltraOptimizedDataService
from src.utils.logging import get_logger


async def test_technology_adoption_intelligence():
    """Test the technology adoption intelligence system."""
    logger = get_logger("test_technology_adoption")
    logger.info("Starting Technology Adoption Intelligence test")
    
    try:
        # Initialize enhanced data service
        data_service = UltraOptimizedDataService(logger)
        logger.info("Enhanced data service initialized")
        
        # Test technology radar generation
        logger.info("Testing technology radar generation...")
        technology_radar = await data_service.get_technology_radar()
        
        if 'error' in technology_radar:
            logger.error(f"Technology radar generation failed: {technology_radar['error']}")
            return False
        
        # Validate results
        logger.info("Validating technology radar results...")
        
        # Check required sections
        required_sections = [
            'framework_battles',
            'adoption_predictions',
            'recommendation_engine',
            'market_intelligence'
        ]
        
        for section in required_sections:
            if section not in technology_radar:
                logger.error(f"Missing required section: {section}")
                return False
            logger.info(f"✓ {section} section present")
        
        # Check framework battles
        battles = technology_radar['framework_battles']
        logger.info(f"Framework battles analyzed: {len(battles)} categories")
        
        for category, battle_data in battles.items():
            logger.info(f"  {category}: Winner={battle_data.get('winner')}, "
                       f"Runner-up={battle_data.get('runner_up')}, "
                       f"Rising star={battle_data.get('rising_star')}")
        
        # Check adoption predictions
        predictions = technology_radar['adoption_predictions']
        logger.info(f"Technology predictions generated: {len(predictions)}")
        
        for tech_name, prediction in predictions.items():
            logger.info(f"  {tech_name}: Current={prediction.get('current_score'):.1f}, "
                       f"Predicted={prediction.get('predicted_score'):.1f}, "
                       f"Trend={prediction.get('trend_direction')}")
        
        # Check recommendations
        recommendations = technology_radar['recommendation_engine']
        if 'top_recommendations' in recommendations:
            top_recs = recommendations['top_recommendations']
            logger.info(f"Top recommendations: {len(top_recs)}")
            
            for i, rec in enumerate(top_recs[:3], 1):
                logger.info(f"  {i}. {rec.get('technology')} - {rec.get('reason')}")
        
        # Check market intelligence
        market_intel = technology_radar['market_intelligence']
        if 'overall_trends' in market_intel:
            trends = market_intel['overall_trends']
            logger.info(f"Market trends identified: {len(trends)}")
            
            for trend in trends:
                logger.info(f"  • {trend}")
        
        # Check confidence score
        confidence = technology_radar.get('confidence_score', 0)
        logger.info(f"Overall confidence score: {confidence:.3f}")
        
        if confidence > 0.5:
            logger.info("✓ Good confidence level achieved")
        else:
            logger.warning("⚠ Low confidence level - may need more data")
        
        logger.info("Technology Adoption Intelligence test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_enhanced_github_trends():
    """Test enhanced GitHub trends functionality."""
    logger = get_logger("test_enhanced_github")
    logger.info("Testing enhanced GitHub trends...")
    
    try:
        data_service = UltraOptimizedDataService(logger)
        
        # Test enhanced GitHub trends
        enhanced_trends = data_service.get_enhanced_github_trends()
        
        if 'error' in enhanced_trends:
            logger.error(f"Enhanced GitHub trends failed: {enhanced_trends['error']}")
            return False
        
        # Check sections
        sections = ['base_data', 'technology_insights', 'trending_frameworks', 'language_trends']
        
        for section in sections:
            if section in enhanced_trends:
                logger.info(f"✓ {section} section present")
            else:
                logger.warning(f"⚠ {section} section missing")
        
        # Show insights
        if 'technology_insights' in enhanced_trends:
            insights = enhanced_trends['technology_insights']
            
            if 'popular_categories' in insights:
                pop_categories = insights['popular_categories']
                logger.info(f"Popular categories: {list(pop_categories.keys())}")
            
            if 'emerging_technologies' in insights:
                emerging = insights['emerging_technologies']
                logger.info(f"Emerging technologies found: {len(emerging)}")
        
        if 'trending_frameworks' in enhanced_trends:
            frameworks = enhanced_trends['trending_frameworks']
            logger.info(f"Trending frameworks identified: {len(frameworks)}")
            
            for fw in frameworks[:3]:
                logger.info(f"  • {fw.get('framework')} ({fw.get('category')})")
        
        logger.info("Enhanced GitHub trends test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Enhanced GitHub trends test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    logger = get_logger("main_test")
    logger.info("=== Technology Adoption Intelligence Test Suite ===")
    
    # Test 1: Enhanced GitHub Trends
    logger.info("\n1. Testing Enhanced GitHub Trends...")
    github_success = test_enhanced_github_trends()
    
    # Test 2: Technology Adoption Intelligence  
    logger.info("\n2. Testing Technology Adoption Intelligence...")
    adoption_success = await test_technology_adoption_intelligence()
    
    # Summary
    logger.info("\n=== Test Results Summary ===")
    logger.info(f"Enhanced GitHub Trends: {'✓ PASS' if github_success else '✗ FAIL'}")
    logger.info(f"Technology Adoption Intelligence: {'✓ PASS' if adoption_success else '✗ FAIL'}")
    
    if github_success and adoption_success:
        logger.info("🎉 All tests passed! Technology Adoption Intelligence is ready.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 