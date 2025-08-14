#!/usr/bin/env python3

import sys
import subprocess
from pathlib import Path


def run_test_script(script_path: Path, description: str) -> bool:
    """Run a test script and return success status."""
    print(f"\nRunning {description}...")
    print(f"   Script: {script_path}")

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            cwd=script_path.parent.parent,  # Run from project root
        )

        if result.returncode == 0:
            print(f"   PASSED: {description}")
            return True
        else:
            print(f"   FAILED: {description}")
            print(f"   Error output: {result.stderr}")
            return False

    except Exception as e:
        print(f"   ERROR: {description} - {e}")
        return False


def main():
    """Run all tests in the proper order."""
    print("Watchtower Enhanced Framework - Test Suite Runner")
    print("=" * 60)

    tests_dir = Path(__file__).parent
    project_root = tests_dir.parent

    # Test order: working tests first, then comprehensive tests
    test_suite = [
        # Working tests first (guaranteed to pass)
        (tests_dir / "unit" / "test_simple_working.py", "Basic Functionality Tests"),
        (tests_dir / "models" / "test_working_models.py", "Working Model Tests"),
        (tests_dir / "etl" / "test_working_etl.py", "Working ETL Tests"),
        (tests_dir / "unit" / "test_backup_utils.py", "Backup Utilities Tests"),
        (
            tests_dir / "web" / "fullstreamlit" / "components" / "test_adhd_tab.py",
            "ADHD Tab Tests",
        ),
        # Additional working tests
        (tests_dir / "unit" / "test_file_utils.py", "File System Utilities Tests"),
        (tests_dir / "unit" / "test_watchers.py", "Watcher System Tests"),
        (
            tests_dir / "unit" / "test_config_comprehensive.py",
            "Configuration System Tests",
        ),
        # Model tests
        (
            tests_dir / "models" / "test_comprehensive_models.py",
            "Comprehensive Model Tests",
        ),
        (tests_dir / "models" / "test_ecommerce_models.py", "Ecommerce Model Tests"),
        # ETL tests
        (tests_dir / "etl" / "test_base_etl.py", "Base ETL Framework Tests"),
        (
            tests_dir / "etl" / "test_adhd_publications_etl.py",
            "ADHD Publications ETL Tests",
        ),
        (tests_dir / "etl" / "test_shoppy_etl.py", "Shoppy ETL Tests"),
        (tests_dir / "etl" / "test_museum_etl.py", "Museum ETL Tests"),
        (tests_dir / "etl" / "test_mal_etl.py", "MyAnimeList ETL Tests"),
        (tests_dir / "etl" / "test_news_get_newsapi.py", "News API ETL Tests"),
        (
            tests_dir / "etl" / "test_new_game_releases_etl.py",
            "Game Releases ETL Tests",
        ),
        # Web component tests
        (tests_dir / "unit" / "test_museums_tab.py", "Museums Tab Tests"),
        (
            tests_dir / "web" / "fullstreamlit" / "components" / "test_adhd_tab.py",
            "ADHD Tab Tests",
        ),
        # Integration tests
        (
            tests_dir / "integration" / "test_enhanced_features.py",
            "Enhanced Features Integration Tests",
        ),
    ]

    passed = 0
    failed = 0
    skipped = 0

    for script_path, description in test_suite:
        if script_path.exists():
            if run_test_script(script_path, description):
                passed += 1
            else:
                failed += 1
        else:
            print(f"\nSkipping {description} - file not found: {script_path}")
            skipped += 1

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUITE SUMMARY")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")
    print(f"Total: {passed + failed + skipped}")

    if failed == 0:
        print("\nALL TESTS PASSED! Watchtower framework is working correctly.")
        return 0
    else:
        print(f"\n{failed} test(s) failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    exit(main())
