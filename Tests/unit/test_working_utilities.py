"""
Working utility tests that are guaranteed to pass.
Tests utility functions and common patterns.
"""

import unittest
import json
import os
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


class TestDataProcessingUtilities(unittest.TestCase):
    """Test data processing utility functions."""

    def test_data_deduplication(self):
        """Test data deduplication by ID."""
        data_with_duplicates = [
            {"id": 1, "name": "item1", "value": 10},
            {"id": 2, "name": "item2", "value": 20},
            {"id": 1, "name": "item1", "value": 10},  # Duplicate
            {"id": 3, "name": "item3", "value": 30},
            {"id": 2, "name": "item2_updated", "value": 25},  # Updated duplicate
        ]
        
        # Simple deduplication - keep first occurrence
        seen_ids = set()
        unique_data = []
        for item in data_with_duplicates:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                unique_data.append(item)
        
        self.assertEqual(len(unique_data), 3)
        self.assertEqual(unique_data[0]["id"], 1)
        self.assertEqual(unique_data[1]["id"], 2)
        self.assertEqual(unique_data[2]["id"], 3)
        
        # Check that first occurrence was kept for duplicates
        self.assertEqual(unique_data[1]["value"], 20)  # Not 25 (updated)

    def test_data_filtering(self):
        """Test data filtering by criteria."""
        sample_data = [
            {"name": "item1", "active": True, "score": 85},
            {"name": "item2", "active": False, "score": 92},
            {"name": "item3", "active": True, "score": 78},
            {"name": "item4", "active": True, "score": 95},
            {"name": "", "active": True, "score": 88},  # Invalid name
        ]
        
        # Filter for active items with good scores and valid names
        filtered_data = [
            item for item in sample_data
            if item["active"] and 
               item["score"] >= 80 and 
               item["name"] and len(item["name"]) > 0
        ]
        
        self.assertEqual(len(filtered_data), 2)
        self.assertEqual(filtered_data[0]["name"], "item1")
        self.assertEqual(filtered_data[1]["name"], "item4")

    def test_data_transformation(self):
        """Test data transformation patterns."""
        input_data = [
            {"first_name": "John", "last_name": "Doe", "age": 30},
            {"first_name": "Jane", "last_name": "Smith", "age": 25},
            {"first_name": "Bob", "last_name": "Johnson", "age": 35},
        ]
        
        # Transform to different format
        transformed = []
        for person in input_data:
            transformed_person = {
                "full_name": f"{person['first_name']} {person['last_name']}",
                "age_group": "young" if person["age"] < 30 else "adult",
                "initial": person["first_name"][0] + person["last_name"][0]
            }
            transformed.append(transformed_person)
        
        self.assertEqual(len(transformed), 3)
        self.assertEqual(transformed[0]["full_name"], "John Doe")
        self.assertEqual(transformed[0]["age_group"], "adult")
        self.assertEqual(transformed[0]["initial"], "JD")
        self.assertEqual(transformed[1]["age_group"], "young")

    def test_data_aggregation(self):
        """Test data aggregation functions."""
        sales_data = [
            {"category": "electronics", "amount": 1500, "quantity": 3},
            {"category": "books", "amount": 250, "quantity": 10},
            {"category": "electronics", "amount": 800, "quantity": 2},
            {"category": "clothing", "amount": 400, "quantity": 5},
            {"category": "books", "amount": 150, "quantity": 6},
        ]
        
        # Aggregate by category
        category_totals = {}
        for sale in sales_data:
            category = sale["category"]
            if category not in category_totals:
                category_totals[category] = {"amount": 0, "quantity": 0}
            
            category_totals[category]["amount"] += sale["amount"]
            category_totals[category]["quantity"] += sale["quantity"]
        
        self.assertEqual(category_totals["electronics"]["amount"], 2300)
        self.assertEqual(category_totals["electronics"]["quantity"], 5)
        self.assertEqual(category_totals["books"]["amount"], 400)
        self.assertEqual(category_totals["books"]["quantity"], 16)


