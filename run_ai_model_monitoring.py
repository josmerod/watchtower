#!/usr/bin/env python3
"""AI Model Monitoring Runner Script.

This script demonstrates how to run the AI model monitoring ETL system
for tracking new model releases from OpenAI, Anthropic, and Google.

Usage:
    python run_ai_model_monitoring.py [--provider PROVIDER] [--all]

Examples:
    python run_ai_model_monitoring.py --all
    python run_ai_model_monitoring.py --provider openai
    python run_ai_model_monitoring.py --provider anthropic
    python run_ai_model_monitoring.py --provider google
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.utils.logging import get_logger
from src.etl.ai_platforms.ai_model_monitoring_etl import AIModelMonitoringETL
from src.etl.ai_platforms.openai_platform_etl import OpenAIPlatformETL
from src.etl.ai_platforms.anthropic_etl import AnthropicETL
from src.etl.ai_platforms.google_gemini_etl import GoogleGeminiETL

logger = get_logger("AIModelMonitoringRunner")


async def run_all_providers():
    """Run monitoring for all AI providers."""
    logger.info("Starting comprehensive AI model monitoring for all providers")
    
    try:
        # Run the comprehensive ETL that combines all sources
        comprehensive_etl = AIModelMonitoringETL()
        updates = await comprehensive_etl.fetch_all_sources()
        
        if updates:
            processed = comprehensive_etl.process_updates(updates)
            comprehensive_etl.save_updates(processed)
            logger.info(f"Processed and saved {len(processed)} updates from all providers")
        else:
            logger.warning("No updates found from any provider")
        
        logger.info("Comprehensive AI model monitoring completed successfully")
        
    except Exception as e:
        logger.error(f"Error in comprehensive AI model monitoring: {e}", exc_info=True)
        raise


async def run_openai_monitoring():
    """Run monitoring specifically for OpenAI."""
    logger.info("Starting OpenAI platform monitoring")
    
    try:
        etl = OpenAIPlatformETL()
        
        # Extract data
        extracted_data = etl.extract()
        if not extracted_data:
            logger.warning("No data extracted from OpenAI")
            return
            
        # Transform data
        transformed_data = etl.transform(extracted_data)
        
        # Load data
        etl.load(transformed_data)
        
        logger.info(f"OpenAI monitoring completed successfully. Processed {len(transformed_data)} records")
        
    except Exception as e:
        logger.error(f"Error in OpenAI monitoring: {e}", exc_info=True)
        raise


async def run_anthropic_monitoring():
    """Run monitoring specifically for Anthropic."""
    logger.info("Starting Anthropic platform monitoring")
    
    try:
        etl = AnthropicETL()
        
        # Extract data
        extracted_data = etl.extract()
        if not extracted_data:
            logger.warning("No data extracted from Anthropic")
            return
            
        # Transform data
        transformed_data = etl.transform(extracted_data)
        
        # Load data
        etl.load(transformed_data)
        
        logger.info(f"Anthropic monitoring completed successfully. Processed {len(transformed_data)} records")
        
    except Exception as e:
        logger.error(f"Error in Anthropic monitoring: {e}", exc_info=True)
        raise


async def run_google_monitoring():
    """Run monitoring specifically for Google/Gemini."""
    logger.info("Starting Google Gemini platform monitoring")
    
    try:
        # Use the existing Google Gemini ETL with async main
        from src.etl.ai_platforms.google_gemini_etl import main as google_main
        await google_main()
        
    except Exception as e:
        logger.error(f"Error in Google monitoring: {e}", exc_info=True)
        raise


async def main():
    """Main entry point for the AI model monitoring runner."""
    parser = argparse.ArgumentParser(
        description="Run AI model monitoring for tracking new model releases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all                    Run monitoring for all providers
  %(prog)s --provider openai        Run OpenAI monitoring only
  %(prog)s --provider anthropic     Run Anthropic monitoring only
  %(prog)s --provider google        Run Google/Gemini monitoring only
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--all', 
        action='store_true',
        help='Run monitoring for all AI providers (OpenAI, Anthropic, Google)'
    )
    group.add_argument(
        '--provider',
        choices=['openai', 'anthropic', 'google'],
        help='Run monitoring for a specific provider only'
    )
    
    args = parser.parse_args()
    
    start_time = datetime.now()
    logger.info(f"AI Model Monitoring started at {start_time}")
    
    try:
        if args.all:
            await run_all_providers()
        elif args.provider == 'openai':
            await run_openai_monitoring()
        elif args.provider == 'anthropic':
            await run_anthropic_monitoring()
        elif args.provider == 'google':
            await run_google_monitoring()
            
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"AI Model Monitoring completed successfully in {duration}")
        
    except Exception as e:
        logger.error(f"AI Model Monitoring failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 