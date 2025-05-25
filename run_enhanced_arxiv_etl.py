#!/usr/bin/env python
"""
Script to run the Enhanced ArXiv ETL pipeline with advanced intelligence features.
"""
import sys
import os
import argparse
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.etl.arxiv.enhanced_arxiv_etl import EnhancedArxivETL
from src.utils.logging import get_logger


def main():
    """Run the Enhanced ArXiv ETL pipeline with command line arguments."""
    logger = get_logger("run_enhanced_arxiv_etl")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run Enhanced ArXiv ETL pipeline with advanced intelligence features")
    parser.add_argument("--days", type=int, default=7, help="Number of days back to fetch papers (default: 7)")
    parser.add_argument("--max-results", type=int, default=200, help="Maximum number of papers to fetch (default: 200)")
    parser.add_argument("--clusters", type=int, default=15, help="Number of clusters for paper classification (default: 15)")
    parser.add_argument("--no-advanced-scoring", action="store_true", help="Disable advanced impact scoring")
    parser.add_argument("--no-github", action="store_true", help="Disable GitHub integration")
    parser.add_argument("--no-pwc", action="store_true", help="Disable Papers With Code integration")
    parser.add_argument("--name", type=str, default="enhanced_arxiv", help="ETL process name (default: enhanced_arxiv)")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for processing (default: 50)")
    args = parser.parse_args()
    
    # Log start
    logger.info(f"Starting Enhanced ArXiv ETL run at {datetime.now()}")
    logger.info(f"Parameters: days_back={args.days}, max_results={args.max_results}, clusters={args.clusters}")
    logger.info(f"Advanced features: scoring={not args.no_advanced_scoring}, github={not args.no_github}, pwc={not args.no_pwc}")
    
    # Initialize and run the ETL
    try:
        etl = EnhancedArxivETL(
            name=args.name,
            days_back=args.days,
            max_results=args.max_results,
            n_clusters=args.clusters,
            enable_advanced_scoring=not args.no_advanced_scoring,
            enable_github_integration=not args.no_github,
            enable_pwc_integration=not args.no_pwc,
            batch_size=args.batch_size
        )
        
        logger.info("Running Enhanced ArXiv ETL pipeline...")
        metrics = etl.run()
        
        # Log success metrics
        logger.info("Enhanced ArXiv ETL run completed successfully!")
        logger.info(f"📊 Results Summary:")
        logger.info(f"  • Papers extracted: {metrics.records_extracted}")
        logger.info(f"  • Papers transformed: {metrics.records_transformed}")
        logger.info(f"  • Papers loaded: {metrics.records_loaded}")
        logger.info(f"  • Failed records: {metrics.records_failed}")
        logger.info(f"  • Duration: {metrics.duration_seconds:.2f} seconds")
        logger.info(f"  • Success rate: {(metrics.records_loaded / max(metrics.records_extracted, 1)) * 100:.1f}%")
        
        # Print summary for user
        print(f"\n✅ Enhanced ArXiv ETL completed successfully!")
        print(f"📈 Processed {metrics.records_loaded} papers in {metrics.duration_seconds:.2f} seconds")
        print(f"🎯 Success rate: {(metrics.records_loaded / max(metrics.records_extracted, 1)) * 100:.1f}%")
        
        if metrics.records_failed > 0:
            print(f"⚠️  {metrics.records_failed} papers failed processing")
        
        # Show where results are saved
        print(f"\n📁 Results saved to:")
        print(f"  • JSON: data/{args.name}/output/latest_enhanced_papers.json")
        print(f"  • CSV: data/{args.name}/output/latest_enhanced_papers.csv")
        print(f"  • Reports: data/{args.name}/output/*_report.json")
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("Enhanced ArXiv ETL run interrupted by user")
        print("\n⚠️  ETL run interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"Enhanced ArXiv ETL run failed: {str(e)}")
        print(f"\n❌ Enhanced ArXiv ETL run failed: {str(e)}")
        
        # Print troubleshooting tips
        print(f"\n🔧 Troubleshooting tips:")
        print(f"  • Check your internet connection")
        print(f"  • Verify ArXiv API is accessible")
        print(f"  • Try reducing --max-results if you get timeouts")
        print(f"  • Use --no-github and --no-pwc to disable external integrations")
        print(f"  • Check logs for detailed error information")
        
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 