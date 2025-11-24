"""Test script to verify AI Research alerts."""

from datetime import datetime, timezone
from src.models.ai_research_model import AIResearchPaper, ResearchDomain, ImplementationComplexity
from src.alerts.engine import AlertEngine

# Create a high-potential paper (should trigger alert)
high_potential_paper = AIResearchPaper(
    id="test_paper_1",
    title="Advanced Transformer Models for Generative AI",
    authors=["Test Author"],
    published_at=datetime.now(timezone.utc),
    abstract="This paper presents a breakthrough in transformer architectures.",
    url="https://arxiv.org/abs/test.12345",
    source="arxiv",
    primary_domain=ResearchDomain.GENERATIVE,  # Fixed: use GENERATIVE instead of MACHINE_LEARNING
    tags=["cs.LG", "cs.AI"],
    trend_score=0.9,  # High trend score (0-1 scale)
    complexity=ImplementationComplexity.MEDIUM,
    industry_impact="High Potential",  # This should trigger the alert
    implementation_probability=85.0,
    industry_impact_score=85.0,
    complexity_score=50.0
)

# Create a low-potential paper (should NOT trigger alert)
low_potential_paper = AIResearchPaper(
    id="test_paper_2",
    title="Theoretical Analysis of Some Algorithm",
    authors=["Another Author"],
    published_at=datetime.now(timezone.utc),  # Fixed: published_at instead of published_date
    abstract="A theoretical paper on algorithms.",
    url="https://arxiv.org/abs/test.67890",
    source="arxiv",
    primary_domain=ResearchDomain.OTHER,
    tags=["cs.DS"],
    trend_score=0.3,  # Low trend score
    complexity=ImplementationComplexity.VERY_HIGH,
    industry_impact="Research Only",  # Should NOT trigger
    implementation_probability=15.0,
    industry_impact_score=15.0,
    complexity_score=85.0
)

# Initialize Alert Engine
alert_engine = AlertEngine()

print("Testing Alerts for AI Research Papers\n")
print("=" * 60)

# Test high-potential paper
print("\n1. Testing HIGH POTENTIAL paper:")
print(f"   Title: {high_potential_paper.title}")
print(f"   Impact: {high_potential_paper.industry_impact}")
print(f"   Trend Score: {high_potential_paper.trend_score}")

content_1 = high_potential_paper.model_dump(mode='json')
content_1['source'] = 'ai_research'
content_1['description'] = f"{high_potential_paper.abstract} [Impact: {high_potential_paper.industry_impact}]"

events_1 = alert_engine.evaluate_content(content_1, user_id="admin")
print(f"   → Alerts Generated: {len(events_1)}")
if events_1:
    for event in events_1:
        print(f"     ✓ Alert: {event.rule_name} - {event.severity}")

# Test low-potential paper
print("\n2. Testing LOW POTENTIAL paper:")
print(f"   Title: {low_potential_paper.title}")
print(f"   Impact: {low_potential_paper.industry_impact}")
print(f"   Trend Score: {low_potential_paper.trend_score}")

content_2 = low_potential_paper.model_dump(mode='json')
content_2['source'] = 'ai_research'
content_2['description'] = f"{low_potential_paper.abstract} [Impact: {low_potential_paper.industry_impact}]"

events_2 = alert_engine.evaluate_content(content_2, user_id="admin")
print(f"   → Alerts Generated: {len(events_2)}")
if events_2:
    for event in events_2:
        print(f"     ✓ Alert: {event.rule_name} - {event.severity}")

print("\n" + "=" * 60)
print(f"\nTotal alerts: {len(events_1) + len(events_2)}")
print("\nAlert files should be in: data/alerts/admin/events/")
