"""Intelligence engines for AI Research analysis."""

from src.models.ai_research_model import AIResearchPaper, ImplementationComplexity


class AITrendDetector:
    """Detects trends in AI research."""

    def analyze_trend(self, paper: AIResearchPaper) -> float:
        """Calculate trend score (0.0-1.0 scale).

        Simple heuristic for now:
        - Recent publication date
        - Keywords in title (e.g., "Transformer", "Diffusion", "LLM")
        """
        score = 0.5  # Base score
        title_lower = paper.title.lower()

        hot_keywords = [
            "transformer",
            "diffusion",
            "llm",
            "generative",
            "foundation model",
            "agent",
        ]
        for kw in hot_keywords:
            if kw in title_lower:
                score += 0.1

        return min(1.0, score)


class ImplementationComplexityScorer:
    """Scores implementation complexity."""

    def score_complexity(self, paper: AIResearchPaper) -> ImplementationComplexity:
        """Calculate complexity level.

        Heuristic:
        - Code available -> Lower complexity
        - "Theory" domain -> Higher complexity
        """
        score = 50.0

        if paper.code_url:
            score -= 20.0  # Easier if code exists

        if "theory" in paper.primary_domain.lower():
            score += 20.0

        # Map score to enum
        if score < 30:
            return ImplementationComplexity.LOW
        elif score < 60:
            return ImplementationComplexity.MEDIUM
        elif score < 80:
            return ImplementationComplexity.HIGH
        else:
            return ImplementationComplexity.VERY_HIGH


class ResearchOpportunityAnalyzer:
    """Identifies implementation opportunities."""

    def identify_opportunities(self, paper: AIResearchPaper) -> list[str]:
        """Identify potential opportunities."""
        opportunities = []

        if paper.complexity == ImplementationComplexity.LOW and paper.trend_score > 70:
            opportunities.append("Quick Implementation Candidate")

        if not paper.code_url:
            opportunities.append("Open Source Implementation Gap")

        return opportunities
