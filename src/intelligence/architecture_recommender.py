"""Architecture Pattern Recommender Engine."""

import json
from pathlib import Path

from src.models.architecture_pattern_model import ArchitecturePattern
from src.models.user_profile_model import UserProfile
from src.utils.file_system import get_project_root
from src.utils.logging import get_logger


class ArchitectureRecommender:
    """Engine for recommending architecture patterns based on user profile and tech stack."""

    def __init__(self):
        """Initialize the recommender."""
        self.logger = get_logger("ArchitectureRecommender")
        self.patterns: list[ArchitecturePattern] = self._load_patterns()

    def _load_patterns(self) -> list[ArchitecturePattern]:
        """Load patterns from the catalog JSON."""
        try:
            root = Path(get_project_root())
            pattern_file = root / "data" / "architecture" / "output" / "architecture_patterns.json"

            if not pattern_file.exists():
                self.logger.warning(f"Pattern catalog not found at {pattern_file}")
                return []

            with open(pattern_file, encoding="utf-8") as f:
                data = json.load(f)

            patterns = [ArchitecturePattern(**p) for p in data]
            self.logger.info(f"Loaded {len(patterns)} architecture patterns")
            return patterns

        except Exception as e:
            self.logger.error(f"Error loading architecture patterns: {e}")
            return []

    def get_all_patterns(self) -> list[ArchitecturePattern]:
        """Get all available patterns."""
        return self.patterns

    def get_pattern_by_id(self, pattern_id: str) -> ArchitecturePattern | None:
        """Get a specific pattern by ID."""
        for p in self.patterns:
            if p.pattern_id == pattern_id:
                return p
        return None

    def recommend_patterns(self, user_profile: UserProfile, top_n: int = 5) -> list[tuple[ArchitecturePattern, float, dict[str, float]]]:
        """Recommend patterns based on user profile (tech stack, team size, etc.).

        Args:
            user_profile: User profile containing tech stack and preferences
            top_n: Number of recommendations to return

        Returns:
            List of tuples (pattern, score, breakdown)
        """
        scored_patterns = []

        for pattern in self.patterns:
            score, breakdown = self.score_pattern(user_profile, pattern)
            scored_patterns.append((pattern, score, breakdown))

        # Sort by score descending
        scored_patterns.sort(key=lambda x: x[1], reverse=True)

        return scored_patterns[:top_n]

    def score_pattern(self, user_profile: UserProfile, pattern: ArchitecturePattern) -> tuple[float, dict[str, float]]:
        """Score a pattern against a user profile.

        Scoring Factors:
        1. Tech Stack Match (50%): Do user technologies match compatible technologies?
        2. Team Size Match (30%): Does user team size match recommended size?
        3. Complexity Match (20%): Does pattern complexity match user skill level?

        Returns:
            Tuple (total_score, breakdown_dict)
        """
        breakdown = {}

        # 1. Tech Stack Match (50%)
        tech_score = self._score_tech_stack(user_profile, pattern)
        breakdown["tech_match"] = tech_score * 0.5

        # 2. Team Size Match (30%)
        team_score = self._score_team_size(user_profile, pattern)
        breakdown["team_match"] = team_score * 0.3

        # 3. Complexity/Skill Match (20%)
        skill_score = self._score_skill_complexity(user_profile, pattern)
        breakdown["skill_match"] = skill_score * 0.2

        total_score = sum(breakdown.values())
        return total_score, breakdown

    def _score_tech_stack(self, user_profile: UserProfile, pattern: ArchitecturePattern) -> float:
        """Score based on technology compatibility."""
        if not hasattr(user_profile, "tech_stack") or not user_profile.tech_stack:
            return 0.5  # Neutral if no stack defined

        user_techs = [t.lower().strip() for t in user_profile.tech_stack]
        pattern_techs = [t.lower().strip() for t in pattern.compatible_technologies]

        if not pattern_techs:
            return 0.5  # Neutral if pattern has no specific tech constraints

        matches = 0
        for tech in user_techs:
            # Check for direct match or partial match (e.g. "aws" in "aws lambda")
            if any(tech in pt or pt in tech for pt in pattern_techs):
                matches += 1

        # Normalize: if we have at least 1 match, it's good. More is better.
        # Cap at 1.0
        if matches == 0:
            return 0.1
        return min(1.0, 0.4 + (matches * 0.2))

    def _score_team_size(self, user_profile: UserProfile, pattern: ArchitecturePattern) -> float:
        """Score based on team size fit."""
        if not hasattr(user_profile, "team_size") or not user_profile.team_size:
            return 0.5

        if not pattern.recommended_team_size:
            return 0.5

        user_size = user_profile.team_size.lower()
        # Handle string vs Enum
        rec_size = pattern.recommended_team_size if isinstance(pattern.recommended_team_size, str) else pattern.recommended_team_size.value
        rec_size = rec_size.lower()

        # Direct match
        if user_size in rec_size or rec_size in user_size:
            return 1.0

        # Logic for partial matches
        # If pattern is for "Medium to Large" and user is "Medium", match
        if "medium" in user_size and ("medium" in rec_size or "large" in rec_size):
            return 0.8
        if "large" in user_size and ("medium" in rec_size or "large" in rec_size):
            return 0.8
        if "small" in user_size and "small" in rec_size:
            return 1.0

        # Mismatch (e.g. Solo dev vs Microservices)
        if "solo" in user_size and ("large" in rec_size or "medium" in rec_size):
            return 0.1

        return 0.4

    def _score_skill_complexity(self, user_profile: UserProfile, pattern: ArchitecturePattern) -> float:
        """Score based on skill level vs complexity."""
        # Map skill levels to appropriate max complexity
        # Beginner -> Low
        # Intermediate -> Medium
        # Advanced -> High
        # Expert -> Very High

        skill = user_profile.skill_level.value.lower() if hasattr(user_profile.skill_level, "value") else user_profile.skill_level.lower()

        # Handle string vs Enum
        complexity = pattern.complexity if isinstance(pattern.complexity, str) else pattern.complexity.value
        complexity = complexity.lower()

        if skill == "beginner":
            if complexity == "low":
                return 1.0
            if complexity == "medium":
                return 0.6
            return 0.2

        if skill == "intermediate":
            if complexity == "medium":
                return 1.0
            if complexity == "low":
                return 0.9
            if complexity == "high":
                return 0.6
            return 0.3

        if skill == "advanced":
            if complexity == "high":
                return 1.0
            if complexity == "medium":
                return 0.9
            if complexity == "very high":
                return 0.8
            return 0.7

        if skill == "expert":
            return 1.0  # Experts can handle anything

        return 0.5

    def explain_recommendation(self, pattern: ArchitecturePattern, breakdown: dict[str, float]) -> str:
        """Generate explanation for recommendation."""
        reasons = []

        if breakdown.get("tech_match", 0) > 0.3:
            reasons.append("Fits your tech stack")
        if breakdown.get("team_match", 0) > 0.2:
            reasons.append("Suitable for your team size")
        if breakdown.get("skill_match", 0) > 0.15:
            reasons.append("Matches your skill level")

        if not reasons:
            return "General recommendation"

        return " • ".join(reasons)
