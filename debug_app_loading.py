#!/usr/bin/env python3
"""
Diagnostic script for Watchtower app loading issues.
Run this to identify what might be causing the app to get stuck.
"""

import sys
import os
import time
from pathlib import Path

# Add the src directory to the Python path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

def test_imports():
    """Test if all critical imports work"""
    print("🧪 Testing imports...")
    
    try:
        from utils.logging import get_logger
        print("✅ Logging import OK")
    except Exception as e:
        print(f"❌ Logging import failed: {e}")
        return False
    
    try:
        from web.fullstreamlit.utils.data_service_ultra_optimized import create_ultra_optimized_service
        print("✅ Data service import OK")
    except Exception as e:
        print(f"❌ Data service import failed: {e}")
        return False
    
    try:
        import streamlit as st
        print("✅ Streamlit import OK")
    except Exception as e:
        print(f"❌ Streamlit import failed: {e}")
        return False
    
    return True

def test_data_service():
    """Test data service initialization and basic operations"""
    print("\n🔬 Testing data service...")
    
    try:
        from utils.logging import get_logger
        from web.fullstreamlit.utils.data_service_ultra_optimized import create_ultra_optimized_service
        
        logger = get_logger("DiagnosticTest")
        data_service = create_ultra_optimized_service(logger)
        
        print("✅ Data service created successfully")
        
        # Test health status
        health = data_service.get_health_status()
        print(f"📊 Health status: {health}")
        
        # Test individual data loading functions with timeout
        test_functions = [
            ("get_museum_data", data_service.get_museum_data),
            ("get_games_data", data_service.get_games_data),
            ("get_allkeyshop_data", data_service.get_allkeyshop_data),
        ]
        
        for func_name, func in test_functions:
            try:
                print(f"⏱️  Testing {func_name}...")
                start_time = time.time()
                result = func()
                duration = time.time() - start_time
                print(f"✅ {func_name} completed in {duration:.2f}s - Result type: {type(result)}")
            except Exception as e:
                print(f"❌ {func_name} failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data service test failed: {e}")
        return False

def test_data_files():
    """Test if data files exist and are readable"""
    print("\n📁 Testing data files...")
    
    data_dir = Path("data")
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return False
    
    critical_paths = [
        "games",
        "allkeyshop_games/output", 
        "youtube",
        "courses",
        "virtual_museums_etl/output"
    ]
    
    for path_str in critical_paths:
        path = data_dir / path_str
        if path.exists():
            try:
                # Count files in directory
                if path.is_dir():
                    files = list(path.glob("*.json"))
                    print(f"✅ {path_str}: {len(files)} JSON files found")
                else:
                    print(f"✅ {path_str}: File exists")
            except Exception as e:
                print(f"⚠️  {path_str}: Accessible but error reading: {e}")
        else:
            print(f"❌ {path_str}: Not found")
    
    return True

def test_date_parsing():
    """Test the robust date parser"""
    print("\n📅 Testing date parsing...")
    
    try:
        from utils.date_parser import parse_date
        
        # Test problematic date formats that were causing warnings
        test_dates = [
            "6.12.25",
            "6.11.25", 
            "18 May 2025 00:00:00 +0000",
            "2025-01-01T10:30:00Z",
            "invalid date"
        ]
        
        for date_str in test_dates:
            result = parse_date(date_str, suppress_warnings=True)
            status = "✅" if result else "⚠️ "
            print(f"{status} '{date_str}' -> {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Date parsing test failed: {e}")
        return False

def main():
    """Run all diagnostic tests"""
    print("🗼 Watchtower App Loading Diagnostic\n")
    
    all_tests_passed = True
    
    # Run tests
    tests = [
        ("Imports", test_imports),
        ("Data Files", test_data_files),
        ("Date Parsing", test_date_parsing),
        ("Data Service", test_data_service),
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running {test_name} test...")
        print('='*50)
        
        try:
            success = test_func()
            if not success:
                all_tests_passed = False
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            all_tests_passed = False
    
    print(f"\n{'='*50}")
    if all_tests_passed:
        print("🎉 All tests passed! App should load properly.")
    else:
        print("⚠️  Some tests failed. Check the output above for issues.")
    print('='*50)

if __name__ == "__main__":
    main() 