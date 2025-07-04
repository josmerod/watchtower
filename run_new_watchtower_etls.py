#!/usr/bin/env python3
"""New Watchtower ETLs Runner.

This script runs the newly implemented ETLs from the brainstorm ideas:
1. Meme Economics Tracker - Because memes are serious business
2. Enhanced Free Games Intelligence - Never miss a free game
3. ADHD-Friendly Location Intelligence - Making the world neurodivergent-friendly

These can be integrated into the main Watchtower ETL scheduler.
"""

import argparse
import sys
from datetime import datetime
from typing import Any

# Add the project root to the path
from src.utils.logging import get_logger

logger = get_logger("NewWatchtowerETLs")


def run_meme_economics():
    """Run the Meme Economics ETL."""
    logger.info("🐸 Starting Meme Economics Tracker...")

    try:
        from src.etl.entertainment.meme_economics_etl import run_meme_economics_etl

        metrics = run_meme_economics_etl()

        logger.info(
            f"✅ Meme Economics completed: {metrics.records_loaded} records, {metrics.success_rate:.1f}% success"
        )
        return {
            "name": "meme_economics",
            "status": "success",
            "records": metrics.records_loaded,
        }

    except Exception as e:
        logger.error(f"❌ Meme Economics failed: {e}")
        return {"name": "meme_economics", "status": "failed", "error": str(e)}


def run_enhanced_free_games():
    """Run the Enhanced Free Games ETL."""
    logger.info("🎮 Starting Enhanced Free Games Intelligence...")

    try:
        from src.etl.games.enhanced_free_games_etl import run_enhanced_free_games_etl

        metrics = run_enhanced_free_games_etl()

        logger.info(
            f"✅ Enhanced Free Games completed: {metrics.records_loaded} records, {metrics.success_rate:.1f}% success"
        )
        return {
            "name": "enhanced_free_games",
            "status": "success",
            "records": metrics.records_loaded,
        }

    except Exception as e:
        logger.error(f"❌ Enhanced Free Games failed: {e}")
        return {"name": "enhanced_free_games", "status": "failed", "error": str(e)}


def run_adhd_locations():
    """Run the ADHD-Friendly Locations ETL."""
    logger.info("🧠 Starting ADHD-Friendly Location Intelligence...")

    try:
        from src.etl.neurodivergent.adhd_friendly_locations_etl import (
            run_adhd_friendly_locations_etl,
        )

        metrics = run_adhd_friendly_locations_etl()

        logger.info(
            f"✅ ADHD Locations completed: {metrics.records_loaded} records, {metrics.success_rate:.1f}% success"
        )
        return {
            "name": "adhd_locations",
            "status": "success",
            "records": metrics.records_loaded,
        }

    except Exception as e:
        logger.error(f"❌ ADHD Locations failed: {e}")
        return {"name": "adhd_locations", "status": "failed", "error": str(e)}


def run_all_new_etls() -> list[dict[str, Any]]:
    """Run all new ETLs and return results."""
    logger.info("🚀 Starting all new Watchtower ETLs from brainstorm ideas!")

    results = []

    # Run all ETLs
    etl_functions = [run_meme_economics, run_enhanced_free_games, run_adhd_locations]

    for etl_func in etl_functions:
        try:
            result = etl_func()
            results.append(result)
        except Exception as e:
            logger.error(f"ETL {etl_func.__name__} crashed: {e}")
            results.append(
                {
                    "name": etl_func.__name__.replace("run_", ""),
                    "status": "crashed",
                    "error": str(e),
                }
            )

    return results


def print_summary(results: list[dict[str, Any]]):
    """Print a summary of ETL results."""
    print("\n" + "=" * 60)
    print("🎉 NEW WATCHTOWER ETLS SUMMARY")
    print("=" * 60)

    total_records = 0
    successful = 0
    failed = 0

    for result in results:
        status_emoji = "✅" if result["status"] == "success" else "❌"
        name = result["name"].replace("_", " ").title()

        if result["status"] == "success":
            records = result.get("records", 0)
            total_records += records
            successful += 1
            print(f"{status_emoji} {name}: {records} records")
        else:
            failed += 1
            error = result.get("error", "Unknown error")
            print(f"{status_emoji} {name}: FAILED - {error}")

    print("-" * 60)
    print(
        f"📊 Total: {successful + failed} ETLs, {successful} successful, {failed} failed"
    )
    print(f"📈 Total records processed: {total_records}")
    print(f"⏱️  Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if successful > 0:
        print("\n🎯 Check these directories for new data:")
        print("- data/meme_economics/output/ - Meme market intelligence")
        print("- data/enhanced_free_games/output/ - Free games recommendations")
        print("- data/adhd_friendly_locations/output/ - Neurodivergent-friendly spaces")

    print("\n💡 Integration opportunities:")
    print("- Add to main ETL scheduler")
    print("- Integrate with Streamlit dashboard")
    print("- Create alert systems for urgent recommendations")
    print("- Connect with notification systems")


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(
        description="Run new Watchtower ETLs from brainstorm ideas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_new_watchtower_etls.py                    # Run all new ETLs
  python run_new_watchtower_etls.py --etl memes        # Run only meme economics
  python run_new_watchtower_etls.py --etl games        # Run only free games
  python run_new_watchtower_etls.py --etl adhd         # Run only ADHD locations
        """,
    )

    parser.add_argument(
        "--etl",
        choices=["memes", "games", "adhd", "all"],
        default="all",
        help="Which ETL to run (default: all)",
    )

    parser.add_argument(
        "--quiet", action="store_true", help="Suppress detailed logging output"
    )

    args = parser.parse_args()

    # Configure logging level
    if args.quiet:
        import logging

        logging.getLogger().setLevel(logging.WARNING)

    # Run selected ETLs
    results = []

    if args.etl == "all":
        results = run_all_new_etls()
    elif args.etl == "memes":
        results = [run_meme_economics()]
    elif args.etl == "games":
        results = [run_enhanced_free_games()]
    elif args.etl == "adhd":
        results = [run_adhd_locations()]

    # Print summary
    if not args.quiet:
        print_summary(results)

    # Return appropriate exit code
    failed_count = sum(1 for r in results if r["status"] != "success")
    return min(failed_count, 1)  # Return 0 for success, 1 for any failures


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
