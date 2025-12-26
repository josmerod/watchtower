"""Test script for Architecture Intelligence."""

from src.intelligence.architecture_recommender import ArchitectureRecommender
from src.models.user_profile_model import SkillLevel, UserProfile

print("=" * 70)
print("Testing Architecture Intelligence (Story 8.7)")
print("=" * 70)

# 1. Initialize Recommender
print("\n1. Initializing Recommender...")
recommender = ArchitectureRecommender()
patterns = recommender.get_all_patterns()
print(f"   ✓ Loaded {len(patterns)} patterns from catalog")

# Verify specific patterns exist
microservices = recommender.get_pattern_by_id("microservices")
if microservices:
    print(f"   ✓ Found pattern: {microservices.name}")
else:
    print("   ❌ Failed to find 'microservices' pattern")

# 2. Test Recommendations for Different Profiles

# Profile A: Python/AWS/Microservices/Large Team
print("\n2. Testing Profile A (Python/AWS/Large Team)...")
profile_a = UserProfile(
    user_id="user_a",
    username="Cloud Architect",
    skill_level=SkillLevel.EXPERT,
    tech_stack=["Python", "AWS Lambda", "DynamoDB", "Docker"],
    team_size="Large (20+)",
)

recs_a = recommender.recommend_patterns(profile_a, top_n=3)
print("   Top 3 Recommendations:")
for p, score, breakdown in recs_a:
    print(f"   - {p.name} (Score: {score:.2f})")
    print(f"     Explanation: {recommender.explain_recommendation(p, breakdown)}")

# Verify Serverless is recommended (due to AWS Lambda)
if any(p.pattern_id == "serverless" for p, _, _ in recs_a):
    print("   ✅ PASS: Serverless recommended for AWS Lambda user")
else:
    print("   ❌ FAIL: Serverless NOT recommended for AWS Lambda user")

# Profile B: Solo Dev/Simple App
print("\n3. Testing Profile B (Solo Dev/Simple App)...")
profile_b = UserProfile(
    user_id="user_b",
    username="Indie Hacker",
    skill_level=SkillLevel.BEGINNER,
    tech_stack=["Django", "PostgreSQL"],
    team_size="Solo",
)

recs_b = recommender.recommend_patterns(profile_b, top_n=3)
print("   Top 3 Recommendations:")
for p, score, breakdown in recs_b:
    print(f"   - {p.name} (Score: {score:.2f})")
    print(f"     Explanation: {recommender.explain_recommendation(p, breakdown)}")

# Verify Layered/Monolith is recommended (due to Django/Solo)
if any(p.pattern_id == "layered" for p, _, _ in recs_b):
    print("   ✅ PASS: Layered Architecture recommended for Django/Solo user")
else:
    print("   ❌ FAIL: Layered Architecture NOT recommended for Django/Solo user")

# Verify Microservices is NOT highly recommended (complexity mismatch)
micro_score = next((s for p, s, _ in recs_b if p.pattern_id == "microservices"), 0)
if micro_score < 0.6:
    print(f"   ✅ PASS: Microservices score low ({micro_score:.2f}) for Solo dev")
else:
    print(f"   ❌ FAIL: Microservices score too high ({micro_score:.2f}) for Solo dev")

print("\n" + "=" * 70)
print("Architecture Intelligence Testing Complete!")
print("=" * 70)
