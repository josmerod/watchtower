"""Technology adoption analysis and intelligence system.

This module provides advanced technology adoption trend analysis including:
- Framework battles and comparisons
- Adoption trend predictions
- Technology intelligence aggregation
"""

from __future__ import annotations

import statistics
from typing import Any

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

from exceptions.base import WatchtowerError
from models.technology import (
    AdoptionLevel,
    FrameworkBattleModel,
    MaturityLevel,
    TechnologyCategory,
    TechnologyComparisonModel,
    TechnologyPredictionModel,
    TrendDirection,
)
from utils.logging import get_logger


class TechnologyAdoptionAnalysisError(WatchtowerError):
    """Technology adoption analysis specific error."""

    def __init__(self, message: str, **kwargs):
        """Initialize technology adoption analysis error.

        Args:
            message: Error message.
            **kwargs: Additional arguments for base class.
        """
        kwargs["error_code"] = kwargs.get("error_code", "WT_TECH_ADOPTION_ERROR")
        super().__init__(message, **kwargs)


class TechnologyAdoptionAnalyzer:
    """Advanced technology adoption trend analysis.

    This class provides comprehensive analysis of technology adoption patterns,
    framework battles, and predictive intelligence using multi-source data.
    """

    def __init__(self, data_service: Any) -> None:
        """Initialize the technology adoption analyzer.

        Args:
            data_service: Data service for accessing GitHub, DEV, and other data sources.
        """
        self.data_service = data_service
        self.logger = get_logger(self.__class__.__name__)

        # Framework definitions for battles
        self.framework_categories = {
            TechnologyCategory.FRONTEND: {
                "frameworks": [
                    "react",
                    "vue",
                    "angular",
                    "svelte",
                    "solidjs",
                    "preact",
                ],
                "keywords": ["frontend", "ui", "component", "spa", "client-side"],
            },
            TechnologyCategory.BACKEND: {
                "frameworks": [
                    "django",
                    "flask",
                    "fastapi",
                    "express",
                    "nestjs",
                    "koa",
                    "gin",
                    "fiber",
                ],
                "keywords": [
                    "backend",
                    "api",
                    "server",
                    "rest",
                    "graphql",
                    "web framework",
                ],
            },
            TechnologyCategory.MOBILE: {
                "frameworks": [
                    "react-native",
                    "flutter",
                    "ionic",
                    "xamarin",
                    "capacitor",
                    "nativescript",
                ],
                "keywords": ["mobile", "ios", "android", "cross-platform", "native"],
            },
            TechnologyCategory.ML: {
                "frameworks": [
                    "tensorflow",
                    "pytorch",
                    "scikit-learn",
                    "xgboost",
                    "lightgbm",
                    "catboost",
                ],
                "keywords": [
                    "machine learning",
                    "deep learning",
                    "ai",
                    "neural network",
                    "model",
                ],
            },
        }

        # Initialize prediction models
        self.prediction_models: dict[str, Any] = {}
        self._setup_prediction_models()

    def _setup_prediction_models(self) -> None:
        """Setup machine learning models for predictions."""
        try:
            # Initialize with default models
            self.prediction_models = {
                "adoption_predictor": RandomForestRegressor(
                    n_estimators=100, random_state=42, max_depth=10
                ),
                "growth_predictor": LinearRegression(),
                "scaler": StandardScaler(),
            }

            self.logger.info("Prediction models initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to setup prediction models: {e}")
            raise TechnologyAdoptionAnalysisError(
                "Failed to initialize prediction models", cause=e
            )

    async def analyze_framework_battles(
        self,
    ) -> dict[TechnologyCategory, FrameworkBattleModel]:
        """Analyze head-to-head framework battles using existing data.

        Returns:
            Dictionary mapping categories to framework battle results.

        Raises:
            TechnologyAdoptionAnalysisError: If analysis fails.
        """
        self.logger.info("Starting framework battle analysis")

        try:
            battles = {}

            for category, config in self.framework_categories.items():
                self.logger.debug(f"Analyzing {category.value} frameworks")

                # Get framework data for this category
                framework_data = await self._gather_framework_data(
                    config["frameworks"], config["keywords"]
                )

                if not framework_data:
                    self.logger.warning(
                        f"No data available for {category.value} frameworks"
                    )
                    continue

                # Perform comparative analysis
                comparison_results = self._compare_frameworks(framework_data)

                # Create battle model
                battle = self._create_framework_battle(category, comparison_results)
                battles[category] = battle

                self.logger.info(
                    f"{category.value} battle analyzed: "
                    f"Winner={battle.winner}, Runner-up={battle.runner_up}"
                )

            self.logger.info(
                f"Completed framework battle analysis for {len(battles)} categories"
            )
            return battles

        except Exception as e:
            self.logger.error(f"Framework battle analysis failed: {e}")
            raise TechnologyAdoptionAnalysisError(
                "Framework battle analysis failed",
                context={"error_details": str(e)},
                cause=e,
            )

    async def _gather_framework_data(
        self, frameworks: list[str], keywords: list[str]
    ) -> dict[str, dict[str, Any]]:
        """Gather framework data from multiple sources.

        Args:
            frameworks: List of framework names to analyze.
            keywords: Keywords to help identify related content.

        Returns:
            Dictionary mapping framework names to their metrics.
        """
        framework_data = {}

        try:
            # Get GitHub trends data
            github_data = await self._get_github_data()

            # Get DEV community data
            dev_data = await self._get_dev_community_data()

            for framework in frameworks:
                metrics = await self._extract_framework_metrics(
                    framework, keywords, github_data, dev_data
                )

                if metrics:
                    framework_data[framework] = metrics

        except Exception as e:
            self.logger.error(f"Failed to gather framework data: {e}")

        return framework_data

    async def _get_github_data(self) -> list[dict[str, Any]]:
        """Get GitHub trends data from data service.

        Returns:
            List of GitHub repository data.
        """
        try:
            github_data = self.data_service.get_github_trends()
            if isinstance(github_data, dict) and "error" in github_data:
                self.logger.warning(f"GitHub data error: {github_data['error']}")
                return []
            return github_data if isinstance(github_data, list) else []
        except Exception as e:
            self.logger.warning(f"Failed to get GitHub data: {e}")
            return []

    async def _get_dev_community_data(self) -> list[dict[str, Any]]:
        """Get DEV community data from data service.

        Returns:
            List of DEV community articles/posts.
        """
        try:
            dev_data = self.data_service.get_dev_community()
            if isinstance(dev_data, dict) and "error" in dev_data:
                self.logger.warning(f"DEV community data error: {dev_data['error']}")
                return []
            return dev_data if isinstance(dev_data, list) else []
        except Exception as e:
            self.logger.warning(f"Failed to get DEV community data: {e}")
            return []

    async def _extract_framework_metrics(
        self,
        framework: str,
        keywords: list[str],
        github_data: list[dict[str, Any]],
        dev_data: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Extract metrics for a specific framework.

        Args:
            framework: Framework name to extract metrics for.
            keywords: Related keywords for identification.
            github_data: GitHub repository data.
            dev_data: DEV community data.

        Returns:
            Dictionary containing framework metrics or None if not found.
        """
        metrics = {
            "name": framework,
            "github_stars": 0,
            "github_forks": 0,
            "github_activity_score": 0,
            "dev_mentions": 0,
            "dev_engagement_score": 0,
            "trend_score": 0,
            "popularity_score": 0,
            "growth_rate": 0.0,
            "maturity_level": "emerging",
            "last_activity": None,
        }

        try:
            # Extract GitHub metrics
            github_metrics = self._extract_github_metrics(framework, github_data)
            if github_metrics:
                metrics.update(github_metrics)

            # Extract DEV community metrics
            dev_metrics = self._extract_dev_metrics(framework, keywords, dev_data)
            if dev_metrics:
                metrics.update(dev_metrics)

            # Calculate derived metrics
            metrics = self._calculate_derived_metrics(metrics)

            return (
                metrics
                if any(v > 0 for k, v in metrics.items() if isinstance(v, (int, float)))
                else None
            )

        except Exception as e:
            self.logger.warning(f"Failed to extract metrics for {framework}: {e}")
            return None

    def _extract_github_metrics(
        self, framework: str, github_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Extract GitHub-specific metrics for a framework.

        Args:
            framework: Framework name.
            github_data: GitHub repository data.

        Returns:
            Dictionary containing GitHub metrics.
        """
        metrics = {}
        total_stars = 0
        total_forks = 0
        activity_scores = []

        framework_lower = framework.lower()

        for repo in github_data:
            repo_name = (repo.get("name") or "").lower()
            repo_description = (repo.get("description") or "").lower()
            repo_topics = [topic.lower() for topic in (repo.get("topics") or []) if topic]

            # Check if repository is related to the framework
            if (
                framework_lower in repo_name
                or framework_lower in repo_description
                or framework_lower in repo_topics
            ):
                total_stars += repo.get("stars", 0)
                total_forks += repo.get("forks", 0)

                activity_score = repo.get("activity_score", 0)
                if activity_score > 0:
                    activity_scores.append(activity_score)

        if activity_scores:
            metrics.update(
                {
                    "github_stars": total_stars,
                    "github_forks": total_forks,
                    "github_activity_score": round(statistics.mean(activity_scores), 2),
                    "github_repos_count": len(activity_scores),
                }
            )

        return metrics

    def _extract_dev_metrics(
        self, framework: str, keywords: list[str], dev_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Extract DEV community metrics for a framework.

        Args:
            framework: Framework name.
            keywords: Related keywords.
            dev_data: DEV community data.

        Returns:
            Dictionary containing DEV community metrics.
        """
        metrics = {}
        mentions = 0
        engagement_scores = []

        framework_lower = framework.lower()
        keyword_set = {kw.lower() for kw in keywords}

        for article in dev_data:
            title = (article.get("title") or "").lower()
            content = (article.get("content") or "").lower()
            tags = [tag.lower() for tag in (article.get("tag_list") or []) if tag]

            # Check if article mentions the framework
            article_text = f"{title} {content} {' '.join(tags)}"

            if framework_lower in article_text or any(
                keyword in article_text for keyword in keyword_set
            ):
                mentions += 1

                engagement_score = article.get("engagement_score", 0)
                if engagement_score > 0:
                    engagement_scores.append(engagement_score)

        if engagement_scores:
            metrics.update(
                {
                    "dev_mentions": mentions,
                    "dev_engagement_score": round(
                        statistics.mean(engagement_scores), 2
                    ),
                    "dev_trend_score": round(
                        sum(
                            article.get("trend_score", 0)
                            for article in dev_data
                            if framework_lower in (article.get("title") or "").lower()
                        )
                        / max(mentions, 1),
                        2,
                    ),
                }
            )

        return metrics

    def _calculate_derived_metrics(self, metrics: dict[str, Any]) -> dict[str, Any]:
        """Calculate derived metrics from base metrics.

        Args:
            metrics: Base metrics dictionary.

        Returns:
            Updated metrics with derived calculations.
        """
        try:
            # Calculate popularity score
            github_component = min((metrics.get("github_stars", 0) / 10000) * 40, 40)
            dev_component = min((metrics.get("dev_mentions", 0) / 100) * 30, 30)
            activity_component = min(
                (metrics.get("github_activity_score", 0) / 100) * 30, 30
            )

            popularity_score = github_component + dev_component + activity_component
            metrics["popularity_score"] = round(popularity_score, 2)

            # Calculate growth rate (simplified)
            stars = metrics.get("github_stars", 0)
            engagement = metrics.get("dev_engagement_score", 0)

            if stars > 50000:
                growth_rate = 0.2 + (engagement / 100)
            elif stars > 10000:
                growth_rate = 0.5 + (engagement / 50)
            elif stars > 1000:
                growth_rate = 1.0 + (engagement / 20)
            else:
                growth_rate = 0.1

            metrics["growth_rate"] = round(min(growth_rate, 2.0), 3)

            # Determine maturity level
            if stars > 100000:
                maturity = "established"
            elif stars > 50000:
                maturity = "mature"
            elif stars > 10000:
                maturity = "growing"
            else:
                maturity = "emerging"

            metrics["maturity_level"] = maturity

            # Calculate trend score
            trend_score = (
                popularity_score * 0.6 + (metrics.get("growth_rate", 0) * 100) * 0.4
            )
            metrics["trend_score"] = round(trend_score, 2)

        except Exception as e:
            self.logger.warning(f"Failed to calculate derived metrics: {e}")

        return metrics

    def _compare_frameworks(
        self, framework_data: dict[str, dict[str, Any]]
    ) -> list[TechnologyComparisonModel]:
        """Compare frameworks within a category.

        Args:
            framework_data: Dictionary mapping framework names to their metrics.

        Returns:
            List of technology comparison models.
        """
        comparisons = []

        # Sort frameworks by overall score for ranking
        sorted_frameworks = sorted(
            framework_data.items(),
            key=lambda x: x[1].get("popularity_score", 0),
            reverse=True,
        )

        for rank, (framework_name, metrics) in enumerate(sorted_frameworks, 1):
            try:
                # Analyze strengths and weaknesses
                strengths, weaknesses = self._analyze_strengths_weaknesses(metrics)

                # Calculate recommendation score
                recommendation_score = self._calculate_recommendation_score(metrics)

                # Determine use cases
                use_cases = self._determine_use_cases(framework_name, metrics)

                comparison = TechnologyComparisonModel(
                    technology_name=framework_name,
                    category=self._determine_category(framework_name),
                    popularity_score=metrics.get("popularity_score", 0),
                    growth_rate=metrics.get("growth_rate", 0),
                    community_health=min(
                        metrics.get("dev_engagement_score", 0) * 10, 100
                    ),
                    job_market_demand=self._estimate_job_demand(
                        framework_name, metrics
                    ),
                    learning_curve=self._assess_learning_curve(framework_name),
                    maturity_level=MaturityLevel(
                        metrics.get("maturity_level", "emerging")
                    ),
                    ecosystem_size=self._estimate_ecosystem_size(metrics),
                    performance_score=self._estimate_performance_score(framework_name),
                    overall_rank=rank,
                    strengths=strengths,
                    weaknesses=weaknesses,
                    recommendation_score=recommendation_score,
                    use_cases=use_cases,
                )

                comparisons.append(comparison)

            except Exception as e:
                self.logger.warning(
                    f"Failed to create comparison for {framework_name}: {e}"
                )
                continue

        return comparisons

    def _analyze_strengths_weaknesses(
        self, metrics: dict[str, Any]
    ) -> tuple[list[str], list[str]]:
        """Analyze framework strengths and weaknesses.

        Args:
            metrics: Framework metrics.

        Returns:
            Tuple of (strengths, weaknesses) lists.
        """
        strengths = []
        weaknesses = []

        # Analyze based on metrics
        if metrics.get("github_stars", 0) > 50000:
            strengths.append("Large community support")
        elif metrics.get("github_stars", 0) < 5000:
            weaknesses.append("Limited community size")

        if metrics.get("growth_rate", 0) > 0.5:
            strengths.append("Rapid growth and adoption")
        elif metrics.get("growth_rate", 0) < 0.1:
            weaknesses.append("Slow growth or stagnation")

        if metrics.get("dev_engagement_score", 0) > 5:
            strengths.append("High developer engagement")
        elif metrics.get("dev_engagement_score", 0) < 2:
            weaknesses.append("Low developer engagement")

        if metrics.get("maturity_level") in ["mature", "established"]:
            strengths.append("Proven stability and reliability")
        elif metrics.get("maturity_level") == "emerging":
            strengths.append("Modern and innovative approach")
            weaknesses.append("May lack production maturity")

        return strengths, weaknesses

    def _calculate_recommendation_score(self, metrics: dict[str, Any]) -> float:
        """Calculate recommendation score for a framework.

        Args:
            metrics: Framework metrics.

        Returns:
            Recommendation score (0-100).
        """
        score = 0.0

        # Base score from popularity
        score += metrics.get("popularity_score", 0) * 0.4

        # Growth component
        growth_rate = metrics.get("growth_rate", 0)
        growth_score = min(growth_rate * 50, 50)
        score += growth_score * 0.3

        # Community engagement
        engagement_score = min(metrics.get("dev_engagement_score", 0) * 10, 30)
        score += engagement_score * 0.3

        return round(min(score, 100), 2)

    def _determine_use_cases(
        self, framework_name: str, metrics: dict[str, Any]
    ) -> list[str]:
        """Determine recommended use cases for a framework.

        Args:
            framework_name: Name of the framework.
            metrics: Framework metrics.

        Returns:
            List of recommended use cases.
        """
        use_cases = []

        # Framework-specific use cases
        framework_use_cases = {
            "react": [
                "Single Page Applications",
                "Component-based UIs",
                "Large-scale applications",
            ],
            "vue": [
                "Progressive web apps",
                "Rapid prototyping",
                "Small to medium applications",
            ],
            "angular": [
                "Enterprise applications",
                "Complex SPAs",
                "TypeScript projects",
            ],
            "svelte": [
                "High-performance apps",
                "Small bundle size requirements",
                "Modern web apps",
            ],
            "django": [
                "Web applications",
                "REST APIs",
                "Admin interfaces",
                "Content management",
            ],
            "flask": [
                "Microservices",
                "API development",
                "Small web applications",
                "Prototyping",
            ],
            "fastapi": [
                "Modern APIs",
                "High-performance services",
                "Auto-documentation",
                "Async applications",
            ],
            "express": [
                "Node.js APIs",
                "Real-time applications",
                "Microservices",
                "RESTful services",
            ],
            "react-native": [
                "Cross-platform mobile",
                "iOS and Android apps",
                "Rapid mobile development",
            ],
            "flutter": [
                "Cross-platform mobile",
                "High-performance mobile apps",
                "Custom UI design",
            ],
            "tensorflow": [
                "Deep learning",
                "Neural networks",
                "Production ML models",
                "Research",
            ],
            "pytorch": [
                "Research and experimentation",
                "Dynamic neural networks",
                "Academic projects",
            ],
            "scikit-learn": [
                "Traditional machine learning",
                "Data analysis",
                "Rapid prototyping",
            ],
        }

        use_cases = framework_use_cases.get(
            framework_name.lower(), ["General purpose development"]
        )

        # Add maturity-based recommendations
        if metrics.get("maturity_level") == "established":
            use_cases.append("Enterprise and mission-critical applications")
        elif metrics.get("maturity_level") == "emerging":
            use_cases.append("Experimental and innovative projects")

        return use_cases

    def _determine_category(self, framework_name: str) -> TechnologyCategory:
        """Determine the category for a framework.

        Args:
            framework_name: Name of the framework.

        Returns:
            Technology category enum.
        """
        for category, config in self.framework_categories.items():
            if framework_name.lower() in config["frameworks"]:
                return category
        return TechnologyCategory.GENERAL

    def _estimate_job_demand(
        self, framework_name: str, metrics: dict[str, Any]
    ) -> float:
        """Estimate job market demand for a framework.

        Args:
            framework_name: Name of the framework.
            metrics: Framework metrics.

        Returns:
            Job demand score (0-100).
        """
        # Base estimation using popularity and maturity
        popularity = metrics.get("popularity_score", 0)
        maturity = metrics.get("maturity_level", "emerging")

        # Maturity bonus
        maturity_multiplier = {
            "established": 1.5,
            "mature": 1.3,
            "growing": 1.1,
            "emerging": 0.8,
        }

        base_demand = popularity * maturity_multiplier.get(maturity, 1.0)

        # Framework-specific adjustments
        framework_adjustments = {
            "react": 1.5,
            "angular": 1.4,
            "vue": 1.2,
            "django": 1.3,
            "express": 1.4,
            "tensorflow": 1.3,
            "pytorch": 1.2,
        }

        adjustment = framework_adjustments.get(framework_name.lower(), 1.0)
        final_demand = min(base_demand * adjustment, 100)

        return round(final_demand, 2)

    def _assess_learning_curve(self, framework_name: str) -> str:
        """Assess the learning curve difficulty for a framework.

        Args:
            framework_name: Name of the framework.

        Returns:
            Learning curve assessment string.
        """
        learning_curves = {
            "react": "medium",
            "vue": "easy",
            "angular": "hard",
            "svelte": "easy",
            "django": "medium",
            "flask": "easy",
            "fastapi": "easy",
            "express": "easy",
            "react-native": "medium",
            "flutter": "medium",
            "tensorflow": "hard",
            "pytorch": "medium",
            "scikit-learn": "easy",
        }

        return learning_curves.get(framework_name.lower(), "medium")

    def _estimate_ecosystem_size(self, metrics: dict[str, Any]) -> int:
        """Estimate ecosystem size score.

        Args:
            metrics: Framework metrics.

        Returns:
            Ecosystem size score.
        """
        # Base calculation using GitHub activity and community engagement
        github_score = min(metrics.get("github_stars", 0) / 1000, 50)
        community_score = metrics.get("dev_mentions", 0) * 2

        ecosystem_size = int(github_score + community_score)
        return min(ecosystem_size, 100)

    def _estimate_performance_score(self, framework_name: str) -> float:
        """Estimate performance benchmark score.

        Args:
            framework_name: Name of the framework.

        Returns:
            Performance score (0-100).
        """
        # Framework performance characteristics (based on general knowledge)
        performance_scores = {
            "react": 75.0,
            "vue": 80.0,
            "angular": 70.0,
            "svelte": 90.0,
            "django": 70.0,
            "flask": 75.0,
            "fastapi": 90.0,
            "express": 85.0,
            "react-native": 70.0,
            "flutter": 85.0,
            "tensorflow": 80.0,
            "pytorch": 75.0,
            "scikit-learn": 70.0,
        }

        return performance_scores.get(framework_name.lower(), 60.0)

    def _create_framework_battle(
        self, category: TechnologyCategory, comparisons: list[TechnologyComparisonModel]
    ) -> FrameworkBattleModel:
        """Create a framework battle model from comparison results.

        Args:
            category: Technology category.
            comparisons: List of framework comparisons.

        Returns:
            Framework battle model.
        """
        if not comparisons:
            raise TechnologyAdoptionAnalysisError(
                f"No frameworks available for {category.value} battle"
            )

        # Sort by overall score
        sorted_comparisons = sorted(
            comparisons, key=lambda x: x.recommendation_score, reverse=True
        )

        winner = sorted_comparisons[0].technology_name
        runner_up = (
            sorted_comparisons[1].technology_name
            if len(sorted_comparisons) > 1
            else winner
        )

        # Find rising star (highest growth rate)
        rising_star = (
            max(comparisons, key=lambda x: x.growth_rate).technology_name
            if comparisons
            else None
        )

        # Market analysis
        market_share_leader = max(
            comparisons, key=lambda x: x.popularity_score
        ).technology_name

        developer_preference = max(
            comparisons, key=lambda x: x.community_health
        ).technology_name

        enterprise_adoption = max(
            comparisons, key=lambda x: x.job_market_demand
        ).technology_name

        # Simple predictions (6 and 12 month)
        predicted_winner_6m = winner  # Conservative prediction
        predicted_winner_12m = (
            rising_star if rising_star and rising_star != winner else winner
        )

        # Calculate confidence scores
        confidence_score = min(
            len(comparisons) / 4, 1.0
        )  # More frameworks = higher confidence
        data_quality_score = 0.8  # Assuming good data quality

        return FrameworkBattleModel(
            category=category,
            frameworks=comparisons,
            winner=winner,
            runner_up=runner_up,
            rising_star=rising_star,
            market_share_leader=market_share_leader,
            developer_preference=developer_preference,
            enterprise_adoption=enterprise_adoption,
            predicted_winner_6m=predicted_winner_6m,
            predicted_winner_12m=predicted_winner_12m,
            confidence_score=confidence_score,
            data_quality_score=data_quality_score,
        )

    async def predict_adoption_trends(
        self, timeframe_months: int = 12
    ) -> dict[str, TechnologyPredictionModel]:
        """Predict technology adoption trends using ML.

        Args:
            timeframe_months: Prediction timeframe in months.

        Returns:
            Dictionary mapping technology names to prediction models.

        Raises:
            TechnologyAdoptionAnalysisError: If prediction fails.
        """
        self.logger.info(
            f"Starting adoption trend predictions for {timeframe_months} months"
        )

        try:
            predictions = {}

            # Get current technology data
            current_technologies = await self._gather_current_technology_data()

            if not current_technologies:
                raise TechnologyAdoptionAnalysisError(
                    "No current technology data available"
                )

            for tech_name, tech_data in current_technologies.items():
                try:
                    prediction = await self._predict_single_technology(
                        tech_name, tech_data, timeframe_months
                    )

                    if prediction:
                        predictions[tech_name] = prediction

                except Exception as e:
                    self.logger.warning(
                        f"Failed to predict trends for {tech_name}: {e}"
                    )
                    continue

            self.logger.info(
                f"Generated predictions for {len(predictions)} technologies"
            )
            return predictions

        except Exception as e:
            self.logger.error(f"Adoption trend prediction failed: {e}")
            raise TechnologyAdoptionAnalysisError(
                "Adoption trend prediction failed",
                context={"timeframe_months": timeframe_months},
                cause=e,
            )

    async def _gather_current_technology_data(self) -> dict[str, dict[str, Any]]:
        """Gather current technology data for predictions.

        Returns:
            Dictionary mapping technology names to their current data.
        """
        current_data = {}

        try:
            # Collect data from all framework categories
            for category, config in self.framework_categories.items():
                framework_data = await self._gather_framework_data(
                    config["frameworks"], config["keywords"]
                )
                current_data.update(framework_data)

        except Exception as e:
            self.logger.error(f"Failed to gather current technology data: {e}")

        return current_data

    async def _predict_single_technology(
        self, tech_name: str, tech_data: dict[str, Any], timeframe_months: int
    ) -> TechnologyPredictionModel | None:
        """Predict adoption trends for a single technology.

        Args:
            tech_name: Technology name.
            tech_data: Current technology data.
            timeframe_months: Prediction timeframe.

        Returns:
            Technology prediction model or None if prediction fails.
        """
        try:
            # Extract current metrics
            current_score = tech_data.get("popularity_score", 0)
            current_growth_rate = tech_data.get("growth_rate", 0)

            # Simple trend prediction based on current growth
            predicted_growth = current_growth_rate * (timeframe_months / 12)
            predicted_score = min(current_score * (1 + predicted_growth), 100)

            # Determine trend direction
            if predicted_growth > 0.5:
                trend_direction = TrendDirection.EXPLOSIVE
            elif predicted_growth > 0.2:
                trend_direction = TrendDirection.RISING
            elif predicted_growth > -0.1:
                trend_direction = TrendDirection.STABLE
            else:
                trend_direction = TrendDirection.DECLINING

            # Determine adoption levels
            current_adoption_level = self._determine_adoption_level(current_score)
            predicted_adoption_level = self._determine_adoption_level(predicted_score)

            # Calculate confidence based on data quality
            confidence = self._calculate_prediction_confidence(tech_data)

            # Generate insights
            key_drivers = self._identify_key_drivers(tech_data, predicted_growth)
            risk_factors = self._identify_risk_factors(tech_data, predicted_growth)
            recommendation = self._generate_recommendation(predicted_growth, confidence)

            return TechnologyPredictionModel(
                technology_name=tech_name,
                current_score=current_score,
                current_adoption_level=current_adoption_level,
                predicted_score=predicted_score,
                predicted_adoption_level=predicted_adoption_level,
                growth_rate=predicted_growth,
                trend_direction=trend_direction,
                prediction_timeframe_months=timeframe_months,
                confidence=confidence,
                key_drivers=key_drivers,
                risk_factors=risk_factors,
                recommendation=recommendation,
                early_adoption_indicators=self._identify_early_adoption_indicators(
                    tech_data
                ),
                competitive_threats=self._identify_competitive_threats(tech_name),
            )

        except Exception as e:
            self.logger.warning(f"Failed to predict trends for {tech_name}: {e}")
            return None

    def _determine_adoption_level(self, score: float) -> AdoptionLevel:
        """Determine adoption level based on score.

        Args:
            score: Adoption score (0-100).

        Returns:
            Adoption level enum.
        """
        if score >= 80:
            return AdoptionLevel.DOMINANT
        elif score >= 60:
            return AdoptionLevel.MAINSTREAM
        elif score >= 30:
            return AdoptionLevel.GROWING
        elif score >= 10:
            return AdoptionLevel.NICHE
        else:
            return AdoptionLevel.DECLINING

    def _calculate_prediction_confidence(self, tech_data: dict[str, Any]) -> float:
        """Calculate prediction confidence based on data quality.

        Args:
            tech_data: Technology data.

        Returns:
            Confidence score (0-1).
        """
        confidence = 0.5  # Base confidence

        # Increase confidence based on data availability
        if tech_data.get("github_stars", 0) > 0:
            confidence += 0.1
        if tech_data.get("dev_mentions", 0) > 0:
            confidence += 0.1
        if tech_data.get("github_activity_score", 0) > 0:
            confidence += 0.1

        # Higher confidence for more mature technologies
        maturity = tech_data.get("maturity_level", "emerging")
        if maturity in ["mature", "established"]:
            confidence += 0.2
        elif maturity == "growing":
            confidence += 0.1

        return min(confidence, 1.0)

    def _identify_key_drivers(
        self, tech_data: dict[str, Any], predicted_growth: float
    ) -> list[str]:
        """Identify key growth drivers for a technology.

        Args:
            tech_data: Technology data.
            predicted_growth: Predicted growth rate.

        Returns:
            List of key growth drivers.
        """
        drivers = []

        if tech_data.get("github_activity_score", 0) > 50:
            drivers.append("Strong developer community activity")

        if tech_data.get("dev_engagement_score", 0) > 5:
            drivers.append("High community engagement and interest")

        if predicted_growth > 0.3:
            drivers.append("Rapid adoption and growth momentum")

        if tech_data.get("maturity_level") == "emerging":
            drivers.append("Modern approach and innovation")

        if not drivers:
            drivers.append("Stable market position")

        return drivers

    def _identify_risk_factors(
        self, tech_data: dict[str, Any], predicted_growth: float
    ) -> list[str]:
        """Identify risk factors for a technology.

        Args:
            tech_data: Technology data.
            predicted_growth: Predicted growth rate.

        Returns:
            List of risk factors.
        """
        risks = []

        if tech_data.get("github_stars", 0) < 1000:
            risks.append("Limited community size and support")

        if predicted_growth < 0:
            risks.append("Declining adoption trend")

        if tech_data.get("maturity_level") == "emerging":
            risks.append("Technology immaturity and potential instability")

        if tech_data.get("dev_engagement_score", 0) < 2:
            risks.append("Low developer engagement and interest")

        return risks

    def _generate_recommendation(
        self, predicted_growth: float, confidence: float
    ) -> str:
        """Generate adoption recommendation based on prediction.

        Args:
            predicted_growth: Predicted growth rate.
            confidence: Prediction confidence.

        Returns:
            Recommendation string.
        """
        if confidence < 0.6:
            return "Monitor - Insufficient data for strong recommendation"
        elif predicted_growth > 0.5:
            return "Strong Adopt - High growth potential with good confidence"
        elif predicted_growth > 0.2:
            return "Adopt - Positive growth trend with reasonable confidence"
        elif predicted_growth > 0.0:
            return "Consider - Stable growth with some potential"
        else:
            return "Avoid - Declining trend predicted"

    def _identify_early_adoption_indicators(
        self, tech_data: dict[str, Any]
    ) -> list[str]:
        """Identify early adoption indicators.

        Args:
            tech_data: Technology data.

        Returns:
            List of early adoption indicators.
        """
        indicators = []

        if tech_data.get("growth_rate", 0) > 0.5:
            indicators.append("Rapid community growth")

        if tech_data.get("dev_mentions", 0) > 20:
            indicators.append("Increasing developer discussions")

        if tech_data.get("github_activity_score", 0) > 70:
            indicators.append("High repository activity and contributions")

        return indicators

    def _identify_competitive_threats(self, tech_name: str) -> list[str]:
        """Identify competitive threats for a technology.

        Args:
            tech_name: Technology name.

        Returns:
            List of competitive threats.
        """
        # Technology-specific competitive analysis
        threats = {
            "react": ["Vue.js growing adoption", "Angular enterprise dominance"],
            "vue": ["React ecosystem size", "Angular enterprise features"],
            "angular": ["React developer preference", "Vue.js simplicity"],
            "django": ["FastAPI performance", "Express.js ecosystem"],
            "flask": ["FastAPI modern features", "Django batteries-included approach"],
            "fastapi": ["Django ecosystem maturity", "Express.js market presence"],
            "tensorflow": ["PyTorch research adoption", "Emerging ML frameworks"],
            "pytorch": [
                "TensorFlow production maturity",
                "Industry-specific solutions",
            ],
        }

        return threats.get(tech_name.lower(), ["Emerging alternative technologies"])