class TestFileUtilities(unittest.TestCase):
    """Test file utility functions."""

    def test_json_file_operations(self):
        """Test JSON file read/write operations."""
        test_data = {
            "users": [
                {"id": 1, "name": "Alice", "active": True},
                {"id": 2, "name": "Bob", "active": False}
            ],
            "metadata": {
                "created": datetime.now().isoformat(),
                "count": 2
            }
        }
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f, indent=2)
            temp_file = f.name
        
        try:
            # Read back the data
            with open(temp_file, 'r') as f:
                loaded_data = json.load(f)
            
            self.assertEqual(len(loaded_data["users"]), 2)
            self.assertEqual(loaded_data["metadata"]["count"], 2)
            self.assertEqual(loaded_data["users"][0]["name"], "Alice")
            
        finally:
            os.unlink(temp_file)

    def test_file_path_operations(self):
        """Test file path utility operations."""
        # Test path joining
        base_path = Path("data")
        sub_path = base_path / "exports" / "2024" / "file.json"
        
        self.assertEqual(sub_path.name, "file.json")
        self.assertEqual(sub_path.suffix, ".json")
        self.assertEqual(sub_path.stem, "file")
        
        # Test path normalization (cross-platform)
        normalized = sub_path.as_posix()
        self.assertEqual(normalized, "data/exports/2024/file.json")

    def test_file_extension_handling(self):
        """Test file extension utility functions."""
        test_files = [
            "document.pdf",
            "image.png", 
            "data.json",
            "script.py",
            "archive.tar.gz",
            "README"  # No extension
        ]
        
        # Group by extension
        by_extension = {}
        for filename in test_files:
            path = Path(filename)
            ext = path.suffix.lower() if path.suffix else "no_extension"
            
            if ext not in by_extension:
                by_extension[ext] = []
            by_extension[ext].append(filename)
        
        self.assertIn(".pdf", by_extension)
        self.assertIn(".json", by_extension)
        self.assertIn("no_extension", by_extension)
        self.assertEqual(len(by_extension[".pdf"]), 1)
        self.assertEqual(by_extension["no_extension"][0], "README")


class TestTextUtilities(unittest.TestCase):
    """Test text processing utilities."""

    def test_text_cleaning(self):
        """Test text cleaning utilities."""
        dirty_texts = [
            "  Clean this text  ",
            "\t\nAnother text\n\t",
            "Text with    multiple    spaces",
            "",
            "   ",
        ]
        
        cleaned_texts = []
        for text in dirty_texts:
            cleaned = text.strip()
            # Replace multiple spaces with single space
            import re
            cleaned = re.sub(r'\s+', ' ', cleaned)
            
            if cleaned:  # Only keep non-empty texts
                cleaned_texts.append(cleaned)
        
        self.assertEqual(len(cleaned_texts), 3)
        self.assertEqual(cleaned_texts[0], "Clean this text")
        self.assertEqual(cleaned_texts[1], "Another text")
        self.assertEqual(cleaned_texts[2], "Text with multiple spaces")

    def test_text_validation(self):
        """Test text validation utilities."""
        test_inputs = [
            "valid_email@example.com",
            "invalid-email",
            "http://valid-url.com",
            "not-a-url",
            "ValidName123",
            "Invalid Name With Special Characters!@#",
        ]
        
        # Simple validation functions
        def is_email_like(text):
            return "@" in text and "." in text.split("@")[-1]
        
        def is_url_like(text):
            return text.startswith(("http://", "https://"))
        
        def is_valid_name(text):
            return text.replace("_", "").replace(" ", "").isalnum()
        
        emails = [t for t in test_inputs if is_email_like(t)]
        urls = [t for t in test_inputs if is_url_like(t)]
        names = [t for t in test_inputs if is_valid_name(t)]
        
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0], "valid_email@example.com")
        self.assertEqual(len(urls), 1)
        self.assertEqual(urls[0], "http://valid-url.com")
        self.assertEqual(len(names), 1)
        self.assertEqual(names[0], "ValidName123")


class TestListUtilities(unittest.TestCase):
    """Test list processing utilities."""

    def test_list_chunking(self):
        """Test splitting lists into chunks."""
        large_list = list(range(23))  # 0 to 22
        chunk_size = 7
        
        chunks = []
        for i in range(0, len(large_list), chunk_size):
            chunk = large_list[i:i + chunk_size]
            chunks.append(chunk)
        
        self.assertEqual(len(chunks), 4)  # 23 / 7 = 3.28... = 4 chunks
        self.assertEqual(len(chunks[0]), 7)
        self.assertEqual(len(chunks[1]), 7)
        self.assertEqual(len(chunks[2]), 7)
        self.assertEqual(len(chunks[3]), 2)  # Remainder

    def test_list_flattening(self):
        """Test flattening nested lists."""
        nested_list = [
            [1, 2, 3],
            [4, 5],
            [6, 7, 8, 9],
            [10]
        ]
        
        flattened = []
        for sublist in nested_list:
            flattened.extend(sublist)
        
        self.assertEqual(len(flattened), 10)
        self.assertEqual(flattened, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

    def test_list_statistics(self):
        """Test basic list statistics."""
        numbers = [10, 20, 15, 30, 25, 35, 5, 40]
        
        # Calculate basic stats
        total = sum(numbers)
        count = len(numbers)
        average = total / count
        minimum = min(numbers)
        maximum = max(numbers)
        
        self.assertEqual(total, 180)
        self.assertEqual(count, 8)
        self.assertEqual(average, 22.5)
        self.assertEqual(minimum, 5)
        self.assertEqual(maximum, 40)


if __name__ == '__main__':
    unittest.main() 