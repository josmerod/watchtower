"""Tests for the DeepLearning.AI courses ETL (src/etl/courses/deeplearning_ai_etl.py).

Sitemap and card parsing run against fixture HTML/XML mirroring the real
markup — no live network access.
"""

import json

import pytest

from src.etl.courses import deeplearning_ai_etl as etl

# Trimmed sitemap with course and non-course locs.
FIXTURE_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.deeplearning.ai/</loc></url>
  <url><loc>https://www.deeplearning.ai/courses/agentic-ai</loc></url>
  <url><loc>https://www.deeplearning.ai/courses/building-toward-computer-use-with-anthropic</loc></url>
  <url><loc>https://www.deeplearning.ai/courses/pydantic-for-llm-workflows</loc></url>
  <url><loc>https://www.deeplearning.ai/courses/ai-python-for-beginners/</loc></url>
  <url><loc>https://www.deeplearning.ai/blog/some-post</loc></url>
</urlset>
"""

# Card markup mirroring the real catalog: a partner card, a featured card
# without the figure wrapper, and a "Learn More" link that must be skipped.
FIXTURE_HTML = """
<html><body>
<a class="contents" href="/courses/building-toward-computer-use-with-anthropic">
  <figure class="bg-base-200 relative aspect-video"><img alt="Building toward Computer Use with Anthropic" src="/x.jpg"/></figure>
  <div class="card-body gap-2">
    <div class="text-base-content-secondary body2 flex items-center gap-1">
      <ul><li><img alt="Anthropic" src="/anthropic.png"/></ul>
      <span class="line-clamp-1">Anthropic</span>
    </div>
    <h3 class="card-title subtitle2 line-clamp-2">Building toward Computer Use with Anthropic</h3>
    <p class="body2 text-base-content-secondary line-clamp-3 flex-1">Learn how an AI Assistant is built to use and accomplish tasks on computers.</p>
  </div>
</a>
<a class="contents" href="/courses/pydantic-for-llm-workflows">
  <div class="card-body gap-2">
    <div><span class="line-clamp-1">DeepLearning.AI</span></div>
    <h3 class="card-title">Pydantic for LLM Workflows</h3>
    <p class="body2">Build reliable LLM applications with structured outputs and validated data using Pydantic.</p>
  </div>
</a>
<a href="/courses/agentic-ai">Learn More</a>
<a href="/courses/other-course"><span>Course</span></a>
</body></html>
"""


class TestParseSitemap:
    def test_extracts_course_slugs_only(self):
        slugs = etl.parse_sitemap(FIXTURE_SITEMAP)
        assert slugs == ["agentic-ai", "ai-python-for-beginners", "building-toward-computer-use-with-anthropic", "pydantic-for-llm-workflows"]

    def test_empty_sitemap(self):
        assert etl.parse_sitemap("") == []


class TestParseCourseCards:
    @pytest.fixture
    def cards(self):
        return etl.parse_course_cards(FIXTURE_HTML)

    def test_full_card_with_partner(self, cards):
        card = cards["building-toward-computer-use-with-anthropic"]
        assert card["title"] == "Building toward Computer Use with Anthropic"
        assert card["partner"] == "Anthropic"
        assert card["summary"].startswith("Learn how an AI Assistant")

    def test_card_without_figure(self, cards):
        card = cards["pydantic-for-llm-workflows"]
        assert card["title"] == "Pydantic for LLM Workflows"
        assert card["partner"] == "DeepLearning.AI"

    def test_links_without_heading_are_skipped(self, cards):
        assert "agentic-ai" not in cards
        assert "other-course" not in cards

    def test_empty_html(self):
        assert etl.parse_course_cards("") == {}


class TestBuildCourses:
    def test_enriched_and_fallback_records(self):
        cards = etl.parse_course_cards(FIXTURE_HTML)
        slugs = etl.parse_sitemap(FIXTURE_SITEMAP)
        courses = etl.build_courses(slugs, cards)
        by_slug = {c["url"].rsplit("/", 1)[-1]: c for c in courses}
        assert len(courses) == 4

        enriched = by_slug["agentic-ai"]
        # No card for agentic-ai (only a Learn More link) — title from slug
        assert enriched["title"] == "Agentic Ai"
        assert enriched["partner"] == ""
        assert enriched["metadata"]["card_enriched"] is False

        full = by_slug["building-toward-computer-use-with-anthropic"]
        assert full["title"] == "Building toward Computer Use with Anthropic"
        assert full["partner"] == "Anthropic"
        assert full["metadata"]["card_enriched"] is True

        common = {"is_free": True, "language": "en", "source": "deeplearning.ai/courses"}
        for c in courses:
            assert all(c[k] == v for k, v in common.items())
            assert c["url"].startswith("https://www.deeplearning.ai/courses/")

    def test_title_from_slug(self):
        assert etl._title_from_slug("ai-python-for-beginners") == "Ai Python For Beginners"


class TestFetchAndMain:
    def test_fetch_courses_merges_sources(self, monkeypatch):
        monkeypatch.setattr(etl, "fetch_url", lambda url, max_retries=3: FIXTURE_SITEMAP if "sitemap" in url else FIXTURE_HTML)
        courses = etl.fetch_courses()
        assert len(courses) == 4
        assert {c["partner"] for c in courses} >= {"Anthropic", "DeepLearning.AI", ""}

    def test_fetch_courses_sitemap_down_falls_back_to_cards(self, monkeypatch):
        monkeypatch.setattr(etl, "fetch_url", lambda url, max_retries=3: None if "sitemap" in url else FIXTURE_HTML)
        courses = etl.fetch_courses()
        assert len(courses) == 2
        assert all(c["metadata"]["card_enriched"] for c in courses)

    def test_fetch_courses_all_sources_down(self, monkeypatch):
        monkeypatch.setattr(etl, "fetch_url", lambda url, max_retries=3: None)
        assert etl.fetch_courses() == []

    def test_main_writes_latest_and_archive(self, tmp_path, monkeypatch):
        monkeypatch.setattr(etl, "get_project_root", lambda: str(tmp_path))
        monkeypatch.setattr(etl, "fetch_courses", lambda max_retries=3: [{"title": "T", "url": "https://www.deeplearning.ai/courses/t"}])
        etl.main()
        latest = tmp_path / "data" / "courses" / "deeplearning_ai_latest.json"
        assert latest.exists()
        archives = list((tmp_path / "data" / "courses").glob("deeplearning_ai_2*.json"))
        assert len(archives) == 1
        assert json.loads(latest.read_text(encoding="utf-8"))[0]["title"] == "T"

    def test_main_no_courses_keeps_last_good(self, tmp_path, monkeypatch):
        monkeypatch.setattr(etl, "get_project_root", lambda: str(tmp_path))
        monkeypatch.setattr(etl, "fetch_courses", lambda max_retries=3: [])
        courses_dir = tmp_path / "data" / "courses"
        courses_dir.mkdir(parents=True)
        sentinel = courses_dir / "deeplearning_ai_latest.json"
        sentinel.write_text("[]", encoding="utf-8")
        etl.main()
        assert sentinel.read_text(encoding="utf-8") == "[]"
