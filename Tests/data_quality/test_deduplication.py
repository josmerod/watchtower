"""Comprehensive tests for the content deduplication engine.

Tests cover:
- Title similarity algorithms
- Content hashing
- URL matching
- Quality-based prioritization
- Performance with large datasets
- Edge cases and error handling
"""

from datetime import datetime, timedelta

import pytest

from src.data_quality.deduplication import DeduplicationEngine
from src.models.base import TimestampedModel


class TestContentItem(TimestampedModel):
    """Test model for content items."""

    title: str | None = None
    description: str | None = None
    url: str | None = None
    source: str | None = None
    author: str | None = None
    content: str | None = None
    published_at: datetime | None = None


class TestDeduplicationEngine:
    """Test suite for DeduplicationEngine."""

    def test_init_default_parameters(self):
        """Test engine initialization with default parameters."""
        engine = DeduplicationEngine()
        assert engine.title_similarity_threshold == 0.8
        assert len(engine.source_reputation_scores) > 0
        assert "default" in engine.source_reputation_scores

    def test_init_custom_parameters(self):
        """Test engine initialization with custom parameters."""
        engine = DeduplicationEngine(title_similarity_threshold=0.9)
        assert engine.title_similarity_threshold == 0.9

    def test_normalize_text(self):
        """Test text normalization for comparison."""
        engine = DeduplicationEngine()

        # Basic normalization
        assert engine._normalize_text("Hello World") == "hello world"
        assert engine._normalize_text("  Hello   WORLD  ") == "hello world"
        assert engine._normalize_text("Hello, World!") == "hello world"

        # Edge cases
        assert engine._normalize_text("") == ""
        assert engine._normalize_text(None) == ""
        assert engine._normalize_text("   ") == ""

    def test_calculate_title_similarity(self):
        """Test title similarity calculation."""
        engine = DeduplicationEngine()

        # Exact matches
        similarity = engine._calculate_title_similarity("Test Title", "Test Title")
        assert similarity == 1.0

        # Similar titles
        similarity = engine._calculate_title_similarity("Machine Learning Algorithms", "Machine Learning Algorithm Review")
        assert similarity > 0.8

        # Different titles
        similarity = engine._calculate_title_similarity("Machine Learning", "Quantum Physics")
        assert similarity < 0.3

        # Edge cases
        similarity = engine._calculate_title_similarity("", "Test")
        assert similarity == 0.0

        similarity = engine._calculate_title_similarity(None, "Test")
        assert similarity == 0.0

    def test_generate_content_hash(self):
        """Test content hash generation."""
        engine = DeduplicationEngine()

        item1 = TestContentItem(
            title="Test Title",
            description="Test Description",
            url="https://example.com/test",
        )
        item2 = TestContentItem(
            title="Test Title",
            description="Test Description",
            url="https://example.com/test",
        )

        hash1 = engine._generate_content_hash(item1)
        hash2 = engine._generate_content_hash(item2)

        # Same content should generate same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

        # Different content should generate different hash
        item3 = TestContentItem(title="Different Title")
        hash3 = engine._generate_content_hash(item3)
        assert hash1 != hash3

    def test_source_reputation_scoring(self):
        """Test source reputation scoring."""
        engine = DeduplicationEngine()

        # Known sources
        arxiv_item = TestContentItem(source="arxiv")
        assert engine._get_source_score(arxiv_item) >= 90

        # Unknown source should get default score
        unknown_item = TestContentItem(source="unknown_source")
        assert engine._get_source_score(unknown_item) == engine.source_reputation_scores["default"]

        # Source from URL
        github_url_item = TestContentItem(url="https://github.com/user/repo", source=None)
        assert engine._get_source_score(github_url_item) >= 90

    def test_recency_scoring(self):
        """Test recency scoring calculation."""
        engine = DeduplicationEngine()

        # Very recent item
        recent_item = TestContentItem(created_at=datetime.utcnow())
        recent_score = engine._calculate_recency_score(recent_item)
        assert recent_score >= 0.9

        # Old item (30 days ago)
        old_date = datetime.utcnow() - timedelta(days=30)
        old_item = TestContentItem(created_at=old_date)
        old_score = engine._calculate_recency_score(old_item)
        assert old_score <= 0.1

        # Very old item should get score 0
        very_old_date = datetime.utcnow() - timedelta(days=100)
        very_old_item = TestContentItem(created_at=very_old_date)
        very_old_score = engine._calculate_recency_score(very_old_item)
        assert very_old_score == 0.0

    def test_completeness_scoring(self):
        """Test completeness scoring calculation."""
        engine = DeduplicationEngine()

        # Complete item with many fields
        complete_item = TestContentItem(
            title="Test",
            description="Description",
            url="https://example.com",
            author="Author",
            content="Content",
            source="Source",
        )
        complete_score = engine._calculate_completeness_score(complete_item)
        assert complete_score >= 0.5

        # Minimal item
        minimal_item = TestContentItem(title="Test")
        minimal_score = engine._calculate_completeness_score(minimal_item)
        assert minimal_score <= 0.2

    def test_quality_scoring(self):
        """Test overall quality scoring."""
        engine = DeduplicationEngine()

        # High-quality item
        high_quality_item = TestContentItem(
            title="Important Research Paper",
            description="Comprehensive description",
            source="arxiv",
            created_at=datetime.utcnow(),
            url="https://arxiv.org/abs/1234",
            author="Famous Author",
        )
        high_score = engine._calculate_quality_score(high_quality_item)
        assert high_score >= 80.0

        # Low-quality item
        low_quality_item = TestContentItem(
            title="Brief note",
            created_at=datetime.utcnow() - timedelta(days=60),
            source="unknown_blog",
        )
        low_score = engine._calculate_quality_score(low_quality_item)
        assert low_score <= 60.0

    def test_find_duplicates_by_title(self):
        """Test duplicate detection by title similarity."""
        engine = DeduplicationEngine(title_similarity_threshold=0.8)

        items = [
            TestContentItem(title="Machine Learning in Healthcare"),
            TestContentItem(title="Machine Learning for Healthcare"),  # Similar
            TestContentItem(title="Quantum Computing Basics"),  # Different
            TestContentItem(title="Machine Learning in Healthcare Review"),  # Similar
        ]

        duplicate_groups = engine._find_duplicates_by_title(items)

        # Should find one duplicate group with 3 similar items
        assert len(duplicate_groups) == 1
        assert len(duplicate_groups[0]) == 3

        # Check that all items in group are indeed similar
        group = duplicate_groups[0]
        for i, item1 in enumerate(group):
            for item2 in group[i + 1 :]:
                similarity = engine._calculate_title_similarity(item1.title, item2.title)
                assert similarity >= 0.8

    def test_find_duplicates_by_content_hash(self):
        """Test duplicate detection by content hash."""
        engine = DeduplicationEngine()

        items = [
            TestContentItem(
                title="Same Content",
                description="Same description",
                url="https://example.com/same",
            ),
            TestContentItem(
                title="Same Content",  # Same as above
                description="Same description",
                url="https://example.com/same",  # Same URL for identical content
            ),
            TestContentItem(title="Different Content", description="Different description"),
        ]

        duplicate_groups = engine._find_duplicates_by_content_hash(items)

        # Should find one duplicate group with 2 items
        assert len(duplicate_groups) == 1
        assert len(duplicate_groups[0]) == 2

    def test_find_duplicates_by_url(self):
        """Test duplicate detection by URL matching."""
        engine = DeduplicationEngine()

        items = [
            TestContentItem(title="First Article", url="https://example.com/article"),
            TestContentItem(
                title="Second Article",
                url="https://example.com/article",  # Same URL
            ),
            TestContentItem(title="Third Article", url="https://example.com/different"),
        ]

        duplicate_groups = engine._find_duplicates_by_url(items)

        # Should find one duplicate group with 2 items
        assert len(duplicate_groups) == 1
        assert len(duplicate_groups[0]) == 2

    def test_select_primary_item(self):
        """Test selection of primary item from duplicate group."""
        engine = DeduplicationEngine()

        # Create items with different quality scores
        high_quality_item = TestContentItem(
            title="High Quality",
            source="arxiv",
            created_at=datetime.utcnow(),
            description="Detailed description",
        )
        high_quality_item.quality_score = 95.0

        medium_quality_item = TestContentItem(
            title="Medium Quality",
            source="unknown",
            created_at=datetime.utcnow() - timedelta(days=10),
            description="Brief description",
        )
        medium_quality_item.quality_score = 75.0

        low_quality_item = TestContentItem(title="Low Quality", created_at=datetime.utcnow() - timedelta(days=60))
        low_quality_item.quality_score = 60.0

        duplicate_group = [low_quality_item, high_quality_item, medium_quality_item]
        primary = engine._select_primary_item(duplicate_group)

        # Should select the highest quality item
        assert primary == high_quality_item

    def test_find_duplicates_comprehensive(self):
        """Test comprehensive duplicate detection with mixed methods."""
        engine = DeduplicationEngine()

        # Create diverse test data
        items = [
            # Title similarity group - very similar titles
            TestContentItem(title="Machine Learning Review", source="arxiv"),
            TestContentItem(title="Machine Learning Review Paper", source="github"),
            TestContentItem(title="Machine Learning Review", source="arxiv"),
            TestContentItem(title="Machine Learning Review Paper", source="github"),
            TestContentItem(title="Machine Learning Review Extra", source="techcrunch"),  # Similar enough (>0.8)
            # Content hash group - exact same content
            TestContentItem(
                title="Research Paper",
                description="Detailed analysis of machine learning algorithms",
                url="https://example.com/research",
            ),
            TestContentItem(
                title="Research Paper",
                description="Detailed analysis of machine learning algorithms",
                url="https://example.com/research",  # Identical content
            ),
            # URL match group
            TestContentItem(title="First Article", url="https://example.com/article1"),
            TestContentItem(title="Second Article", url="https://example.com/article1"),
            # Unique items - clearly different
            TestContentItem(title="Quantum Computing Fundamentals"),
            TestContentItem(title="Climate Change Analysis"),
        ]

        result = engine.find_duplicates(items)

        # Should find 3 duplicate groups at minimum (may find more due to title similarity)
        assert len(result.duplicate_groups) >= 3

        # Should have fewer unique items than total items
        assert len(result.unique_items) < len(items)
        assert result.duplicates_removed > 0
        assert result.total_items == len(items)

        # Check that all groups have primary items
        for group in result.duplicate_groups:
            assert group.primary_item is not None
            assert len(group.duplicate_items) >= 1
            assert len(group.items) == len(group.duplicate_items) + 1

    def test_merge_duplicate_groups(self):
        """Test merging of overlapping duplicate groups."""
        engine = DeduplicationEngine()

        item1 = TestContentItem(title="Test A")
        item2 = TestContentItem(title="Test A")  # Exact match to A
        item3 = TestContentItem(title="Test A")  # Exact match to A

        # Create groups that should merge: [item1, item2] and [item2, item3]
        groups = [[item1, item2], [item2, item3]]

        merged = engine._merge_duplicate_groups(groups)

        # Should merge into single group
        assert len(merged) == 1
        assert len(merged[0]) == 3

        # Check that all items are in the merged group (by ID comparison)
        merged_ids = {getattr(item, "id", str(item)) for item in merged[0]}
        expected_ids = {getattr(item, "id", str(item)) for item in [item1, item2, item3]}
        assert merged_ids == expected_ids

    def test_empty_data_handling(self):
        """Test handling of empty data."""
        engine = DeduplicationEngine()

        result = engine.find_duplicates([])
        assert result.total_items == 0
        assert len(result.unique_items) == 0
        assert len(result.duplicate_groups) == 0
        assert result.duplicates_removed == 0

        unique_items = engine.deduplicate_content([])
        assert len(unique_items) == 0

    def test_single_item_handling(self):
        """Test handling of single item."""
        engine = DeduplicationEngine()

        items = [TestContentItem(title="Single Item")]
        result = engine.find_duplicates(items)

        assert result.total_items == 1
        assert len(result.unique_items) == 1
        assert len(result.duplicate_groups) == 0
        assert result.duplicates_removed == 0

        # Item should not be marked as duplicate
        unique_item = result.unique_items[0]
        assert unique_item.get("is_duplicate") is False
        assert unique_item.get("duplicate_group_id") is None

    def test_performance_large_dataset(self):
        """Test performance with large dataset."""
        import time

        engine = DeduplicationEngine()

        # Create 10,000 items with some duplicates
        items = []
        import uuid

        for i in range(8000):
            # Use UUIDs prefix to ensure titles are distinct and sorted distributively
            items.append(TestContentItem(title=f"{uuid.uuid4()} Unique Item"))

        # Add duplicate groups - use exact matches for better control
        for i in range(1000):
            base_title = f"Duplicate Group {uuid.uuid4()}"
            items.extend(
                [
                    TestContentItem(title=base_title),
                    TestContentItem(title=base_title),
                    TestContentItem(title=base_title),
                ]
            )

        # Should complete within reasonable time (less than 30 seconds)
        start_time = time.time()
        result = engine.find_duplicates(items)
        end_time = time.time()

        processing_time = end_time - start_time
        assert processing_time < 30.0, f"Processing took too long: {processing_time:.2f}s"

        # Should find duplicates (number may vary due to exact matching vs similarity)
        assert len(result.duplicate_groups) >= 1000  # At least 1000 groups
        assert result.duplicates_removed >= 2000  # At least 2000 duplicates
        assert len(result.unique_items) <= 9000  # No more than 9000 unique items (8000 + 1000 originals)

    def test_statistics_tracking(self):
        """Test that deduplication statistics are properly tracked."""
        engine = DeduplicationEngine()

        items = [
            TestContentItem(title="Similar Title 1"),
            TestContentItem(title="Similar Title 2"),
            TestContentItem(title="Same Content", description="Same"),
            TestContentItem(title="Same Content", description="Same"),
            TestContentItem(title="Same Content", description="Same"),  # Same title for hash match
            TestContentItem(title="URL Test", url="https://example.com"),
            TestContentItem(title="URL Test 2", url="https://example.com"),
        ]

        result = engine.find_duplicates(items)

        # Check detection stats
        stats = result.detection_stats
        assert stats["title_similarity_matches"] > 0
        assert stats["content_hash_matches"] > 0
        assert stats["url_matches"] > 0
        assert stats["total_comparisons"] > 0

    def test_error_handling(self):
        """Test error handling with invalid data."""
        engine = DeduplicationEngine()

        # Test with malformed items (should not crash)
        items = [
            TestContentItem(),  # Empty item
            TestContentItem(title=""),  # Empty title
            TestContentItem(title="Normal Item"),  # Normal item
        ]

        # Should not raise exceptions
        result = engine.find_duplicates(items)
        # Empty items should be deduplicated against each other
        assert result.total_items == 3
        # Should have 2 unique items: 1 empty group representative + 1 normal item
        assert len(result.unique_items) == 2

    def test_duplicate_group_creation(self):
        """Test duplicate group object creation."""
        engine = DeduplicationEngine()

        items = [
            TestContentItem(title="Item 1"),
            TestContentItem(title="Item 2"),
        ]

        # Give items quality scores
        items[0].quality_score = 80.0
        items[1].quality_score = 90.0

        group = engine._create_duplicate_group("test_group", items, "title_similarity")

        assert group.group_id == "test_group"
        assert len(group.items) == 2
        assert len(group.duplicate_items) == 1
        assert group.detection_method == "title_similarity"

        # Check that items were marked correctly (by ID comparison since they're converted to dicts)
        primary_item_id = group.primary_item.get("id")
        duplicate_item_id = group.duplicate_items[0].get("id")

        assert primary_item_id == items[1].id  # Higher quality item should be primary
        assert duplicate_item_id == items[0].id
        assert items[1].is_duplicate is False
        assert items[0].is_duplicate is True
        assert items[1].duplicate_group_id == "test_group"
        assert items[0].duplicate_group_id == "test_group"

    def test_quality_score_calculation_edge_cases(self):
        """Test quality score calculation with edge cases."""
        engine = DeduplicationEngine()

        # Item with minimal fields
        minimal_item = TestContentItem(title="Minimal")
        score = engine._calculate_quality_score(minimal_item)
        assert 0.0 <= score <= 100.0

        # Item with all fields
        complete_item = TestContentItem(
            title="Complete",
            description="Description",
            url="https://example.com",
            author="Author",
            content="Content",
            source="arxiv",
        )
        score = engine._calculate_quality_score(complete_item)
        assert 0.0 <= score <= 100.0
        assert score >= engine._get_source_score(complete_item) * 0.4  # Base source score contribution


if __name__ == "__main__":
    pytest.main([__file__])
