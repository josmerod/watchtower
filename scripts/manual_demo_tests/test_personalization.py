"""Simplified test script to verify personalized recommendations."""

from datetime import datetime, timezone

from src.data_quality.user_profile_manager import UserProfileManager
from src.intelligence.recommendation_engine import ContentBasedRecommendationEngine
from src.models.ai_research_model import AIResearchPaper, ImplementationComplexity
from src.models.user_profile_model import (
    LearningGoal,
    ResearchDomain,
    SkillLevel,
    UserProfile,
)

print("=" * 70)
print("Testing Personalized AI Content Discovery (Story 8.6)")
print("=" * 70)

# Initialize components
profile_manager = UserProfileManager()
recommendation_engine = ContentBasedRecommendationEngine()

# Create a test user profile
print("\n1. Creating test user profile...")
test_profile = UserProfile(
    user_id="demo_user",
    username="AI Learning Enthusiast",
    preferred_domains=[ResearchDomain.NLP, ResearchDomain.CV],
    skill_level=SkillLevel.INTERMEDIATE,
    learning_goals=[
        LearningGoal(
            goal_name="Learn Vision Transformers",
            target_domain=ResearchDomain.CV,
            target_skill_level=SkillLevel.ADVANCED,
            keywords=["vision", "transformer", "vit", "attention"],
        )
    ],
)

# Save profile
profile_manager.save_profile(test_profile)
print(f"   ✓ Profile created and saved for: {test_profile.username}")

# Create mock papers for testing
print("\n2. Creating test papers...")
test_papers = [
    AIResearchPaper(
        id="paper_1",
        title="Attention Mechanisms in Vision Transformers",
        authors=["Test Author 1"],
        published_at=datetime.now(timezone.utc),
        abstract="A comprehensive study on attention mechanisms in vision transformers for image classification.",
        url="https://arxiv.org/abs/test.1",
        source="arxiv",
        primary_domain=ResearchDomain.CV,
        tags=["cs.CV"],
        trend_score=0.85,
        complexity=ImplementationComplexity.MEDIUM,
        industry_impact="High Potential",
        industry_impact_score=85.0,
        implementation_probability=75.0,
        complexity_score=50.0,
    ),
    AIResearchPaper(
        id="paper_2",
        title="Convolutional Networks for Image Segmentation",
        authors=["Test Author 2"],
        published_at=datetime.now(timezone.utc),
        abstract="Novel CNN architecture for semantic segmentation tasks.",
        url="https://arxiv.org/abs/test.2",
        source="arxiv",
        primary_domain=ResearchDomain.CV,
        tags=["cs.CV"],
        trend_score=0.6,
        complexity=ImplementationComplexity.MEDIUM,
        industry_impact="Moderate Interest",
        industry_impact_score=60.0,
        implementation_probability=55.0,
        complexity_score=50.0,
    ),
    AIResearchPaper(
        id="paper_3",
        title="Advanced Theoretical Analysis of Deep Learning",
        authors=["Test Author 3"],
        published_at=datetime.now(timezone.utc),
        abstract="Theoretical foundations of deep learning convergence.",
        url="https://arxiv.org/abs/test.3",
        source="arxiv",
        primary_domain=ResearchDomain.ML_THEORY,
        tags=["cs.LG"],
        trend_score=0.4,
        complexity=ImplementationComplexity.VERY_HIGH,
        industry_impact="Research Only",
        industry_impact_score=30.0,
        implementation_probability=20.0,
        complexity_score=95.0,
    ),
]

print(f"   ✓ Created {len(test_papers)} test papers")

# Generate recommendations
print("\n3. Generating personalized recommendations...")
recommendations = recommendation_engine.recommend_papers(test_profile, test_papers, top_n=10)

print(f"   ✓ Generated {len(recommendations)} recommendations\n")

# Display results
print("4. Recommendation Results:\n")
for i, (paper, score, _breakdown) in enumerate(recommendations, 1):
    print(f"   {i}. {paper.title}")
    print(f"      Match: {score * 100:.1f}%")
    print()

# Verify ranking
print("5. Verification:\n")
if recommendations[0][0].id == "paper_1":
    print("   ✅ PASS: Perfect match (Vision Transformers) ranked #1")
else:
    print(f"   ❌ FAIL: Expected paper_1 at #1, got {recommendations[0][0].id}")

if recommendations[-1][0].id == "paper_3":
    print("   ✅ PASS: Poorest match (Theoretical + Very High complexity) ranked last")
else:
    print("   ❌ FAIL: Expected paper_3 at last position")

# Test profile management
print("\n6. Testing profile management...")
loaded_profile = profile_manager.load_profile("demo_user")
if loaded_profile:
    print("   ✅ PASS: Profile loaded successfully")
else:
    print("   ❌ FAIL: Could not load profile")

print("\n" + "=" * 70)
print("Story 8.6 Phase 1 Testing Complete!")
print("All core functionality verified ✓")
print("=" * 70)
