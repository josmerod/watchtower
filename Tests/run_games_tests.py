#!/usr/bin/env python3
"""Dedicated test runner for Games functionality.
Runs ETL tests, component tests, and data quality validation.
"""

import os
import sys
import unittest
from datetime import datetime

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def run_games_tests():
    """Run all games-related tests"""
    print("=" * 60)
    print("🎮 GAMES FUNCTIONALITY TEST SUITE")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Create test suite
    test_suite = unittest.TestSuite()

    # Import and add ETL tests
    try:
        from Tests.etl.test_games_etl_comprehensive import (
            TestGamesDataQuality,
            TestGamesETLComprehensive,
        )

        test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestGamesETLComprehensive))
        test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestGamesDataQuality))
        print("✅ Loaded ETL tests")
    except ImportError as e:
        print(f"⚠️  Could not load ETL tests: {e}")

    # Import and add component tests
    try:
        from Tests.web.fullstreamlit.components.test_games_tab import (
            TestGamesDataIntegration,
            TestGamesTabComponent,
        )

        test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestGamesTabComponent))
        test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestGamesDataIntegration))
        print("✅ Loaded component tests")
    except ImportError as e:
        print(f"⚠️  Could not load component tests: {e}")

    # Import existing new game releases tests if available
    try:
        from Tests.etl.test_new_game_releases_etl import TestNewGameReleasesETL

        test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestNewGameReleasesETL))
        print("✅ Loaded existing new releases tests")
    except ImportError as e:
        print(f"⚠️  Could not load existing new releases tests: {e}")

    print()
    print("Running tests...")
    print("-" * 60)

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, descriptions=True, failfast=False)

    result = runner.run(test_suite)

    print()
    print("=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")

    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split(chr(10))[0]}")

    if result.errors:
        print("\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split(chr(10))[0]}")

    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"\n🎯 Success Rate: {success_rate:.1f}%")

    if result.wasSuccessful():
        print("🎉 ALL TESTS PASSED!")
        print("\n🎮 Games functionality is working correctly!")
        return True
    else:
        print("⚠️  SOME TESTS FAILED!")
        print("🔧 Please review the failures and fix the issues.")
        return False


def validate_data_quality():
    """Validate current games data quality"""
    print("\n" + "=" * 60)
    print("🔍 DATA QUALITY VALIDATION")
    print("=" * 60)

    data_dir = os.path.join(project_root, "data", "games")

    if not os.path.exists(data_dir):
        print("❌ Games data directory not found!")
        return False

    # Check file existence and basic structure
    expected_files = [
        ("deals.json", "Game deals data"),
        ("bundles.json", "Game bundles data"),
        ("giveaways.json", "Game giveaways data"),
        ("itchio_trending.json", "Itch.io trending games"),
        ("new_releases.json", "New game releases"),
    ]

    all_good = True

    for filename, description in expected_files:
        filepath = os.path.join(data_dir, filename)

        if os.path.exists(filepath):
            try:
                import json

                with open(filepath) as f:
                    data = json.load(f)

                if isinstance(data, list):
                    print(f"✅ {description}: {len(data)} records")
                else:
                    print(f"⚠️  {description}: Non-list structure")

            except json.JSONDecodeError:
                print(f"❌ {description}: Corrupted JSON")
                all_good = False
            except Exception as e:
                print(f"❌ {description}: Error reading file - {e}")
                all_good = False
        else:
            print(f"❌ {description}: File not found")
            all_good = False

    # Check data freshness
    deals_file = os.path.join(data_dir, "deals.json")
    if os.path.exists(deals_file):
        mod_time = os.path.getmtime(deals_file)
        mod_datetime = datetime.fromtimestamp(mod_time)
        age_hours = (datetime.now() - mod_datetime).total_seconds() / 3600

        if age_hours < 24:
            print(f"✅ Data freshness: Updated {age_hours:.1f} hours ago")
        else:
            print(f"⚠️  Data freshness: Updated {age_hours:.1f} hours ago (consider refreshing)")

    return all_good


if __name__ == "__main__":
    print("🚀 Starting Games Functionality Test Suite")

    # Run tests
    tests_passed = run_games_tests()

    # Validate data quality
    data_quality_good = validate_data_quality()

    print("\n" + "=" * 60)
    print("🏁 FINAL SUMMARY")
    print("=" * 60)

    if tests_passed and data_quality_good:
        print("🎉 Games functionality is FULLY OPERATIONAL!")
        print("   - All tests passed")
        print("   - Data quality is good")
        print("   - Ready for production use")
        exit_code = 0
    elif tests_passed:
        print("⚠️  Games functionality has MINOR ISSUES")
        print("   - All tests passed")
        print("   - Data quality needs attention")
        exit_code = 1
    else:
        print("❌ Games functionality has MAJOR ISSUES")
        print("   - Some tests failed")
        print("   - Requires immediate attention")
        exit_code = 2

    print(f"\nFinished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sys.exit(exit_code)
