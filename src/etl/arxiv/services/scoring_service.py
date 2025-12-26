"""Scoring services for ArXiv paper intelligence analysis."""

import logging
from typing import Any

from src.models.arxiv import CommercialPotential, ResearchCategory, TechnologyReadinessLevel

logger = logging.getLogger(__name__)


class ScoringService:
    """Service for calculating various intelligence scores for research papers."""

    def __init__(self, debug: bool = False):
        """Initialize scoring service.

        Args:
            debug: Enable debug logging
        """
        self.debug = debug

        # Industry impact keywords with weights
        self.impact_keywords = {
            "breakthrough": 3.0,
            "novel": 2.5,
            "unprecedented": 3.0,
            "revolutionary": 3.0,
            "game-changing": 3.0,
            "paradigm shift": 3.0,
            "significant improvement": 2.5,
            "state-of-the-art": 2.5,
            "best performance": 2.0,
            "superior performance": 2.0,
            "outperforms": 2.0,
            "substantial improvement": 2.5,
            "real-world": 2.5,
            "production": 2.5,
            "enterprise": 2.0,
            "practical": 2.0,
            "scalable": 2.0,
            "deployment": 2.0,
            "implementation": 1.5,
            "commercial": 2.5,
            "industry": 2.0,
            "robust": 1.5,
            "efficient": 1.5,
            "optimized": 1.5,
            "reliable": 1.5,
            "stable": 1.5,
            "fast": 1.5,
            "lightweight": 1.5,
            "high-performance": 2.0,
            "comprehensive": 1.5,
            "extensive": 1.5,
            "thorough": 1.5,
            "empirical": 1.0,
            "experimental": 1.0,
            "evaluation": 1.0,
            "benchmark": 2.0,
            "dataset": 1.5,
            "open source": 2.0,
        }

        # Technology readiness indicators
        self.trl_indicators = {
            TechnologyReadinessLevel.TRL_1: ["basic research", "theoretical", "fundamental", "principle"],
            TechnologyReadinessLevel.TRL_2: ["concept", "formulated", "hypothesis", "proposed"],
            TechnologyReadinessLevel.TRL_3: ["proof of concept", "experimental", "prototype", "preliminary"],
            TechnologyReadinessLevel.TRL_4: ["validation", "laboratory", "controlled", "tested"],
            TechnologyReadinessLevel.TRL_5: ["relevant environment", "simulation", "realistic", "validated"],
            TechnologyReadinessLevel.TRL_6: ["demonstration", "pilot", "beta", "field test"],
            TechnologyReadinessLevel.TRL_7: ["system prototype", "pre-commercial", "alpha"],
            TechnologyReadinessLevel.TRL_8: ["complete system", "production ready", "commercial"],
            TechnologyReadinessLevel.TRL_9: ["proven system", "deployed", "operational", "production"],
        }

        # Commercial potential indicators
        self.commercial_indicators = {
            CommercialPotential.HIGH: [
                "commercial", "industry", "enterprise", "production", "deployment",
                "market", "business", "revenue", "startup", "venture", "patent",
                "licensing", "product", "customer", "user", "adoption",
            ],
            CommercialPotential.MEDIUM: [
                "application", "practical", "real-world", "implementation",
                "prototype", "demonstration", "pilot", "feasibility",
            ],
            CommercialPotential.LOW: [
                "experimental", "preliminary", "exploratory", "investigation",
            ],
            CommercialPotential.RESEARCH: [
                "theoretical", "fundamental", "basic research", "academic",
                "mathematical", "analytical", "formal", "abstract",
            ],
        }

        # Research category indicators
        self.research_category_indicators = {
            ResearchCategory.MACHINE_LEARNING: ["machine learning", "neural network", "deep learning", "model training"],
            ResearchCategory.COMPUTER_VISION: ["computer vision", "image processing", "object detection", "visual recognition"],
            ResearchCategory.NATURAL_LANGUAGE: ["nlp", "natural language", "text analysis", "language model"],
            ResearchCategory.ROBOTICS: ["robot", "robotics", "autonomous", "manipulation", "navigation"],
            ResearchCategory.DATABASE_SYSTEMS: ["database", "query processing", "data management", "storage"],
            ResearchCategory.SOFTWARE_ENGINEERING: ["software engineering", "testing", "verification", "maintenance"],
            ResearchCategory.NETWORKING: ["network", "protocol", "distributed system", "communication"],
            ResearchCategory.SECURITY: ["security", "privacy", "encryption", "authentication", "cryptographic"],
            ResearchCategory.THEORETICAL_CS: ["algorithm", "complexity", "computational", "theoretical", "optimization"],
        }

    def calculate_industry_impact(self, paper_data: dict[str, Any]) -> float:
        """Calculate potential industry impact using advanced NLP analysis.

        Args:
            paper_data: Paper metadata dictionary

        Returns:
            Industry impact score (0-10)
        """
        title = paper_data.get("title", "").lower()
        summary = paper_data.get("summary", "").lower()
        text = f"{title} {summary}"

        impact_score = 0.0

        # Keyword-based scoring
        for keyword, weight in self.impact_keywords.items():
            if keyword in text:
                impact_score += weight

        # Category-based scoring
        categories = paper_data.get("categories", [])
        high_impact_categories = ["cs.AI", "cs.LG", "cs.SE", "cs.CR", "cs.DB"]
        for cat in categories:
            if cat in high_impact_categories:
                impact_score += 1.5

        # Relevance score boost
        relevance_score = paper_data.get("relevance_score", 0)
        impact_score += relevance_score * 0.3

        # GitHub integration boost
        found_keywords = paper_data.get("found_keywords", [])
        if found_keywords and any("github" in kw.lower() for kw in found_keywords):
            impact_score += 1.0

        # Normalize to 0-10 scale
        normalized_score = min(impact_score / 3.0, 10.0)
        return round(normalized_score, 2)

    def assess_technology_readiness(self, paper_data: dict[str, Any]) -> TechnologyReadinessLevel | None:
        """Assess technology readiness level based on content analysis.

        Args:
            paper_data: Paper metadata dictionary

        Returns:
            TRL level or None if undetermined
        """
        title = paper_data.get("title", "").lower()
        summary = paper_data.get("summary", "").lower()
        text = f"{title} {summary}"

        # Score each TRL level based on indicator presence
        trl_scores = {}
        for trl_level, indicators in self.trl_indicators.items():
            score = sum(1 for indicator in indicators if indicator in text)
            trl_scores[trl_level] = score

        if not trl_scores or max(trl_scores.values()) == 0:
            return None

        best_trl = max(trl_scores.items(), key=lambda x: x[1])[0]
        return best_trl

    def assess_commercial_potential(self, paper_data: dict[str, Any]) -> CommercialPotential:
        """Assess commercial viability potential.

        Args:
            paper_data: Paper metadata dictionary

        Returns:
            Commercial potential level
        """
        title = paper_data.get("title", "").lower()
        summary = paper_data.get("summary", "").lower()
        text = f"{title} {summary}"

        # Score each commercial potential level
        potential_scores = {}
        for potential, indicators in self.commercial_indicators.items():
            score = sum(1 for indicator in indicators if indicator in text)
            potential_scores[potential] = score

        # Adjust based on categories
        categories = paper_data.get("categories", [])
        applied_categories = ["cs.SE", "cs.DB", "cs.CR", "cs.AR", "cs.NI"]
        if any(cat in applied_categories for cat in categories):
            potential_scores[CommercialPotential.HIGH] += 1
            potential_scores[CommercialPotential.MEDIUM] += 1

        if not potential_scores or max(potential_scores.values()) == 0:
            return CommercialPotential.RESEARCH

        best_potential = max(potential_scores.items(), key=lambda x: x[1])[0]
        return best_potential

    def calculate_innovation_score(self, paper_data: dict[str, Any]) -> float:
        """Calculate innovation score based on novelty indicators.

        Args:
            paper_data: Paper metadata dictionary

        Returns:
            Innovation score (0-10)
        """
        title = paper_data.get("title", "").lower()
        summary = paper_data.get("summary", "").lower()
        text = f"{title} {summary}"

        innovation_keywords = {
            "novel": 2.0,
            "new": 1.0,
            "first": 1.5,
            "unique": 2.0,
            "innovative": 2.0,
            "original": 1.5,
            "groundbreaking": 3.0,
            "unprecedented": 3.0,
            "state-of-the-art": 2.0,
            "cutting-edge": 2.5,
            "advance": 1.0,
            "extension": 0.5,
            "improvement": 1.0,
        }

        score = 0.0
        for keyword, weight in innovation_keywords.items():
            if keyword in text:
                score += weight

        # Normalize to 0-10
        normalized = min(score / 2.0, 10.0)
        return round(normalized, 2)

    def predict_citation_potential(self, paper_data: dict[str, Any]) -> float:
        """Predict citation potential based on various factors.

        Args:
            paper_data: Paper metadata dictionary

        Returns:
            Citation potential score (0-10)
        """
        score = 0.0

        # Author count (more authors = potentially more citations)
        authors = paper_data.get("authors", [])
        if authors:
            score += min(len(authors) * 0.3, 2.0)

        # Paper length (longer papers often get more citations)
        summary = paper_data.get("summary", "")
        if summary:
            word_count = len(summary.split())
            score += min(word_count / 100, 1.5)

        # Category impact
        categories = paper_data.get("categories", [])
        high_citation_categories = ["cs.AI", "cs.LG", "cs.CV", "cs.CL"]
        for cat in categories:
            if cat in high_citation_categories:
                score += 1.0

        # Practical applicability
        text = f"{paper_data.get('title', '').lower()} {summary.lower()}"
        practical_keywords = ["dataset", "code", "implementation", "available", "open source"]
        score += sum(0.5 for keyword in practical_keywords if keyword in text)

        # Normalize to 0-10
        normalized = min(score, 10.0)
        return round(normalized, 2)

    def assess_reproducibility(self, paper_data: dict[str, Any]) -> float:
        """Assess reproducibility of research.

        Args:
            paper_data: Paper metadata dictionary

        Returns:
            Reproducibility score (0-10)
        """
        title = paper_data.get("title", "").lower()
        summary = paper_data.get("summary", "").lower()
        text = f"{title} {summary}"

        reproducibility_indicators = {
            "code": 2.0,
            "data": 1.5,
            "available": 1.0,
            "github": 2.0,
            "open source": 2.0,
            "dataset": 1.5,
            "implementation": 1.0,
            "benchmark": 1.0,
            "experimental": 0.5,
            "evaluation": 0.5,
        }

        score = sum(weight for keyword, weight in reproducibility_indicators.items() if keyword in text)

        # Check for structured approach
        if any(word in text for word in ["methodology", "framework", "systematic"]):
            score += 1.0

        # Normalize to 0-10
        normalized = min(score, 10.0)
        return round(normalized, 2)
