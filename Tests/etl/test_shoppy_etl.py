# Tests/etl/test_shoppy_etl.py
import sys
import os
import json
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Ensure the module can be imported
try:
    from src.etl.ecommerce.shoppy_etl import ShoppyScraper, run_shoppy_etl
    from src.models.ecommerce import ShoppyProduct # Expected to be used by ETL output
except ImportError as e:
    print(f"Error importing modules: {e}. Ensure PYTHONPATH is set correctly or run from project root.")
    sys.exit(1)

# Define a directory for test outputs if needed, or mock them all
TEST_DATA_DIR = project_root / "Tests" / "test_data" / "shoppy"
# os.makedirs(TEST_DATA_DIR, exist_ok=True) # Not creating physical files for unit tests

def test_shoppy_scraper_initialization():
    print("Testing ShoppyScraper Initialization...")
    try:
        scraper = ShoppyScraper(base_url="https://test.shoppy.gg/")
        assert scraper.base_url == "https://test.shoppy.gg/", "Base URL not set correctly"
        print("ShoppyScraper Initialization: PASSED")
        return True
    except Exception as e:
        print(f"ShoppyScraper Initialization: FAILED - {e}")
        return False

def test_shoppy_scraper_fetch_product_data_mock():
    print("\nTesting ShoppyScraper Fetch Product Data (Mock)...")
    try:
        scraper = ShoppyScraper()
        # This method is a placeholder, so we test its current mock behavior
        product_id = "test_product_123"
        data = scraper.fetch_product_data(product_id)
        assert data["product_id"] == product_id, "Product ID mismatch"
        assert "raw_content" in data, "Raw content missing"
        assert "Mock HTML" in data["raw_content"], "Mock content incorrect"
        assert "fetched_at" in data, "Fetched_at timestamp missing"
        print("ShoppyScraper Fetch Product Data (Mock): PASSED")
        return True
    except Exception as e:
        print(f"ShoppyScraper Fetch Product Data (Mock): FAILED - {e}")
        return False

def test_shoppy_scraper_parse_product_data_mock():
    print("\nTesting ShoppyScraper Parse Product Data (Mock)...")
    try:
        scraper = ShoppyScraper()
        product_id = "test_parse_123"
        now = datetime.now()
        raw_data = {
            "product_id": product_id,
            "raw_content": "<html><body>Mock HTML for parsing</body></html>",
            "fetched_at": now.isoformat()
        }
        # This method is a placeholder, so we test its current mock behavior
        parsed_data = scraper.parse_product_data(raw_data)
        assert parsed_data["product_id"] == product_id, "Product ID mismatch in parsed data"
        assert parsed_data["name"] == f"Placeholder Product Name for {product_id}", "Parsed name incorrect"
        assert "price" in parsed_data, "Price missing in parsed data"
        assert "parsed_at" in parsed_data, "Parsed_at timestamp missing"
        print("ShoppyScraper Parse Product Data (Mock): PASSED")
        return True
    except Exception as e:
        print(f"ShoppyScraper Parse Product Data (Mock): FAILED - {e}")
        return False

@patch("src.etl.ecommerce.shoppy_etl.os.makedirs")
@patch("builtins.open", new_callable=mock_open)
@patch("src.etl.ecommerce.shoppy_etl.ShoppyScraper")
def test_run_shoppy_etl_mock_flow(MockShoppyScraper, mock_file_open, mock_os_makedirs):
    print("\nTesting run_shoppy_etl (Mock Flow)...")
    try:
        # Configure the mock scraper
        mock_scraper_instance = MockShoppyScraper.return_value

        raw_data_sample = {"product_id": "prod1", "raw_content": "raw", "fetched_at": datetime.now().isoformat()}
        processed_data_sample = {
            "product_id": "prod1", "name": "Test Product", "price": "1 USD",
            "seller": "Test Seller", "url": "http://example.com/prod1",
            "description": "Test desc",
            "fetched_at": datetime.now().isoformat(), "parsed_at": datetime.now().isoformat()
        }

        mock_scraper_instance.fetch_product_data.return_value = raw_data_sample
        mock_scraper_instance.parse_product_data.return_value = processed_data_sample

        product_ids_to_test = ["prod1", "prod2"]
        processed_results = run_shoppy_etl(product_ids_to_test)

        # Correct the expected path for os.makedirs by resolving project_root against DATA_DIR
        # DATA_DIR in shoppy_etl.py is "data/shoppy"
        # project_root / "data" / "shoppy"
        expected_data_dir_path = project_root / "data" / "shoppy"
        mock_os_makedirs.assert_called_once_with(expected_data_dir_path, exist_ok=True)

        # Check fetch and parse calls
        assert mock_scraper_instance.fetch_product_data.call_count == len(product_ids_to_test)
        assert mock_scraper_instance.parse_product_data.call_count == len(product_ids_to_test)

        # Check file writing operations
        # RAW_DATA_PATH = os.path.join(DATA_DIR, "shoppy_raw_data_{timestamp}.json")
        # PROCESSED_DATA_PATH = os.path.join(DATA_DIR, "shoppy_processed_data.json")
        # These paths are relative to the execution of shoppy_etl.py, which means they are rooted from project_root.

        raw_data_path_part = str(expected_data_dir_path / "shoppy_raw_data")
        processed_data_path_part = str(expected_data_dir_path / "shoppy_processed_data.json")

        # Collect all file paths opened for writing
        write_calls_args = [call_args[0][0] for call_args in mock_file_open.call_args_list if call_args[0][1] == 'w']

        assert any(raw_data_path_part in str(path) for path in write_calls_args), f"Raw data file not written to expected dir part: {raw_data_path_part}. Paths written: {write_calls_args}"
        assert any(processed_data_path_part in str(path) for path in write_calls_args), f"Processed data file not written to expected dir part: {processed_data_path_part}. Paths written: {write_calls_args}"

        # Check content of processed results
        assert len(processed_results) == len(product_ids_to_test)
        assert processed_results[0]["name"] == "Test Product"

        print("run_shoppy_etl (Mock Flow): PASSED")
        return True
    except AssertionError as e:
        print(f"run_shoppy_etl (Mock Flow): FAILED - Assertion Error: {e}")
        return False
    except Exception as e:
        print(f"run_shoppy_etl (Mock Flow): FAILED - Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("Shoppy ETL Test Suite")
    print("=" * 40)

    tests = [
        test_shoppy_scraper_initialization,
        test_shoppy_scraper_fetch_product_data_mock,
        test_shoppy_scraper_parse_product_data_mock,
        test_run_shoppy_etl_mock_flow,
    ]

    passed_count = 0
    failed_count = 0

    for test_func in tests:
        if test_func():
            passed_count += 1
        else:
            failed_count += 1
        print("-" * 40)

    print(f"\nResults: {passed_count} passed, {failed_count} failed")

    if failed_count > 0:
        sys.exit(1)
    else:
        print("All Shoppy ETL tests passed!")

if __name__ == "__main__":
    main()
