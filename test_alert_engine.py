#!/usr/bin/env python3
"""Test script for the alert rule engine."""

from datetime import datetime, time
from src.alerts.engine import AlertEngine
from src.alerts.models import (
    AlertRule, SourceMatchCondition, KeywordMatchCondition,
    CategoryMatchCondition, PriceThresholdCondition, TimeRange
)


def create_test_alert_rules():
    """Create test alert rules for testing."""

    # Rule 1: Source match for ArXiv papers
    arxiv_rule = AlertRule(
        id="test-rule-1",
        name="ArXiv Papers Alert",
        description="Alert when new ArXiv papers are found",
        user_id="test-user",
        conditions=[
            SourceMatchCondition(
                condition_type="source_match",
                value="arxiv",
                operator="contains"
            )
        ]
    )

    # Rule 2: Keyword match for Python
    python_rule = AlertRule(
        id="test-rule-2",
        name="Python Content Alert",
        description="Alert for content containing 'python'",
        user_id="test-user",
        conditions=[
            KeywordMatchCondition(
                condition_type="keyword_match",
                value="python",
                operator="contains",
                case_sensitive=False
            )
        ]
    )

    # Rule 3: Price threshold for free content
    free_deals_rule = AlertRule(
        id="test-rule-3",
        name="Free Deals Alert",
        description="Alert for free deals and courses",
        user_id="test-user",
        conditions=[
            PriceThresholdCondition(
                condition_type="price_threshold",
                value=0.0,
                operator="equals",
                currency="USD"
            )
        ]
    )

    return [arxiv_rule, python_rule, free_deals_rule]


def save_test_rules(rules):
    """Save test rules to file system for testing."""
    import json
    from pathlib import Path

    # Create test directory
    test_data_dir = Path("data/alerts/test-user")
    test_data_dir.mkdir(parents=True, exist_ok=True)

    # Save rules to file
    rules_file = test_data_dir / "rules.json"
    rules_data = [rule.model_dump() for rule in rules]

    with open(rules_file, 'w', encoding='utf-8') as f:
        json.dump(rules_data, f, indent=2, ensure_ascii=False, default=str)

    print(f"Saved {len(rules)} test rules to {rules_file}")


def create_test_content():
    """Create test content items for evaluation."""

    content_items = [
        {
            "id": "content-1",
            "title": "Machine Learning Advances in 2024",
            "description": "New developments in ML",
            "source": "arxiv",
            "url": "https://arxiv.org/abs/2024.12345",
            "categories": ["machine-learning", "ai"]
        },
        {
            "id": "content-2",
            "title": "Python Programming Best Practices",
            "description": "A guide to Python programming",
            "source": "github",
            "url": "https://github.com/user/python-guide",
            "price": None,
            "categories": ["programming", "python"]
        },
        {
            "id": "content-3",
            "title": "Free Python Course",
            "description": "Learn Python for free",
            "source": "udemy",
            "price": 0.0,
            "url": "https://udemy.com/free-python-course",
            "categories": ["programming", "python"]
        },
        {
            "id": "content-4",
            "title": "JavaScript Framework Tutorial",
            "description": "Learn modern JavaScript",
            "source": "medium",
            "price": 29.99,
            "url": "https://medium.com/js-tutorial",
            "categories": ["javascript", "web-development"]
        }
    ]

    return content_items


def test_alert_engine():
    """Test the alert rule engine."""

    print("Testing Alert Rule Engine...")
    print("=" * 50)

    # Create and save test rules
    test_rules = create_test_alert_rules()
    save_test_rules(test_rules)

    # Create test content
    test_content = create_test_content()

    # Initialize alert engine
    engine = AlertEngine()

    print(f"Testing {len(test_content)} content items against {len(test_rules)} alert rules")
    print()

    total_matches = 0
    for i, content in enumerate(test_content, 1):
        print(f"Testing Content {i}: {content['title'][:50]}...")

        # Evaluate content against rules
        alert_events = engine.evaluate_content(content, "test-user")

        print(f"  -> Generated {len(alert_events)} alert events")

        for event in alert_events:
            print(f"     Rule: {event.rule_name}")
            print(f"     Message: {event.message[:80]}...")
            print(f"     Severity: {event.severity}")
            print()

        total_matches += len(alert_events)

    # Get engine metrics
    metrics = engine.get_metrics()
    print("Engine Performance Metrics:")
    print(f"  Evaluations: {metrics['evaluations_count']}")
    print(f"  Matches: {metrics['matches_count']}")
    print(f"  Errors: {metrics['errors_count']}")
    print(f"  Match Rate: {metrics['match_rate']:.1f}%")
    print(f"  Cached Users: {metrics['cached_users']}")
    print(f"  Dedup Cache Size: {metrics['dedup_cache_size']}")
    print()

    # Test deduplication (should not generate alerts for duplicate content)
    print("Testing deduplication...")
    duplicate_content = test_content[0]  # Use first content item again
    duplicate_alerts = engine.evaluate_content(duplicate_content, "test-user")
    print(f"Duplicate content generated {len(duplicate_alerts)} alerts (should be 0)")

    # Expected behavior verification
    assert total_matches == 4, f"Expected 4 total alert matches, got {total_matches}"
    assert duplicate_alerts == [], f"Expected no alerts for duplicate content, got {len(duplicate_alerts)}"

    print("[SUCCESS] All alert engine tests passed!")
    return True


if __name__ == "__main__":
    test_alert_engine()