"""Intelligence engines for AI Research analysis."""

from typing import Optional
from pydantic import BaseModel, Field

from src.models.ai_research_model import AIResearchPaper, ImplementationComplexity
from src.intelligence.llm_client import get_llm_client, LLMClient
import logging

logger = logging.getLogger(__name__)

# Pydantic models for structured LLM extraction
class PaperAnalysis(BaseModel):
    trend_score: float = Field(description="Relevance score 0.0 to 1.0 based on latest AI trends")
    complexity: ImplementationComplexity = Field(description="Estimated implementation complexity")
    key_innovations: list[str] = Field(description="List of 3-5 key technical innovations")
    summary: str = Field(description="Concise technical summary for a developer")
    reasoning: str = Field(description="Brief reasoning for the trend score")


class AITrendDetector:
    """Detects trends in AI research using Hybrid (Heuristic + LLM) approach."""
    
    def __init__(self):
        self.llm_client: LLMClient = get_llm_client()

    def analyze_trend(self, paper: AIResearchPaper) -> float:
        """Calculate trend score (0.0-1.0 scale).
        
        Hybrid Logic:
        1. Base heuristic score (keyword match).
        2. If heuristic > 0.4 (potentially interesting), use LLM for deep analysis.
        3. Else, return heuristic score (save cost).
        """
        # 1. Heuristic Check
        heuristic_score = self._heuristic_score(paper)
        
        # 2. Threshold Check (Optimize costs)
        # Only use LLM for potentially relevant papers
        if heuristic_score < 0.3:
            return heuristic_score
            
        # 3. LLM Analysis
        try:
            analysis = self._get_llm_analysis(paper)
            if analysis:
                # Weighted average: 70% LLM, 30% Heuristic
                return (analysis.trend_score * 0.7) + (heuristic_score * 0.3)
        except Exception as e:
            logger.warning(f"LLM analysis failed for {paper.title}: {e}")
            
        return heuristic_score

    def _heuristic_score(self, paper: AIResearchPaper) -> float:
        """Original heuristic logic."""
        score = 0.5
        title_lower = paper.title.lower()
        hot_keywords = ["transformer", "diffusion", "llm", "generative", "foundation model", "agent", "rag", "reasoning"]
        
        for kw in hot_keywords:
            if kw in title_lower:
                score += 0.1
        return min(1.0, score)

    def _get_llm_analysis(self, paper: AIResearchPaper) -> Optional[PaperAnalysis]:
        """Call LLM to analyze paper."""
        prompt = (
            "Analyze this AI research paper. "
            "Determine its relevance to current bleeding-edge AI trends (Agents, multimodal, reasoning, efficiency). "
            "Score 0.0 (irrelevant/dated) to 1.0 (breakthrough/must-read). "
            "Estimate implementation complexity for a single engineer."
        )
        content = f"Title: {paper.title}\nAbstract: {paper.summary}\nDomain: {paper.primary_domain}"
        
        return self.llm_client.extract_structured_data(content, PaperAnalysis, prompt)


class ImplementationComplexityScorer:
    """Scores implementation complexity."""

    def score_complexity(self, paper: AIResearchPaper) -> ImplementationComplexity:
        """Calculate complexity level."""
        # Check if code is available (Strongest signal)
        if paper.code_url:
            return ImplementationComplexity.LOW
            
        # Fallback to simple heuristic if LLM analysis wasn't cached/done
        # (In a real scenario, we'd reuse the LLM result from TrendDetector if available)
        
        # Simple heuristic
        if "theory" in paper.primary_domain.lower() or "math" in paper.primary_domain.lower():
            return ImplementationComplexity.VERY_HIGH
            
        return ImplementationComplexity.HIGH


class ResearchOpportunityAnalyzer:
    """Identifies implementation opportunities."""

    def identify_opportunities(self, paper: AIResearchPaper) -> list[str]:
        """Identify potential opportunities."""
        opportunities = []

        if paper.complexity == ImplementationComplexity.LOW and paper.trend_score > 0.7:
            opportunities.append("Quick Implementation Candidate")

        if not paper.code_url and paper.trend_score > 0.8:
            opportunities.append("High-Value Open Source Implementation Gap")
            
        return opportunities
