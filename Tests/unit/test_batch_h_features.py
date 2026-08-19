"""Unit tests for batch H features: saved items (KG F3) and tech radar extraction (TR-F1)."""

import json

import pytest

from src.web.dashboard.components import saved_items
from src.web.dashboard.components.tech_radar_tab import TECH_DICTIONARY, _extract_tech_mentions


@pytest.fixture
def clean_saved_file(tmp_path, monkeypatch):
    """Point the saved-items store at a temp file."""
    import pathlib

    fake = tmp_path / "saved_items.json"
    monkeypatch.setattr(saved_items, "SAVED_FILE", fake)
    return fake


class TestSavedItems:
    def test_roundtrip_save_unsave(self, clean_saved_file):
        item = {"url": "http://example.com/a", "title": "A", "source": "src"}
        h = saved_items.item_hash(item["url"], item["title"])
        assert saved_items.toggle_saved(item) is True
        assert saved_items.is_saved(h)
        assert saved_items.load_saved()[0]["hash"] == h
        assert saved_items.toggle_saved(item) is False
        assert not saved_items.is_saved(h)
        assert saved_items.load_saved() == []

    def test_hash_stable_and_url_prefers_url(self, clean_saved_file):
        assert saved_items.item_hash("HTTP://X.COM/1 ", "t") == saved_items.item_hash("http://x.com/1", "other")
        # Same title different URL -> different hash (URL wins as key)
        assert saved_items.item_hash("http://x.com/1", "t") != saved_items.item_hash("http://x.com/2", "t")

    def test_toggle_survives_reload(self, clean_saved_file):
        saved_items.toggle_saved({"url": "http://example.com/b", "title": "B"})
        # simulate a fresh process reading the same file
        assert json.loads(clean_saved_file.read_text(encoding="utf-8"))[0]["url"] == "http://example.com/b"


class TestTechRadarExtraction:
    def test_dictionary_has_all_quadrants(self):
        quadrants = set(TECH_DICTIONARY.values())
        assert quadrants == {"Techniques", "Tools", "Platforms", "Languages & Frameworks"}

    def test_extraction_returns_records(self):
        # Reads whatever local radar data exists; on CI/dev machines with data
        # this yields records, without data it must simply return a list.
        records = _extract_tech_mentions()
        assert isinstance(records, list)
        for record in records:
            assert record["mentions"] >= 2
            assert record["ring"] in {"Adopt", "Trial", "Assess"}
            assert record["quadrant"] in {"Techniques", "Tools", "Platforms", "Languages & Frameworks"}
