"""Content deduplication engine for Watchtower.

This module provides intelligent deduplication of content across multiple sources
using title similarity, content hashing, and URL matching with quality-based
prioritization.
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

from pydantic import BaseModel

from src.models.base import TimestampedModel
from src.utils.logging import get_logger

logger = get_logger(__name__)


class DuplicateGroup(BaseModel):
    """Represents a group of duplicate content items."""

    group_id: str
    items: list[dict[str, Any]]
    primary_item: dict[str, Any]
    duplicate_items: list[dict[str, Any]]
    detection_method: str  # "title_similarity", "content_hash", "url_match"

    model_config = {"arbitrary_types_allowed": True}


class DeduplicationResult(BaseModel):
    """Results of deduplication process."""

    total_items: int
    unique_items: list[dict[str, Any]]
    duplicate_groups: list[DuplicateGroup]
    duplicates_removed: int
    processing_time_seconds: float
    detection_stats: dict[str, int]

    model_config = {"arbitrary_types_allowed": True}


class DeduplicationEngine:
    """Intelligent content deduplication engine.

    Identifies duplicates using:
    - Title similarity (>80% match)
    - Content hashing (exact content matches)
    - URL matching (exact URL matches)

    Prioritizes items based on:
    - Source reputation score (70-100 range)
    - Recency (newer items get higher priority)
    - Completeness (more populated fields = higher quality)
    """

    def __init__(self, title_similarity_threshold: float = 0.8):
        """Initialize deduplication engine.

        Args:
            title_similarity_threshold: Minimum similarity ratio for title matching.
        """
        self.title_similarity_threshold = title_similarity_threshold
        self.source_reputation_scores = self._initialize_source_scores()

        # Performance tracking
        self.stats = {
            "title_similarity_matches": 0,
            "content_hash_matches": 0,
            "url_matches": 0,
            "total_comparisons": 0,
        }

    def _initialize_source_scores(self) -> dict[str, int]:
        """Initialize source reputation scores.

        Higher scores indicate more reputable sources.

        Returns:
            Dictionary mapping source names to reputation scores (70-100 range).
        """
        # Default scores - can be extended based on domain knowledge
        scores = {
            # High reputation academic/research sources
            "arxiv": 95,
            "github": 92,
            "nature": 98,
            "science": 97,
            "acm": 94,
            "ieee": 93,
            # High reputation news sources
            "reuters": 90,
            "ap_news": 89,
            "bbc": 88,
            "npr": 87,
            # Tech news sources
            "hackernews": 85,
            "techcrunch": 82,
            "ars_technica": 84,
            "wired": 83,
            # Course platforms
            "coursera": 86,
            "edx": 85,
            "udacity": 83,
            # Gaming sources
            "steam": 88,
            "epic_games": 85,
            "gog": 82,
            # Default score for unknown sources
            "default": 75,
        }
        return scores

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison.

        Args:
            text: Input text to normalize.

        Returns:
            Normalized text.
        """
        if not text:
            return ""

        # Convert to lowercase and remove extra whitespace
        text = re.sub(r"\s+", " ", text.lower().strip())

        # Remove common punctuation that doesn't affect meaning
        text = re.sub(r"[^\w\s]", "", text)

        return text

    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles.

        Args:
            title1: First title.
            title2: Second title.

        Returns:
            Similarity ratio between 0 and 1.
        """
        if not title1 or not title2:
            return 0.0

        # Normalize titles for better comparison
        norm_title1 = self._normalize_text(title1)
        norm_title2 = self._normalize_text(title2)

        # Use SequenceMatcher for similarity calculation
        similarity = SequenceMatcher(None, norm_title1, norm_title2).ratio()

        return similarity

    def _generate_content_hash(self, item: TimestampedModel) -> str:
        """Generate content hash for an item.

        Uses relevant text fields for hash generation.

        Args:
            item: Content item to hash.

        Returns:
            SHA256 hash of the content.
        """
        # Collect text content from common fields
        content_parts = []

        # Add title if available
        if hasattr(item, "title") and item.title:
            content_parts.append(str(item.title))

        # Add description/summary if available
        for field in ["description", "summary", "content", "abstract"]:
            if hasattr(item, field) and getattr(item, field):
                content_parts.append(str(getattr(item, field)))

        # Add URL if available (for link-based content)
        if hasattr(item, "url") and item.url:
            content_parts.append(str(item.url))

        # Combine all content parts
        full_content = " ".join(content_parts)

        # Generate SHA256 hash
        return hashlib.sha256(full_content.encode("utf-8")).hexdigest()

    def _get_source_score(self, item: TimestampedModel) -> int:
        """Get source reputation score for an item.

        Args:
            item: Content item to score.

        Returns:
            Source reputation score (70-100 range).
        """
        # Try to determine source from various possible fields
        source_name = None

        # Check common source field names
        for field in ["source", "source_name", "platform", "provider", "site"]:
            if hasattr(item, field) and getattr(item, field):
                source_name = str(getattr(item, field)).lower()
                break

        # Try to extract from URL if no source field found
        if not source_name and hasattr(item, "url") and item.url:
            url = str(item.url).lower()
            if "arxiv" in url:
                source_name = "arxiv"
            elif "github" in url:
                source_name = "github"
            elif "steam" in url:
                source_name = "steam"
            elif "coursera" in url:
                source_name = "coursera"

        # Return score for source, or default if unknown
        return self.source_reputation_scores.get(source_name, self.source_reputation_scores["default"])

    def _calculate_recency_score(self, item: TimestampedModel) -> float:
        """Calculate recency score for an item.

        Newer items get higher scores.

        Args:
            item: Content item to score.

        Returns:
            Recency score (0.0 to 1.0).
        """
        # Use created_at timestamp, fall back to current time if not available
        created_at = getattr(item, "created_at", datetime.utcnow())
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except:
                created_at = datetime.utcnow()

        # Calculate days since creation
        days_old = (datetime.utcnow() - created_at).total_seconds() / (24 * 3600)

        # Score decreases with age (1.0 for very new, 0.0 for very old)
        # Use 30 days as the half-life for recency scoring
        recency_score = max(0.0, 1.0 - (days_old / 30.0))

        return recency_score

    def _calculate_completeness_score(self, item: TimestampedModel) -> float:
        """Calculate completeness score based on populated fields.

        Args:
            item: Content item to score.

        Returns:
            Completeness score (0.0 to 1.0).
        """
        # Define important fields for content quality
        important_fields = [
            "title",
            "description",
            "summary",
            "content",
            "abstract",
            "url",
            "author",
            "published_at",
            "created_at",
            "updated_at",
            "tags",
            "category",
            "source",
        ]

        populated_fields = 0
        total_fields = len(important_fields)

        for field in important_fields:
            if hasattr(item, field) and getattr(item, field):
                value = getattr(item, field)
                # Consider non-empty strings and non-empty lists as populated
                if (isinstance(value, str) and value.strip()) or (isinstance(value, (list, tuple)) and value) or (isinstance(value, dict) and value) or not isinstance(value, (str, list, tuple, dict)):
                    populated_fields += 1

        return populated_fields / total_fields

    def _calculate_quality_score(self, item: TimestampedModel) -> float:
        """Calculate overall quality score for an item.

        Combines source reputation, recency, and completeness.

        Args:
            item: Content item to score.

        Returns:
            Quality score (0.0 to 100.0).
        """
        # Get individual component scores
        source_score = self._get_source_score(item)
        recency_score = self._calculate_recency_score(item)
        completeness_score = self._calculate_completeness_score(item)

        # Weight the components
        # Source reputation is most important (40%)
        # Recency is moderately important (35%)
        # Completeness is less important (25%)
        quality_score = source_score * 0.4 + (recency_score * 100) * 0.35 + (completeness_score * 100) * 0.25

        return min(100.0, max(0.0, quality_score))

    def _find_duplicates_by_title(self, items: list[TimestampedModel]) -> list[list[TimestampedModel]]:
        """Find duplicates based on title similarity.

        Optimized using sorting and windowing to avoid O(N^2) complexity.

        Args:
            items: List of items to check for duplicates.

        Returns:
            List of duplicate groups found by title similarity.
        """
        duplicate_groups = []
        processed_ids = set()

        # Filter items with titles and pre-calculate normalized titles
        valid_items = []
        normalized_titles = {}

        for item in items:
            title = getattr(item, "title", "")
            if title:
                valid_items.append(item)
                item_id = getattr(item, "id", str(item))
                normalized_titles[item_id] = self._normalize_text(title)

        # Sort items by normalized title to bring similar items close together
        valid_items.sort(key=lambda x: normalized_titles[getattr(x, "id", str(x))])

        # Comparison window size - items further apart than this are unlikely to be duplicates
        # unless the dataset is extremely dense with very similar titles
        WINDOW_SIZE = 25

        for i in range(len(valid_items)):
            item1 = valid_items[i]
            item1_id = getattr(item1, "id", str(item1))

            if item1_id in processed_ids:
                continue

            title1 = getattr(item1, "title", "")
            norm_title1 = normalized_titles[item1_id]
            current_group = [item1]

            # Check only items within the window
            for j in range(i + 1, min(i + WINDOW_SIZE + 1, len(valid_items))):
                item2 = valid_items[j]
                item2_id = getattr(item2, "id", str(item2))

                if item2_id in processed_ids:
                    continue

                title2 = getattr(item2, "title", "")
                norm_title2 = normalized_titles[item2_id]

                # Optimization: Check length difference first on NORMALIZED titles
                # If lengths differ significantly, ratio cannot be high
                len1, len2 = len(norm_title1), len(norm_title2)
                if abs(len1 - len2) / max(len1, len2) > (1 - self.title_similarity_threshold):
                    continue

                # Optimization: Use quick_ratio first (O(N)) before full ratio (expensive)
                matcher = SequenceMatcher(None, norm_title1, norm_title2)
                if matcher.real_quick_ratio() < self.title_similarity_threshold:
                    continue
                if matcher.quick_ratio() < self.title_similarity_threshold:
                    continue

                # Use SequenceMatcher directly on pre-normalized titles
                similarity = matcher.ratio()
                self.stats["total_comparisons"] += 1

                if similarity >= self.title_similarity_threshold:
                    current_group.append(item2)
                    processed_ids.add(item2_id)
                    self.stats["title_similarity_matches"] += 1

            if len(current_group) > 1:
                duplicate_groups.append(current_group)
                processed_ids.add(item1_id)

        return duplicate_groups

    def _find_duplicates_by_content_hash(self, items: list[TimestampedModel]) -> list[list[TimestampedModel]]:
        """Find duplicates based on content hash.

        Args:
            items: List of items to check for duplicates.

        Returns:
            List of duplicate groups found by content hash.
        """
        # Group items by content hash
        hash_groups = defaultdict(list)

        for item in items:
            content_hash = self._generate_content_hash(item)
            hash_groups[content_hash].append(item)

        # Extract groups with multiple items (duplicates)
        duplicate_groups = []
        for hash_value, group_items in hash_groups.items():
            if len(group_items) > 1:
                duplicate_groups.append(group_items)
                self.stats["content_hash_matches"] += len(group_items) - 1

        return duplicate_groups

    def _find_duplicates_by_url(self, items: list[TimestampedModel]) -> list[list[TimestampedModel]]:
        """Find duplicates based on exact URL matches.

        Args:
            items: List of items to check for duplicates.

        Returns:
            List of duplicate groups found by URL matching.
        """
        # Group items by URL
        url_groups = defaultdict(list)

        for item in items:
            url = getattr(item, "url", "")
            if url:
                url_groups[url].append(item)

        # Extract groups with multiple items (duplicates)
        duplicate_groups = []
        for url, group_items in url_groups.items():
            if len(group_items) > 1:
                duplicate_groups.append(group_items)
                self.stats["url_matches"] += len(group_items) - 1

        return duplicate_groups

    def _merge_duplicate_groups(self, groups: list[list[TimestampedModel]]) -> list[list[TimestampedModel]]:
        """Merge overlapping duplicate groups.

        Items that appear in multiple groups should be merged into a single group.

        Args:
            groups: List of duplicate groups that may overlap.

        Returns:
            List of merged duplicate groups.
        """
        if not groups:
            return []

        # Track which items are in which groups
        item_to_groups = defaultdict(list)

        for group_idx, group in enumerate(groups):
            for item in group:
                item_id = getattr(item, "id", str(item))
                item_to_groups[item_id].append(group_idx)

        # Merge overlapping groups
        merged_groups = []
        processed_indices = set()

        for i, group in enumerate(groups):
            if i in processed_indices:
                continue

            # Start new merged group - remove duplicates manually since set() doesn't work with Pydantic models
            merged_group = []
            seen_ids = set()
            for item in group:
                item_id = getattr(item, "id", str(item))
                if item_id not in seen_ids:
                    merged_group.append(item)
                    seen_ids.add(item_id)

            groups_to_merge = {i}

            # Find all overlapping groups
            changed = True
            while changed:
                changed = False
                new_group_items = []

                for group_idx in list(groups_to_merge):
                    if group_idx in processed_indices:
                        continue

                    for item in groups[group_idx]:
                        item_id = getattr(item, "id", str(item))

                        # Find all groups containing this item
                        overlapping_groups = item_to_groups.get(item_id, [])
                        for overlap_idx in overlapping_groups:
                            if overlap_idx not in groups_to_merge:
                                groups_to_merge.add(overlap_idx)
                                changed = True
                                for new_item in groups[overlap_idx]:
                                    new_item_id = getattr(new_item, "id", str(new_item))
                                    if new_item_id not in seen_ids:
                                        new_group_items.append(new_item)
                                        seen_ids.add(new_item_id)

                if new_group_items:
                    merged_group.extend(new_group_items)

            merged_groups.append(merged_group)
            processed_indices.update(groups_to_merge)

        return merged_groups

    def _select_primary_item(self, items: list[TimestampedModel]) -> TimestampedModel:
        """Select the primary (highest quality) item from a duplicate group.

        Args:
            items: List of duplicate items.

        Returns:
            The highest quality item as the primary.
        """
        if not items:
            raise ValueError("Cannot select primary item from empty group")

        if len(items) == 1:
            return items[0]

        # Calculate quality scores for all items
        scored_items = []
        for item in items:
            if getattr(item, "quality_score", None) is not None:
                quality_score = item.quality_score
            else:
                quality_score = self._calculate_quality_score(item)
            scored_items.append((quality_score, item))

        # Sort by quality score (descending) and return the highest
        scored_items.sort(key=lambda x: x[0], reverse=True)
        return scored_items[0][1]

    def _create_duplicate_group(self, group_id: str, items: list[TimestampedModel], detection_method: str) -> DuplicateGroup:
        """Create a duplicate group object.

        Args:
            group_id: Unique identifier for the duplicate group.
            items: List of duplicate items.
            detection_method: Method used to detect duplicates.

        Returns:
            DuplicateGroup object.
        """
        if len(items) < 2:
            raise ValueError("Duplicate group must contain at least 2 items")

        # Select primary item based on quality
        primary_item = self._select_primary_item(items)

        # Mark other items as duplicates
        duplicate_items = [item for item in items if item != primary_item]

        # Add duplicate metadata to items
        for item in items:
            # Set duplicate-related fields directly (Pydantic models need direct assignment)
            item.duplicate_group_id = group_id
            item.is_duplicate = item != primary_item
            if item.quality_score is None:
                item.quality_score = self._calculate_quality_score(item)

        return DuplicateGroup(
            group_id=group_id,
            items=[item.model_dump() if hasattr(item, "model_dump") else item for item in items],
            primary_item=(primary_item.model_dump() if hasattr(primary_item, "model_dump") else primary_item),
            duplicate_items=[item.model_dump() if hasattr(item, "model_dump") else item for item in duplicate_items],
            detection_method=detection_method,
        )

    def find_duplicates(self, content: list[TimestampedModel]) -> DeduplicationResult:
        """Find and group duplicate content.

        Args:
            content: List of content items to deduplicate.

        Returns:
            DeduplicationResult with duplicate groups and unique items.
        """
        start_time = datetime.utcnow()

        # Reset statistics
        self.stats = {
            "title_similarity_matches": 0,
            "content_hash_matches": 0,
            "url_matches": 0,
            "total_comparisons": 0,
        }

        if not content:
            return DeduplicationResult(
                total_items=0,
                unique_items=[],
                duplicate_groups=[],
                duplicates_removed=0,
                processing_time_seconds=0.0,
                detection_stats=self.stats.copy(),
            )

        logger.info(f"Starting deduplication for {len(content)} items")

        # Find duplicates using different methods
        title_duplicates = self._find_duplicates_by_title(content)
        hash_duplicates = self._find_duplicates_by_content_hash(content)
        url_duplicates = self._find_duplicates_by_url(content)

        # Combine all duplicate groups
        all_groups = title_duplicates + hash_duplicates + url_duplicates

        # Merge overlapping groups
        merged_groups = self._merge_duplicate_groups(all_groups)

        # Create duplicate group objects
        duplicate_groups = []
        processed_items = set()

        for i, group in enumerate(merged_groups):
            if len(group) < 2:
                continue

            group_id = f"duplicate_group_{i}"
            detection_method = "mixed"

            # Determine primary detection method
            group_item_ids = {getattr(item, "id", str(item)) for item in group}

            if any({getattr(item, "id", str(item)) for item in dup_group} & group_item_ids for dup_group in title_duplicates):
                detection_method = "title_similarity"
            elif any({getattr(item, "id", str(item)) for item in dup_group} & group_item_ids for dup_group in hash_duplicates):
                detection_method = "content_hash"
            elif any({getattr(item, "id", str(item)) for item in dup_group} & group_item_ids for dup_group in url_duplicates):
                detection_method = "url_match"

            try:
                duplicate_group = self._create_duplicate_group(group_id, group, detection_method)
                duplicate_groups.append(duplicate_group)

                # Mark all items in this group as processed
                for item in group:
                    processed_items.add(getattr(item, "id", str(item)))

            except Exception as e:
                logger.error(f"Error creating duplicate group {group_id}: {e}")
                continue

        # Filter out duplicate items to get unique items
        unique_items = []
        for item in content:
            item_id = getattr(item, "id", str(item))
            if item_id not in processed_items:
                # Add metadata for non-duplicate items
                item.duplicate_group_id = None
                item.is_duplicate = False
                if item.quality_score is None:
                    item.quality_score = self._calculate_quality_score(item)
                unique_items.append(item)
            else:
                # Find the primary item from duplicate groups and add to unique items
                for group in duplicate_groups:
                    primary_item_id = group.primary_item.get("id") if isinstance(group.primary_item, dict) else getattr(group.primary_item, "id", str(group.primary_item))
                    if getattr(item, "id", str(item)) == primary_item_id:
                        unique_items.append(item)
                        break

        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        duplicates_removed = sum(len(group.duplicate_items) for group in duplicate_groups)

        logger.info(f"Deduplication completed: {len(content)} items -> {len(unique_items)} unique, " f"{duplicates_removed} duplicates removed in {processing_time:.2f}s")

        # Convert model instances to dictionaries for Pydantic compatibility
        unique_items_dict = [item.model_dump() if hasattr(item, "model_dump") else item for item in unique_items]
        duplicate_groups_dict = []
        for group in duplicate_groups:
            if hasattr(group, "model_dump"):
                duplicate_groups_dict.append(group.model_dump())
            else:
                # Convert items to dictionaries
                group_dict = {
                    "group_id": group.group_id,
                    "items": [item.model_dump() if hasattr(item, "model_dump") else item for item in group.items],
                    "primary_item": (group.primary_item.model_dump() if hasattr(group.primary_item, "model_dump") else group.primary_item),
                    "duplicate_items": [item.model_dump() if hasattr(item, "model_dump") else item for item in group.duplicate_items],
                    "detection_method": group.detection_method,
                }
                duplicate_groups_dict.append(DuplicateGroup(**group_dict))

        return DeduplicationResult(
            total_items=len(content),
            unique_items=unique_items_dict,
            duplicate_groups=duplicate_groups_dict,
            duplicates_removed=duplicates_removed,
            processing_time_seconds=processing_time,
            detection_stats=self.stats.copy(),
        )

    def deduplicate_content(self, content: list[TimestampedModel]) -> list[TimestampedModel]:
        """Deduplicate content and return unique items only.

        Args:
            content: List of content items to deduplicate.

        Returns:
            List of unique content items (highest quality from each duplicate group).
        """
        result = self.find_duplicates(content)
        return result.unique_items
