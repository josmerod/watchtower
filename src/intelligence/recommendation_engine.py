"""Recommendation engine for personalized AI content discovery."""

from typing import List, Dict, Tuple
from datetime import datetime

from src.models.ai_research_model import AIResearchPaper, ResearchDomain, ImplementationComplexity
from src.models.user_profile_model import UserProfile, SkillLevel
from src.utils.logging import get_logger


class ContentBasedRecommendationEngine:
    """Content-based recommendation engine for AI research papers."""
    
    # Complexity to skill level mapping
    COMPLEXITY_SKILL_MAPPING = {
        SkillLevel.BEGINNER: [ImplementationComplexity.LOW],
        SkillLevel.INTERMEDIATE: [ImplementationComplexity.LOW, ImplementationComplexity.MEDIUM],
        SkillLevel.ADVANCED: [ImplementationComplexity.MEDIUM, ImplementationComplexity.HIGH],
        SkillLevel.EXPERT: [ImplementationComplexity.HIGH, ImplementationComplexity.VERY_HIGH],
    }
    
    def __init__(self):
        """Initialize the recommendation engine."""
        self.logger = get_logger("RecommendationEngine")
    
    def recommend_papers(
        self,
        user_profile: UserProfile,
        available_papers: List[AIResearchPaper],
        top_n: int = 10,
        exclude_completed: bool = True
    ) -> List[Tuple[AIResearchPaper, float, Dict[str, float]]]:
        """Generate personalized paper recommendations.
        
        Args:
            user_profile: User profile with preferences
            available_papers: List of papers to recommend from
            top_n: Number of recommendations to return
            exclude_completed: Whether to exclude already-completed papers
            
        Returns:
            List of tuples: (paper, total_score, score_breakdown)
        """
        self.logger.info(f"Generating recommendations for user {user_profile.user_id}")
        
        # Filter out completed papers if requested
        if exclude_completed:
            available_papers = [
                p for p in available_papers
                if p.id not in user_profile.completed_papers
            ]
        
        # Score all papers
        scored_papers = []
        for paper in available_papers:
            score, breakdown = self.score_relevance(user_profile, paper)
            scored_papers.append((paper, score, breakdown))
        
        # Sort by score descending
        scored_papers.sort(key=lambda x: x[1], reverse=True)
        
        # Return top N
        recommendations = scored_papers[:top_n]
        
        self.logger.info(
            f"Generated {len(recommendations)} recommendations "
            f"(filtered from {len(available_papers)} papers)"
        )
        
        return recommendations
    
    def score_relevance(
        self,
        user_profile: UserProfile,
        paper: AIResearchPaper
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate relevance score for a paper.
        
        Scoring breakdown:
        - Domain match: 40%
        - Complexity match: 30%
        - Trend score: 20%
        - Learning goal keywords: 10%
        
        Args:
            user_profile: User profile
            paper: Paper to score
            
        Returns:
            Tuple of (total_score, score_breakdown_dict)
        """
        breakdown = {}
        
        # 1. Domain match (40%)
        domain_score = self._score_domain_match(user_profile, paper)
        breakdown['domain_match'] = domain_score * 0.4
        
        # 2. Complexity match (30%)
        complexity_score = self._score_complexity_match(user_profile, paper)
        breakdown['complexity_match'] = complexity_score * 0.3
        
        # 3. Trend score (20%)
        trend_score = paper.trend_score  # Already 0-1 scale
        breakdown['trend_score'] = trend_score * 0.2
        
        # 4. Learning goal keyword match (10%)
        goal_score = self._score_learning_goals(user_profile, paper)
        breakdown['goal_keywords'] = goal_score * 0.1
        
        # Calculate total
        total_score = sum(breakdown.values())
        
        return total_score, breakdown
    
    def _score_domain_match(self, user_profile: UserProfile, paper: AIResearchPaper) -> float:
        """Score domain match between user preferences and paper.
        
        Returns:
            Score from 0.0 to 1.0
        """
        if not user_profile.preferred_domains:
            return 0.5  # Neutral score if no preferences set
        
        # Check if paper's domain is in user's preferred domains
        if paper.primary_domain in user_profile.preferred_domains:
            return 1.0
        
        # Partial match for related domains (e.g., NLP and Generative AI)
        # This is a simplified heuristic - could be enhanced with domain similarity
        return 0.3
    
    def _score_complexity_match(self, user_profile: UserProfile, paper: AIResearchPaper) -> float:
        """Score complexity match to user's skill level.
        
        Returns:
            Score from 0.0 to 1.0
        """
        appropriate_complexities = self.COMPLEXITY_SKILL_MAPPING.get(
            user_profile.skill_level,
            [ImplementationComplexity.MEDIUM]
        )
        
        if paper.complexity in appropriate_complexities:
            return 1.0
        
        # Partial score for adjacent complexities
        complexity_order = [
            ImplementationComplexity.LOW,
            ImplementationComplexity.MEDIUM,
            ImplementationComplexity.HIGH,
            ImplementationComplexity.VERY_HIGH
        ]
        
        try:
            paper_idx = complexity_order.index(paper.complexity)
            target_indices = [complexity_order.index(c) for c in appropriate_complexities]
            
            # Distance-based scoring
            min_distance = min(abs(paper_idx - t_idx) for t_idx in target_indices)
            
            if min_distance == 1:
                return 0.6  # Adjacent complexity
            elif min_distance == 2:
                return 0.3  # Two steps away
            else:
                return 0.1  # Too far
        except ValueError:
            return 0.5  # Fallback
    
    def _score_learning_goals(self, user_profile: UserProfile, paper: AIResearchPaper) -> float:
        """Score match with user's learning goal keywords.
        
        Returns:
            Score from 0.0 to 1.0
        """
        if not user_profile.learning_goals:
            return 0.5  # Neutral if no goals
        
        # Collect all keywords from active learning goals
        all_keywords = []
        for goal in user_profile.learning_goals:
            if not goal.completed:
                all_keywords.extend(goal.keywords)
        
        if not all_keywords:
            return 0.5
        
        # Check keyword matches in paper title and abstract
        paper_text = f"{paper.title} {paper.abstract}".lower()
        
        matches = sum(1 for keyword in all_keywords if keyword.lower() in paper_text)
        
        # Normalize score
        match_ratio = matches / len(all_keywords)
        
        return min(1.0, match_ratio * 2)  # Boost partial matches
    
    def explain_recommendation(
        self,
        paper: AIResearchPaper,
        score_breakdown: Dict[str, float]
    ) -> str:
        """Generate human-readable explanation for recommendation.
        
        Args:
            paper: Recommended paper
            score_breakdown: Score breakdown from scoring
            
        Returns:
            Explanation string
        """
        reasons = []
        
        # Find top contributing factors
        sorted_factors = sorted(
            score_breakdown.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for factor, score in sorted_factors[:2]:  # Top 2 factors
            if factor == 'domain_match' and score > 0.3:
                domain_str = paper.primary_domain if isinstance(paper.primary_domain, str) else paper.primary_domain.value
                reasons.append(f"Matches your interest in {domain_str}")
            elif factor == 'complexity_match' and score > 0.2:
                complexity_str = paper.complexity if isinstance(paper.complexity, str) else paper.complexity.value
                reasons.append(f"Appropriate difficulty ({complexity_str})")
            elif factor == 'trend_score' and score > 0.15:
                reasons.append("Trending topic")
            elif factor == 'goal_keywords' and score > 0.05:
                reasons.append("Aligns with your learning goals")
        
        if not reasons:
            reasons.append("General recommendation")
        
        return " • ".join(reasons)


class LearningPathOptimizer:
    """Learning path optimizer (placeholder for future implementation)."""
    
    def __init__(self):
        """Initialize the learning path optimizer."""
        self.logger = get_logger("LearningPathOptimizer")
    
    def suggest_next_steps(
        self,
        user_profile: UserProfile,
        completed_papers: List[AIResearchPaper]
    ) -> List[str]:
        """Suggest next steps based on completed papers.
        
        Args:
            user_profile: User profile
            completed_papers: Papers user has completed
            
        Returns:
            List of suggestion strings
        """
        # Placeholder implementation
        suggestions = []
        
        if not completed_papers:
            suggestions.append("Start with foundational papers in your preferred domains")
        else:
            suggestions.append(f"You've completed {len(completed_papers)} papers - great progress!")
            suggestions.append("Consider exploring related domains to broaden your knowledge")
        
        return suggestions
