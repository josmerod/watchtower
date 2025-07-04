#!/usr/bin/env python3

import subprocess
import sys
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
            cwd=script_path.parent.parent  # Run from project root
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

    # Test order: unit -> integration -> ETL -> data validation
    test_suite = [
        # Unit tests

        # Integration tests

        # ETL tests

        # Data validation
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
