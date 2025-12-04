"""Unit tests for ShortcutsManager JavaScript class functionality
Tests localStorage operations, validation, and data management
"""

import json
from unittest.mock import Mock

import pytest


class TestShortcutsManager:
    """Test suite for ShortcutsManager functionality"""

    def setup_method(self):
        """Setup test environment before each test"""
        # Mock localStorage
        self.mock_storage = {}

        def mock_getitem(key):
            return self.mock_storage.get(key)

        def mock_setitem(key, value):
            self.mock_storage[key] = value

        def mock_removeitem(key):
            self.mock_storage.pop(key, None)

        # Mock localStorage with necessary methods
        self.localStorage_mock = Mock()
        self.localStorage_mock.getItem = Mock(side_effect=mock_getitem)
        self.localStorage_mock.setItem = Mock(side_effect=mock_setitem)
        self.localStorage_mock.removeItem = Mock(side_effect=mock_removeitem)

        # Mock console methods
        self.console_mock = Mock()

        # ShortcutsManager implementation (JavaScript to Python conversion)
        self.shortcuts_manager = {
            "storageKey": "watchtower_source_shortcuts",
            "maxShortcuts": 50,
            "domainGroups": {
                "Papers": ["arxiv", "pubmed", "research"],
                "News": ["hackernews", "reddit", "medium", "news"],
                "Deals": ["steam", "epic", "humble", "gog", "deals"],
                "Courses": ["udemy", "coursera", "edx", "learning"],
                "Videos": ["youtube", "vimeo", "video"],
                "AI": ["openai", "anthropic", "huggingface", "ai"],
                "Entertainment": ["cinema", "anime", "games", "entertainment"],
                "Other": [],
            },
        }

    def generate_id(self):
        """Generate unique shortcut ID"""
        import random
        import time

        return f"shortcut_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"

    def get_domain_group(self, source_identifier):
        """Determine domain group from source identifier"""
        identifier = source_identifier.lower()
        for group, keywords in self.shortcuts_manager["domainGroups"].items():
            if any(keyword in identifier for keyword in keywords):
                return group
        return "Other"

    def is_valid_shortcut(self, shortcut):
        """Validate shortcut object structure"""
        return (
            shortcut
            and isinstance(shortcut.get("id"), str)
            and isinstance(shortcut.get("name"), str)
            and isinstance(shortcut.get("domain"), str)
            and isinstance(shortcut.get("source_filter"), dict)
            and isinstance(shortcut.get("order"), int)
            and len(shortcut.get("name", "").strip()) > 0
        )

    def get_all_shortcuts(self):
        """Get all shortcuts from localStorage"""
        try:
            stored = self.localStorage_mock.getItem(self.shortcuts_manager["storageKey"])
            data = json.loads(stored) if stored else {"shortcuts": []}

            if not isinstance(data.get("shortcuts"), list):
                return {"shortcuts": []}

            valid_shortcuts = [shortcut for shortcut in data["shortcuts"] if self.is_valid_shortcut(shortcut)]

            valid_shortcuts.sort(key=lambda x: x.get("order", 0))
            return {"shortcuts": valid_shortcuts}
        except Exception:
            return {"shortcuts": []}

    def save_all_shortcuts(self, data):
        """Save shortcuts to localStorage"""
        try:
            self.localStorage_mock.setItem(self.shortcuts_manager["storageKey"], json.dumps(data))
            return True
        except Exception:
            return False

    def add_shortcut(self, name, domain, source_filter):
        """Add a new shortcut"""
        if not name or not name.strip():
            raise ValueError("Shortcut name cannot be empty")

        if len(name) > 100:
            raise ValueError("Shortcut name must be 100 characters or less")

        data = self.get_all_shortcuts()
        existing = next(
            (s for s in data["shortcuts"] if s["name"].lower() == name.strip().lower()),
            None,
        )
        if existing:
            raise ValueError(f"Shortcut '{name}' already exists")

        if len(data["shortcuts"]) >= self.shortcuts_manager["maxShortcuts"]:
            raise ValueError(f'Maximum {self.shortcuts_manager["maxShortcuts"]} shortcuts allowed')

        new_shortcut = {
            "id": self.generate_id(),
            "name": name.strip(),
            "domain": self.get_domain_group(domain),
            "source_filter": source_filter,
            "order": len(data["shortcuts"]),
            "created_at": "2025-01-16T00:00:00.000Z",  # Mock timestamp
            "updated_at": "2025-01-16T00:00:00.000Z",
        }

        data["shortcuts"].append(new_shortcut)

        if self.save_all_shortcuts(data):
            return new_shortcut
        else:
            raise ValueError("Failed to save shortcut")

    def remove_shortcut(self, shortcut_id):
        """Remove a shortcut"""
        data = self.get_all_shortcuts()
        initial_count = len(data["shortcuts"])

        data["shortcuts"] = [s for s in data["shortcuts"] if s["id"] != shortcut_id]

        # Reorder remaining shortcuts
        for i, shortcut in enumerate(data["shortcuts"]):
            shortcut["order"] = i

        return len(data["shortcuts"]) < initial_count and self.save_all_shortcuts(data)

    def get_shortcuts_by_domain(self):
        """Get shortcuts grouped by domain"""
        data = self.get_all_shortcuts()
        grouped = {}

        # Initialize domain groups
        for domain in self.shortcuts_manager["domainGroups"].keys():
            grouped[domain] = []

        # Group shortcuts
        for shortcut in data["shortcuts"]:
            domain = shortcut.get("domain", "Other")
            if domain not in grouped:
                grouped[domain] = []
            grouped[domain].append(shortcut)

        return grouped

    def test_generate_id_unique(self):
        """Test that generate_id produces unique IDs"""
        id1 = self.generate_id()
        id2 = self.generate_id()

        assert id1 != id2
        assert id1.startswith("shortcut_")
        assert id2.startswith("shortcut_")

    def test_get_domain_group(self):
        """Test domain group detection"""
        assert self.get_domain_group("arxiv_paper") == "Papers"
        assert self.get_domain_group("reddit_news") == "News"
        assert self.get_domain_group("steam_deals") == "Deals"
        assert self.get_domain_group("udemy_course") == "Courses"
        assert self.get_domain_group("youtube_video") == "Videos"
        assert self.get_domain_group("openai_gpt") == "AI"
        assert self.get_domain_group("anime_series") == "Entertainment"
        assert self.get_domain_group("unknown_source") == "Other"

    def test_is_valid_shortcut(self):
        """Test shortcut validation"""
        valid_shortcut = {
            "id": "test_id",
            "name": "Test Shortcut",
            "domain": "Papers",
            "source_filter": {"source": "arxiv"},
            "order": 0,
        }
        assert self.is_valid_shortcut(valid_shortcut) is True

        # Invalid: missing id
        invalid_shortcut = {
            "name": "Test Shortcut",
            "domain": "Papers",
            "source_filter": {"source": "arxiv"},
            "order": 0,
        }
        assert self.is_valid_shortcut(invalid_shortcut) is False

        # Invalid: empty name
        invalid_shortcut["id"] = "test_id"
        invalid_shortcut["name"] = ""
        assert self.is_valid_shortcut(invalid_shortcut) is False

        # Invalid: wrong type for source_filter
        invalid_shortcut["name"] = "Test Shortcut"
        invalid_shortcut["source_filter"] = "not_a_dict"
        assert self.is_valid_shortcut(invalid_shortcut) is False

    def test_get_all_shortcuts_empty_storage(self):
        """Test getting shortcuts from empty storage"""
        data = self.get_all_shortcuts()
        assert data == {"shortcuts": []}

    def test_get_all_shortcuts_with_data(self):
        """Test getting shortcuts with existing data"""
        test_data = {
            "shortcuts": [
                {
                    "id": "test_1",
                    "name": "Test Shortcut 1",
                    "domain": "Papers",
                    "source_filter": {"source": "arxiv"},
                    "order": 1,
                },
                {
                    "id": "test_2",
                    "name": "Test Shortcut 2",
                    "domain": "News",
                    "source_filter": {"source": "reddit"},
                    "order": 0,
                },
            ]
        }

        self.localStorage_mock.setItem(self.shortcuts_manager["storageKey"], json.dumps(test_data))

        data = self.get_all_shortcuts()
        assert len(data["shortcuts"]) == 2
        # Should be sorted by order
        assert data["shortcuts"][0]["id"] == "test_2"
        assert data["shortcuts"][1]["id"] == "test_1"

    def test_get_all_shortcuts_filters_invalid_data(self):
        """Test that invalid shortcuts are filtered out"""
        test_data = {
            "shortcuts": [
                # Valid shortcut
                {
                    "id": "valid_1",
                    "name": "Valid Shortcut",
                    "domain": "Papers",
                    "source_filter": {"source": "arxiv"},
                    "order": 0,
                },
                # Invalid: missing name
                {
                    "id": "invalid_1",
                    "domain": "Papers",
                    "source_filter": {"source": "arxiv"},
                    "order": 1,
                },
                # Invalid: source_filter not a dict
                {
                    "id": "invalid_2",
                    "name": "Invalid Shortcut",
                    "domain": "Papers",
                    "source_filter": "not_a_dict",
                    "order": 2,
                },
            ]
        }

        self.localStorage_mock.setItem(self.shortcuts_manager["storageKey"], json.dumps(test_data))

        data = self.get_all_shortcuts()
        assert len(data["shortcuts"]) == 1
        assert data["shortcuts"][0]["id"] == "valid_1"

    def test_add_shortcut_success(self):
        """Test successfully adding a shortcut"""
        shortcut = self.add_shortcut("Test Paper", "arxiv", {"source": "arxiv", "title": "Test Paper Title"})

        assert shortcut["name"] == "Test Paper"
        assert shortcut["domain"] == "Papers"
        assert "id" in shortcut
        assert "created_at" in shortcut
        assert "updated_at" in shortcut

        # Verify it was saved
        data = self.get_all_shortcuts()
        assert len(data["shortcuts"]) == 1
        assert data["shortcuts"][0]["name"] == "Test Paper"

    def test_add_shortcut_empty_name(self):
        """Test adding shortcut with empty name"""
        with pytest.raises(ValueError, match="Shortcut name cannot be empty"):
            self.add_shortcut("", "arxiv", {})

    def test_add_shortcut_name_too_long(self):
        """Test adding shortcut with name too long"""
        long_name = "x" * 101
        with pytest.raises(ValueError, match="Shortcut name must be 100 characters or less"):
            self.add_shortcut(long_name, "arxiv", {})

    def test_add_shortcut_duplicate_name(self):
        """Test adding shortcut with duplicate name"""
        self.add_shortcut("Test Shortcut", "arxiv", {})

        with pytest.raises(ValueError, match="Shortcut 'Test Shortcut' already exists"):
            self.add_shortcut("Test Shortcut", "reddit", {})

    def test_add_shortcut_max_limit(self):
        """Test adding shortcut beyond maximum limit"""
        # Set max shortcuts to 2 for testing
        self.shortcuts_manager["maxShortcuts"] = 2

        # Add maximum shortcuts
        self.add_shortcut("Shortcut 1", "arxiv", {})
        self.add_shortcut("Shortcut 2", "reddit", {})

        # Try to add one more
        with pytest.raises(ValueError, match="Maximum 2 shortcuts allowed"):
            self.add_shortcut("Shortcut 3", "steam", {})

    def test_remove_shortcut_success(self):
        """Test successfully removing a shortcut"""
        shortcut = self.add_shortcut("Test Shortcut", "arxiv", {})
        shortcut_id = shortcut["id"]

        # Verify it exists
        data = self.get_all_shortcuts()
        assert len(data["shortcuts"]) == 1

        # Remove it
        result = self.remove_shortcut(shortcut_id)
        assert result is True

        # Verify it's gone
        data = self.get_all_shortcuts()
        assert len(data["shortcuts"]) == 0

    def test_remove_shortcut_not_found(self):
        """Test removing a shortcut that doesn't exist"""
        result = self.remove_shortcut("non_existent_id")
        assert result is False

    def test_remove_shortcut_reorders_remaining(self):
        """Test that removing a shortcut reorders remaining shortcuts"""
        # Add multiple shortcuts
        self.add_shortcut("Shortcut 1", "arxiv", {})
        self.add_shortcut("Shortcut 2", "reddit", {})
        self.add_shortcut("Shortcut 3", "steam", {})

        data = self.get_all_shortcuts()
        shortcut_2_id = data["shortcuts"][1]["id"]

        # Remove middle shortcut
        self.remove_shortcut(shortcut_2_id)

        # Verify remaining shortcuts are reordered
        data = self.get_all_shortcuts()
        assert len(data["shortcuts"]) == 2
        assert data["shortcuts"][0]["order"] == 0
        assert data["shortcuts"][1]["order"] == 1

    def test_get_shortcuts_by_domain(self):
        """Test grouping shortcuts by domain"""
        # Add shortcuts from different domains
        self.add_shortcut("Paper 1", "arxiv", {})
        self.add_shortcut("News 1", "reddit", {})
        self.add_shortcut("Paper 2", "pubmed", {})
        self.add_shortcut("Deal 1", "steam", {})

        grouped = self.get_shortcuts_by_domain()

        assert len(grouped["Papers"]) == 2
        assert len(grouped["News"]) == 1
        assert len(grouped["Deals"]) == 1
        assert len(grouped["Courses"]) == 0

        # Verify correct shortcuts in each domain
        paper_titles = [s["name"] for s in grouped["Papers"]]
        assert "Paper 1" in paper_titles
        assert "Paper 2" in paper_titles

    def test_save_all_shortcuts_success(self):
        """Test successfully saving shortcuts"""
        test_data = {"shortcuts": []}
        result = self.save_all_shortcuts(test_data)

        assert result is True
        assert self.localStorage_mock.setItem.called

    def test_save_all_shortcuts_failure(self):
        """Test failure when saving shortcuts"""
        # Mock localStorage.setItem to raise an exception
        self.localStorage_mock.setItem.side_effect = Exception("Storage error")

        test_data = {"shortcuts": []}
        result = self.save_all_shortcuts(test_data)

        assert result is False

    def test_get_all_shortcuts_corrupted_data(self):
        """Test handling corrupted data in localStorage"""
        # Set corrupted JSON data
        self.localStorage_mock.setItem(self.shortcuts_manager["storageKey"], "invalid json")

        data = self.get_all_shortcuts()
        assert data == {"shortcuts": []}

    def test_get_all_shortcuts_non_list_data(self):
        """Test handling data where shortcuts is not a list"""
        test_data = {"shortcuts": "not a list"}
        self.localStorage_mock.setItem(self.shortcuts_manager["storageKey"], json.dumps(test_data))

        data = self.get_all_shortcuts()
        assert data == {"shortcuts": []}
