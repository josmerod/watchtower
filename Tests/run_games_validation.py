#!/usr/bin/env python3
"""
Games Functionality Validation Script.
Tests core functionality and data quality without complex mocking.
"""

import unittest
import sys
import os
from datetime import datetime
import json

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def run_core_validation():
    """Run core games functionality validation"""
    print("="*60)
    print("🎮 GAMES FUNCTIONALITY VALIDATION")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Run the simplified data quality tests
    from Tests.test_games_data_quality import TestGamesDataQuality
    
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestGamesDataQuality))
    
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


def validate_real_data():
    """Validate real games data quality"""
    print("\n" + "="*60)
    print("📊 REAL DATA VALIDATION")
    print("="*60)
    
    data_dir = os.path.join(project_root, "data", "games")
    
    if not os.path.exists(data_dir):
        print("❌ Games data directory not found!")
        return False
    
    # Check file existence and record counts
    files_info = [
        ('deals.json', 'Game deals'),
        ('bundles.json', 'Game bundles'),
        ('giveaways.json', 'Game giveaways'),
        ('itchio_trending.json', 'Itch.io trending games'),
        ('new_releases.json', 'New game releases'),
        ('humblebundles.json', 'Humble bundles')
    ]
    
    total_records = 0
    all_good = True
    
    for filename, description in files_info:
        filepath = os.path.join(data_dir, filename)
        
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    record_count = len(data)
                    total_records += record_count
                    
                    if record_count > 0:
                        print(f"✅ {description}: {record_count} records")
                    else:
                        print(f"⚠️  {description}: 0 records (empty but valid)")
                else:
                    print(f"⚠️  {description}: Non-list structure")
                    
            except json.JSONDecodeError:
                print(f"❌ {description}: Corrupted JSON")
                all_good = False
            except Exception as e:
                print(f"❌ {description}: Error - {e}")
                all_good = False
        else:
            print(f"❌ {description}: File not found")
            all_good = False
    
    print(f"\n📈 Total records across all files: {total_records}")
    
    return all_good and total_records > 0


def test_components_integration():
    """Test component integration"""
    print("\n" + "="*60)
    print("🔧 COMPONENT INTEGRATION TEST")
    print("="*60)
    
    try:
        # Test price parsing function
        from src.web.new_dashboard_poc.components.games_tab import parse_price
        
        test_cases = [
            ("$19.99", 19.99),
            ("Free", 0.0),
            ("", 0.0),
            (None, 0.0),
            ("invalid", 0.0)
        ]
        
        print("Testing price parsing function...")
        for price_str, expected in test_cases:
            result = parse_price(price_str)
            if result == expected:
                print(f"✅ parse_price('{price_str}') = {result}")
            else:
                print(f"❌ parse_price('{price_str}') = {result}, expected {expected}")
                return False
        
        print("✅ Price parsing function working correctly")
        
        # Test data loading (without full execution)
        print("\nTesting component import...")
        from src.web.new_dashboard_poc.components.games_tab import load_deals_data, load_bundles_data
        print("✅ Games tab components can be imported")
        
        return True
        
    except ImportError as e:
        print(f"❌ Component import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Component test failed: {e}")
        return False


def check_etl_integration():
    """Check ETL script integration"""
    print("\n" + "="*60)
    print("⚙️  ETL INTEGRATION CHECK")
    print("="*60)
    
    etl_scripts = [
        'src/etl/games/games_get_deals.py',
        'src/etl/games/games_get_itchio_trending.py', 
        'src/etl/games/games_get_new_releases.py'
    ]
    
    all_good = True
    
    for script in etl_scripts:
        script_path = os.path.join(project_root, script)
        script_name = os.path.basename(script)
        
        if os.path.exists(script_path):
            try:
                # Check syntax by compiling
                with open(script_path, 'r') as f:
                    compile(f.read(), script_path, 'exec')
                print(f"✅ {script_name}: Syntax OK")
            except SyntaxError as e:
                print(f"❌ {script_name}: Syntax error - {e}")
                all_good = False
        else:
            print(f"❌ {script_name}: File not found")
            all_good = False
    
    # Check run scripts include games ETL
    run_scripts = ['run_all_etl.sh', 'run_all_etl.bat']
    
    for run_script in run_scripts:
        script_path = os.path.join(project_root, run_script)
        
        if os.path.exists(script_path):
            with open(script_path, 'r') as f:
                content = f.read()
            
            games_scripts_included = [
                'games_get_deals.py' in content,
                'games_get_itchio_trending.py' in content,
                'games_get_new_releases.py' in content
            ]
            
            if all(games_scripts_included):
                print(f"✅ {run_script}: All games ETL scripts included")
            else:
                print(f"⚠️  {run_script}: Some games ETL scripts missing")
        else:
            print(f"❌ {run_script}: File not found")
    
    return all_good


if __name__ == '__main__':
    print("🚀 Starting Games Functionality Validation")
    
    # Run tests
    tests_passed = run_core_validation()
    
    # Validate data
    data_good = validate_real_data()
    
    # Test components
    components_good = test_components_integration()
    
    # Check ETL integration
    etl_good = check_etl_integration()
    
    print("\n" + "="*60)
    print("🏁 VALIDATION SUMMARY")
    print("="*60)
    
    all_systems_good = tests_passed and data_good and components_good and etl_good
    
    print(f"📋 Core Tests: {'✅ PASSED' if tests_passed else '❌ FAILED'}")
    print(f"📊 Data Quality: {'✅ GOOD' if data_good else '❌ POOR'}")
    print(f"🔧 Components: {'✅ WORKING' if components_good else '❌ BROKEN'}")
    print(f"⚙️  ETL Integration: {'✅ READY' if etl_good else '❌ ISSUES'}")
    
    if all_systems_good:
        print("\n🎉 GAMES FUNCTIONALITY IS FULLY OPERATIONAL!")
        print("   ✅ All core tests passed")
        print("   ✅ Data quality is good")
        print("   ✅ Components working correctly")
        print("   ✅ ETL integration ready")
        print("   🚀 Ready for production use")
        exit_code = 0
    else:
        print(f"\n⚠️  GAMES FUNCTIONALITY HAS ISSUES")
        if not tests_passed:
            print("   ❌ Core tests failed")
        if not data_good:
            print("   ❌ Data quality issues")
        if not components_good:
            print("   ❌ Component issues")
        if not etl_good:
            print("   ❌ ETL integration issues")
        print("   🔧 Requires attention")
        exit_code = 1
    
    print(f"\nValidation completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sys.exit(exit_code) 