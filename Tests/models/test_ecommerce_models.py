# Tests/models/test_ecommerce_models.py
import sys
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
try:
    from pydantic import ValidationError
    from src.models.ecommerce import ShoppyProduct, ShoppyRawData
except ImportError as e:
    print(
        f"Error importing modules: {e}. Ensure PYTHONPATH is set correctly or run from project root."
    )
    sys.exit(1)


def test_shoppy_product_valid_creation():
    print("Testing ShoppyProduct Valid Creation...")
    try:
        now = datetime.now()
        product_data = {}
        product = ShoppyProduct(**product_data)
        assert product.product_id == "test_prod_001"
        assert product.name == "Test Product"
        assert product.rating == 4.5
        print("ShoppyProduct Valid Creation: PASSED")
        return True
    except ValidationError as ve:
        print(f"ShoppyProduct Valid Creation: FAILED - Validation Error: {ve}")
        return False
    except Exception as e:
        print(f"ShoppyProduct Valid Creation: FAILED - {e}")
        return False


def test_shoppy_product_invalid_data():
    print("\nTesting ShoppyProduct Invalid Data...")
    try:
        # Missing required fields
        try:
            ShoppyProduct(
                product_id="incomplete"
            )  # name, price, url, fetched_at, parsed_at are missing
            print(
                "ShoppyProduct Invalid Data: FAILED - ValidationError not raised for missing fields"
            )
            return False
        except ValidationError:
            pass  # Expected

        # Invalid URL
        try:
            now = datetime.now()
            ShoppyProduct(
                product_id="badurl",
                name="Bad URL Product",
                price="1.00",
                url="not-a-url",
                fetched_at=now,
                parsed_at=now,
            )
            print(
                "ShoppyProduct Invalid Data: FAILED - ValidationError not raised for invalid URL"
            )
            return False
        except ValidationError:
            pass  # Expected

        # Invalid data type for rating
        try:
            now = datetime.now()
            ShoppyProduct(
                product_id="badrating",
                name="Bad Rating",
                price="1.00",
                url="http://example.com",
                fetched_at=now,
                parsed_at=now,
                rating="not-a-float",
            )
            print(
                "ShoppyProduct Invalid Data: FAILED - ValidationError not raised for invalid rating type"
            )
            return False
        except ValidationError:
            pass  # Expected

        print("ShoppyProduct Invalid Data: PASSED")
        return True
    except Exception as e:
        print(f"ShoppyProduct Invalid Data: FAILED - Unexpected error: {e}")
        return False


def test_shoppy_raw_data_creation():
    print("\nTesting ShoppyRawData Creation...")
    try:
        now = datetime.now()
        raw_data_payload = {}
        raw_data_obj = ShoppyRawData(**raw_data_payload)
        assert raw_data_obj.product_id == "raw_001"
        assert "HTML content" in raw_data_obj.raw_content
        print("ShoppyRawData Creation: PASSED")
        return True
    except ValidationError as ve:
        print(f"ShoppyRawData Creation: FAILED - Validation Error: {ve}")
        return False
    except Exception as e:
        print(f"ShoppyRawData Creation: FAILED - {e}")
        return False


def main():
    print("E-commerce Models Test Suite")
    print("=" * 40)

    tests = [
        test_shoppy_product_valid_creation,
        test_shoppy_product_invalid_data,
        test_shoppy_raw_data_creation,
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
        print("All E-commerce Models tests passed!")


if __name__ == "__main__":
    main()
