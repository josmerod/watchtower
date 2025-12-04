import unittest
from typing import Any
from unittest.mock import MagicMock, patch

# Add project root to sys.path to allow direct imports
# This might be handled by your test runner in a real environment
try:
    from src.etl.museums.museum_etl import VirtualMuseumsETL
    from src.models.museums import VirtualMuseumModel

    # If SimpleETL or BaseETL are needed for instantiation and are in a separate file:
    # from src.etl.base import SimpleETL
except ImportError as e:
    print(f"Failed to import modules: {e}")
    print("Ensure that src directory is in PYTHONPATH or test runner handles it.")

    # As a fallback for the tool environment, define placeholders if imports fail
    # This allows the file to be created, though tests won't run correctly without actual modules.
    class SimpleETL:
        def __init__(self, name, description):
            self.name = name
            self.description = description
            self.logger = MagicMock()  # Mock logger

        def run(self):
            pass

        def extract(self):
            pass

        def transform(self, data):
            pass

        def load(self, data):
            pass

        def log_metrics(self):
            pass

    class VirtualMuseumsETL(SimpleETL):  # Inherit from placeholder
        def __init__(self):
            super().__init__("test_etl", "Test ETL")

        # Define methods if they are not in SimpleETL placeholder
        def extract(self) -> list[dict[str, Any]]:
            return []

        def transform(self, data: list[dict[str, Any]]) -> list[Any]:
            return []

    class VirtualMuseumModel:  # Placeholder Pydantic model
        def __init__(self, **kwargs):
            if not self.name:
                raise ValueError("Name is required")  # Simulate Pydantic ValidationError


SAMPLE_RAW_ITEMS_FOR_TRANSFORM = [
    {
        "name": "Test Museum 1",
        "wikidata_url": "http://www.wikidata.org/entity/Q1",
        "description": "A great museum.",
        "website_url": "http://example.com/museum1",
        "virtual_tour_url": "http://example.com/museum1/virtualtour",
        "country_label": "Testland",
        "city_label": "Testville",
        "main_subject_label": "History",
        "image_url": "http://example.com/image1.jpg",
        "latitude": 20.0,
        "longitude": 10.0,
    },
    {  # Item missing 'name' for validation error test
        # 'name': None, # Name is missing
        "wikidata_url": "http://www.wikidata.org/entity/Q3"
    },
    {"name": "Test Museum 2", "wikidata_url": "http://www.wikidata.org/entity/Q2"},
]


class TestVirtualMuseumsETL(unittest.TestCase):
    def setUp(self):
        """Set up for test methods."""
        self.etl = VirtualMuseumsETL()
        # Mock logger to prevent console output during tests unless desired
        self.etl.logger = MagicMock()

    @patch("requests.get")
    def test_extract_successful(self, mock_get):
        """Test successful data extraction from Wikidata."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_WIKIDATA_RESPONSE
        mock_get.return_value = mock_response

        extracted_data = self.etl.extract()

        self.assertIsInstance(extracted_data, list)
        self.assertEqual(len(extracted_data), len(SAMPLE_WIKIDATA_RESPONSE["results"]["bindings"]))

        first_item = extracted_data[0]
        self.assertEqual(first_item["name"], "Test Museum 1")
        self.assertEqual(first_item["wikidata_url"], "http://www.wikidata.org/entity/Q1")
        self.assertEqual(first_item["description"], "A great museum.")
        self.assertEqual(first_item["website_url"], "http://example.com/museum1")
        self.assertEqual(first_item["virtual_tour_url"], "http://example.com/museum1/virtualtour")
        self.assertEqual(first_item["country_label"], "Testland")
        self.assertEqual(first_item["city_label"], "Testville")
        self.assertEqual(first_item["main_subject_label"], "History")
        self.assertEqual(first_item["image_url"], "http://example.com/image1.jpg")
        self.assertEqual(first_item["latitude"], 20.0)  # From "Point(10.0 20.0)"
        self.assertEqual(first_item["longitude"], 10.0)

        mock_get.assert_called_once()
        self.etl.logger.info.assert_any_call(f"Received {len(SAMPLE_WIKIDATA_RESPONSE['results']['bindings'])} items from Wikidata.")

    @patch("requests.get")
    def test_extract_api_error(self, mock_get):
        """Test data extraction when Wikidata API returns an error."""
        mock_get.side_effect = requests.exceptions.RequestException("API is down")

        extracted_data = self.etl.extract()

        self.assertIsInstance(extracted_data, list)
        self.assertEqual(len(extracted_data), 0)
        self.etl.logger.error.assert_any_call("Error during data extraction from Wikidata: API is down")

    @patch("requests.get")
    def test_extract_http_error(self, mock_get):
        """Test data extraction when Wikidata API returns non-200 status."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Not Found")
        mock_get.return_value = mock_response

        extracted_data = self.etl.extract()
        self.assertEqual(extracted_data, [])
        self.etl.logger.error.assert_any_call("Error during data extraction from Wikidata: Not Found")

    def test_transform_successful(self):
        """Test successful transformation of raw data to VirtualMuseumModel instances."""
        # Use only the valid items for this test
        valid_raw_items = [SAMPLE_RAW_ITEMS_FOR_TRANSFORM[0], SAMPLE_RAW_ITEMS_FOR_TRANSFORM[2]]

        transformed_data = self.etl.transform(valid_raw_items)

        self.assertIsInstance(transformed_data, list)
        self.assertEqual(len(transformed_data), len(valid_raw_items))

        for model_instance, raw_item in zip(transformed_data, valid_raw_items, strict=False):
            self.assertIsInstance(model_instance, VirtualMuseumModel)
            self.assertEqual(model_instance.name, raw_item["name"])
            self.assertEqual(model_instance.wikidata_url, raw_item["wikidata_url"])
            # Check a few more fields
            self.assertEqual(model_instance.latitude, raw_item.get("latitude"))
            self.assertEqual(model_instance.description, raw_item.get("description"))

        self.etl.logger.info.assert_any_call(f"Successfully transformed {len(valid_raw_items)} items.")

    def test_transform_validation_error(self):
        """Test transformation when some items have validation errors."""
        # SAMPLE_RAW_ITEMS_FOR_TRANSFORM includes one item designed to fail validation (missing 'name')
        # The placeholder VirtualMuseumModel will raise ValueError if name is missing.
        # Pydantic would raise ValidationError.

        transformed_data = self.etl.transform(SAMPLE_RAW_ITEMS_FOR_TRANSFORM)

        # Expecting 2 valid items, 1 invalid item to be skipped
        self.assertEqual(len(transformed_data), 2)

        # Check that the valid items are present
        valid_urls = {SAMPLE_RAW_ITEMS_FOR_TRANSFORM[0]["wikidata_url"], SAMPLE_RAW_ITEMS_FOR_TRANSFORM[2]["wikidata_url"]}
        transformed_urls = {model.wikidata_url for model in transformed_data}
        self.assertEqual(transformed_urls, valid_urls)

        self.etl.logger.info.assert_any_call(f"Successfully transformed {2} items.")
        self.etl.logger.warning.assert_any_call(f"{1} items failed validation or transformation.")


if __name__ == "__main__":
    # This is to ensure that 'requests' is available in the scope for the test class
    # In a real test environment, manage imports at the top level.
    import requests

    unittest.main()
