"""Enhanced data service with Technology Adoption Intelligence.

This module extends the existing data service with advanced technology
adoption analysis and intelligence capabilities.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.analytics.technology_adoption import TechnologyAdoptionAnalyzer
from src.models.technology import FrameworkBattleModel, TechnologyCategory, TechnologyPredictionModel
from src.utils.logging import get_logger
from src.web.fullstreamlit.utils.data_service import DataService


class UltraOptimizedDataService(DataService):
    """Ultra-optimized data service with technology intelligence.
    
    This class extends the base DataService with advanced technology
    adoption analysis capabilities while maintaining all existing functionality.
    """
    
    def __init__(self, logger=None):
        """Initialize the enhanced data service.
        
        Args:
            logger: Optional logger instance.
        """
        super().__init__(logger)
        self.logger = logger or get_logger(self.__class__.__name__)
        
        # Initialize technology adoption analyzer
        self.tech_analyzer: Optional[TechnologyAdoptionAnalyzer] = None
        self._initialize_tech_analyzer()
        
        # Cache for technology intelligence data
        self._tech_intelligence_cache: Dict[str, Any] = {}
        self._cache_expiry: Optional[datetime] = None
        self._cache_duration_minutes = 30  # Cache for 30 minutes
    
    def _initialize_tech_analyzer(self) -> None:
        """Initialize the technology adoption analyzer."""
        try:
            self.tech_analyzer = TechnologyAdoptionAnalyzer(self)
            self.logger.info("Technology adoption analyzer initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize technology analyzer: {e}")
            self.tech_analyzer = None
    
    def get_github_trends(self) -> List[Dict[str, Any]]:
        """Get GitHub trends data.
        
        Returns:
            List of GitHub repository data.
        """
        try:
            # Try to get data from parent class method if it exists
            if hasattr(super(), 'get_github_trends_data'):
                df = super().get_github_trends_data()
                if not df.empty:
                    return df.to_dict('records')
            
            # Fallback: try to load from file directly
            github_file = self.data_dir / "github_trends" / "github_trends_latest.json"
            if github_file.exists():
                github_data = self._safe_load_json(github_file, "GitHub trends")
                self.logger.info(f"Loaded {len(github_data)} GitHub repositories")
                return github_data
            else:
                self.logger.warning("GitHub trends file not found")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to get GitHub trends: {e}")
            return []
    
    def get_dev_community(self) -> List[Dict[str, Any]]:
        """Get DEV community data.
        
        Returns:
            List of DEV community articles.
        """
        try:
            # Try to get data from parent class method if it exists
            if hasattr(super(), 'get_dev_community_data'):
                df = super().get_dev_community_data()
                if not df.empty:
                    return df.to_dict('records')
            
            # Fallback: try to load from file directly
            dev_file = self.data_dir / "dev_community" / "dev_community_latest.json"
            if dev_file.exists():
                dev_data = self._safe_load_json(dev_file, "DEV community")
                self.logger.info(f"Loaded {len(dev_data)} DEV community articles")
                return dev_data
            else:
                self.logger.warning("DEV community file not found")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to get DEV community data: {e}")
            return []
    
    def _is_cache_valid(self) -> bool:
        """Check if the technology intelligence cache is still valid.
        
        Returns:
            True if cache is valid, False otherwise.
        """
        if not self._cache_expiry:
            return False
        
        return datetime.utcnow() < self._cache_expiry
    
    def _update_cache_expiry(self) -> None:
        """Update the cache expiry timestamp."""
        from datetime import timedelta
        self._cache_expiry = datetime.utcnow() + timedelta(minutes=self._cache_duration_minutes)
    
    async def get_technology_radar(self) -> Dict[str, Any]:
        """Get comprehensive technology adoption intelligence.
        
        Returns:
            Dictionary containing technology radar data including:
            - Framework battles
            - Adoption predictions  
            - Technology recommendations
            - Market intelligence
            
        Raises:
            Exception: If technology intelligence cannot be generated.
        """
        self.logger.info("Generating technology radar intelligence")
        
        try:
            # Check cache first
            if self._is_cache_valid() and 'technology_radar' in self._tech_intelligence_cache:
                self.logger.debug("Returning cached technology radar data")
                return self._tech_intelligence_cache['technology_radar']
            
            if not self.tech_analyzer:
                self.logger.warning("Technology analyzer not available")
                return {'error': 'Technology analyzer not initialized'}
            
            # Generate framework battles
            framework_battles = await self.tech_analyzer.analyze_framework_battles()
            
            # Generate adoption predictions
            adoption_predictions = await self.tech_analyzer.predict_adoption_trends()
            
            # Generate technology recommendations
            recommendations = self._generate_technology_recommendations(
                framework_battles, adoption_predictions
            )
            
            # Analyze market intelligence
            market_intelligence = self._analyze_market_trends(
                framework_battles, adoption_predictions
            )
            
            # Compile results
            radar_data = {
                'framework_battles': self._serialize_framework_battles(framework_battles),
                'adoption_predictions': self._serialize_predictions(adoption_predictions),
                'recommendation_engine': recommendations,
                'market_intelligence': market_intelligence,
                'last_updated': datetime.utcnow().isoformat(),
                'data_sources': ['github_trends', 'dev_community', 'analytics_engine'],
                'confidence_score': self._calculate_overall_confidence(
                    framework_battles, adoption_predictions
                )
            }
            
            # Cache the results
            self._tech_intelligence_cache['technology_radar'] = radar_data
            self._update_cache_expiry()
            
            self.logger.info(f"Technology radar generated with {len(framework_battles)} battles and {len(adoption_predictions)} predictions")
            return radar_data
            
        except Exception as e:
            self.logger.error(f"Technology radar generation failed: {e}")
            return {
                'error': str(e),
                'message': 'Failed to generate technology radar intelligence',
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _serialize_framework_battles(
        self, 
        battles: Dict[TechnologyCategory, FrameworkBattleModel]
    ) -> Dict[str, Any]:
        """Serialize framework battles for JSON response.
        
        Args:
            battles: Dictionary of framework battles.
            
        Returns:
            Serialized battles data.
        """
        serialized = {}
        
        for category, battle in battles.items():
            try:
                battle_data = {
                    'category': category.value,
                    'winner': battle.winner,
                    'runner_up': battle.runner_up,
                    'rising_star': battle.rising_star,
                    'market_share_leader': battle.market_share_leader,
                    'developer_preference': battle.developer_preference,
                    'enterprise_adoption': battle.enterprise_adoption,
                    'predicted_winner_6m': battle.predicted_winner_6m,
                    'predicted_winner_12m': battle.predicted_winner_12m,
                    'confidence_score': battle.confidence_score,
                    'data_quality_score': battle.data_quality_score,
                    'total_frameworks': battle.total_frameworks,
                    'battle_summary': battle.battle_summary,
                    'frameworks': []
                }
                
                # Serialize framework details
                for framework in battle.frameworks:
                    framework_data = {
                        'name': framework.technology_name,
                        'category': framework.category.value,
                        'popularity_score': framework.popularity_score,
                        'growth_rate': framework.growth_rate,
                        'community_health': framework.community_health,
                        'job_market_demand': framework.job_market_demand,
                        'learning_curve': framework.learning_curve,
                        'maturity_level': framework.maturity_level.value,
                        'ecosystem_size': framework.ecosystem_size,
                        'performance_score': framework.performance_score,
                        'overall_rank': framework.overall_rank,
                        'strengths': framework.strengths,
                        'weaknesses': framework.weaknesses,
                        'recommendation_score': framework.recommendation_score,
                        'use_cases': framework.use_cases
                    }
                    battle_data['frameworks'].append(framework_data)
                
                serialized[category.value] = battle_data
                
            except Exception as e:
                self.logger.warning(f"Failed to serialize battle for {category}: {e}")
                continue
        
        return serialized
    
    def _serialize_predictions(
        self, 
        predictions: Dict[str, TechnologyPredictionModel]
    ) -> Dict[str, Any]:
        """Serialize technology predictions for JSON response.
        
        Args:
            predictions: Dictionary of technology predictions.
            
        Returns:
            Serialized predictions data.
        """
        serialized = {}
        
        for tech_name, prediction in predictions.items():
            try:
                prediction_data = {
                    'technology_name': prediction.technology_name,
                    'current_score': prediction.current_score,
                    'current_adoption_level': prediction.current_adoption_level.value,
                    'predicted_score': prediction.predicted_score,
                    'predicted_adoption_level': prediction.predicted_adoption_level.value,
                    'growth_rate': prediction.growth_rate,
                    'trend_direction': prediction.trend_direction.value,
                    'prediction_timeframe_months': prediction.prediction_timeframe_months,
                    'confidence': prediction.confidence,
                    'expected_growth_percentage': prediction.expected_growth_percentage,
                    'investment_recommendation': prediction.investment_recommendation,
                    'key_drivers': prediction.key_drivers,
                    'risk_factors': prediction.risk_factors,
                    'recommendation': prediction.recommendation,
                    'early_adoption_indicators': prediction.early_adoption_indicators,
                    'competitive_threats': prediction.competitive_threats
                }
                
                serialized[tech_name] = prediction_data
                
            except Exception as e:
                self.logger.warning(f"Failed to serialize prediction for {tech_name}: {e}")
                continue
        
        return serialized
    
    def _generate_technology_recommendations(
        self,
        battles: Dict[TechnologyCategory, FrameworkBattleModel],
        predictions: Dict[str, TechnologyPredictionModel]
    ) -> Dict[str, Any]:
        """Generate technology recommendations based on battles and predictions.
        
        Args:
            battles: Framework battle results.
            predictions: Technology predictions.
            
        Returns:
            Technology recommendations.
        """
        try:
            recommendations = {
                'top_recommendations': [],
                'category_winners': {},
                'rising_technologies': [],
                'avoid_technologies': [],
                'investment_grades': {
                    'strong_buy': [],
                    'buy': [],
                    'hold': [],
                    'avoid': []
                }
            }
            
            # Extract category winners
            for category, battle in battles.items():
                recommendations['category_winners'][category.value] = {
                    'winner': battle.winner,
                    'recommendation_reason': f"Leading {category.value} framework with highest overall score"
                }
            
            # Analyze predictions for investment recommendations
            for tech_name, prediction in predictions.items():
                investment_rec = prediction.investment_recommendation.lower()
                
                if 'strong buy' in investment_rec:
                    recommendations['investment_grades']['strong_buy'].append({
                        'technology': tech_name,
                        'reason': prediction.recommendation,
                        'growth_potential': f"{prediction.expected_growth_percentage}%"
                    })
                elif 'buy' in investment_rec:
                    recommendations['investment_grades']['buy'].append({
                        'technology': tech_name,
                        'reason': prediction.recommendation,
                        'growth_potential': f"{prediction.expected_growth_percentage}%"
                    })
                elif 'hold' in investment_rec:
                    recommendations['investment_grades']['hold'].append({
                        'technology': tech_name,
                        'reason': prediction.recommendation
                    })
                elif 'avoid' in investment_rec or 'sell' in investment_rec:
                    recommendations['investment_grades']['avoid'].append({
                        'technology': tech_name,
                        'reason': prediction.recommendation
                    })
                
                # Identify rising technologies
                if prediction.trend_direction.value in ['rising', 'explosive'] and prediction.confidence > 0.7:
                    recommendations['rising_technologies'].append({
                        'technology': tech_name,
                        'trend': prediction.trend_direction.value,
                        'confidence': prediction.confidence,
                        'key_drivers': prediction.key_drivers
                    })
                
                # Identify technologies to avoid
                if prediction.trend_direction.value == 'declining' and prediction.confidence > 0.6:
                    recommendations['avoid_technologies'].append({
                        'technology': tech_name,
                        'reason': 'Declining adoption trend predicted',
                        'risk_factors': prediction.risk_factors
                    })
            
            # Generate top recommendations (highest scoring across all categories)
            all_strong_buys = recommendations['investment_grades']['strong_buy']
            all_buys = recommendations['investment_grades']['buy']
            
            top_recommendations = (all_strong_buys + all_buys)[:5]  # Top 5
            recommendations['top_recommendations'] = top_recommendations
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to generate recommendations: {e}")
            return {'error': 'Failed to generate recommendations'}
    
    def _analyze_market_trends(
        self,
        battles: Dict[TechnologyCategory, FrameworkBattleModel],
        predictions: Dict[str, TechnologyPredictionModel]
    ) -> Dict[str, Any]:
        """Analyze market trends from battle and prediction data.
        
        Args:
            battles: Framework battle results.
            predictions: Technology predictions.
            
        Returns:
            Market intelligence analysis.
        """
        try:
            market_analysis = {
                'overall_trends': [],
                'category_insights': {},
                'adoption_lifecycle': {
                    'emerging': [],
                    'growing': [],
                    'mainstream': [],
                    'mature': []
                },
                'market_shifts': [],
                'competitive_landscape': {}
            }
            
            # Analyze overall market trends
            growth_technologies = [
                name for name, pred in predictions.items() 
                if pred.growth_rate > 0.2
            ]
            
            if len(growth_technologies) > len(predictions) * 0.6:
                market_analysis['overall_trends'].append(
                    "Market shows strong innovation and growth across multiple technologies"
                )
            
            declining_count = len([
                name for name, pred in predictions.items() 
                if pred.trend_direction.value == 'declining'
            ])
            
            if declining_count > 0:
                market_analysis['overall_trends'].append(
                    f"{declining_count} technologies showing declining trends - market consolidation occurring"
                )
            
            # Category insights
            for category, battle in battles.items():
                rising_star = battle.rising_star
                winner = battle.winner
                
                insight = f"In {category.value}: {winner} dominates"
                if rising_star and rising_star != winner:
                    insight += f", but {rising_star} is the rising challenger"
                
                market_analysis['category_insights'][category.value] = {
                    'insight': insight,
                    'market_leader': winner,
                    'challenger': rising_star,
                    'confidence': battle.confidence_score
                }
            
            # Adoption lifecycle analysis
            for tech_name, prediction in predictions.items():
                lifecycle_stage = prediction.current_adoption_level.value
                if lifecycle_stage in market_analysis['adoption_lifecycle']:
                    market_analysis['adoption_lifecycle'][lifecycle_stage].append({
                        'technology': tech_name,
                        'score': prediction.current_score,
                        'trend': prediction.trend_direction.value
                    })
            
            # Identify market shifts
            explosive_growth = [
                name for name, pred in predictions.items()
                if pred.trend_direction.value == 'explosive'
            ]
            
            if explosive_growth:
                market_analysis['market_shifts'].append({
                    'type': 'explosive_growth',
                    'technologies': explosive_growth,
                    'description': 'Technologies experiencing explosive growth and rapid adoption'
                })
            
            return market_analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze market trends: {e}")
            return {'error': 'Failed to analyze market trends'}
    
    def _calculate_overall_confidence(
        self,
        battles: Dict[TechnologyCategory, FrameworkBattleModel],
        predictions: Dict[str, TechnologyPredictionModel]
    ) -> float:
        """Calculate overall confidence score for the technology intelligence.
        
        Args:
            battles: Framework battle results.
            predictions: Technology predictions.
            
        Returns:
            Overall confidence score (0-1).
        """
        try:
            confidence_scores = []
            
            # Add battle confidence scores
            for battle in battles.values():
                confidence_scores.append(battle.confidence_score)
            
            # Add prediction confidence scores
            for prediction in predictions.values():
                confidence_scores.append(prediction.confidence)
            
            if not confidence_scores:
                return 0.0
            
            # Calculate weighted average (more data points = higher confidence)
            average_confidence = sum(confidence_scores) / len(confidence_scores)
            
            # Bonus for having more data points
            data_bonus = min(len(confidence_scores) / 20, 0.1)  # Up to 10% bonus
            
            final_confidence = min(average_confidence + data_bonus, 1.0)
            return round(final_confidence, 3)
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate overall confidence: {e}")
            return 0.5  # Default moderate confidence
    
    async def get_security_intelligence(self) -> Dict[str, Any]:
        """Get security intelligence dashboard data.
        
        This is a placeholder implementation that would integrate with
        the SecurityVulnerabilityETL when implemented.
        
        Returns:
            Security intelligence data.
        """
        try:
            # Placeholder implementation
            # In a full implementation, this would integrate with SecurityVulnerabilityETL
            return {
                'placeholder': True,
                'message': 'Security intelligence integration pending',
                'vulnerabilities': [],
                'critical_count': 0,
                'average_severity': 0.0,
                'patch_availability': 0,
                'affected_technologies': [],
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Security intelligence error: {e}")
            return {'error': str(e)}
    
    def get_tech_events_intelligence(self) -> Dict[str, Any]:
        """Get technology events and conference intelligence.
        
        Returns:
            Technology events intelligence data.
        """
        try:
            # Load events from the ETL output
            events_file = self.data_dir / "tech_conference" / "output" / "tech_events_latest.json"
            
            if not events_file.exists():
                self.logger.warning("Tech events file not found, generating demo data")
                return self._generate_demo_events_data()
            
            with open(events_file, "r", encoding="utf-8") as f:
                events_data = json.load(f)
            
            # Process events data
            processed_events = []
            upcoming_events = []
            high_quality_events = []
            free_events = []
            
            for event in events_data:
                processed_event = {
                    'name': event.get('name'),
                    'description': event.get('description', '')[:200] + '...' if len(event.get('description', '')) > 200 else event.get('description', ''),
                    'start_date': event.get('start_date'),
                    'event_type': event.get('event_type'),
                    'format': event.get('format'),
                    'is_virtual': event.get('is_virtual', False),
                    'location': event.get('location') or (event.get('venue', {}).get('city') if event.get('venue') else 'TBD'),
                    'organizer': event.get('organizer'),
                    'estimated_cost': event.get('estimated_cost', 0),
                    'is_free': event.get('is_free', False),
                    'topics': event.get('topics', []),
                    'categories': event.get('categories', []),
                    'quality_score': event.get('quality_score', 0),
                    'relevance_score': event.get('relevance_score', 0),
                    'networking_score': event.get('networking_score', 0),
                    'roi_score': event.get('roi_score', 0),
                    'registration_url': event.get('registration_url'),
                    'website_url': event.get('website_url'),
                    'tags': event.get('tags', []),
                    'source_name': event.get('source_name')
                }
                
                processed_events.append(processed_event)
                
                # Categorize events
                try:
                    event_date = datetime.fromisoformat(event.get('start_date', '').replace('Z', '+00:00'))
                    if event_date > datetime.utcnow():
                        upcoming_events.append(processed_event)
                except:
                    pass
                
                if event.get('quality_score', 0) >= 75:
                    high_quality_events.append(processed_event)
                
                if event.get('is_free', False):
                    free_events.append(processed_event)
            
            # Calculate statistics
            total_events = len(processed_events)
            upcoming_count = len(upcoming_events)
            high_quality_count = len(high_quality_events)
            free_events_count = len(free_events)
            
            # Calculate average scores
            avg_quality = sum(e.get('quality_score', 0) for e in processed_events) / max(total_events, 1)
            avg_relevance = sum(e.get('relevance_score', 0) for e in processed_events) / max(total_events, 1)
            avg_networking = sum(e.get('networking_score', 0) for e in processed_events) / max(total_events, 1)
            avg_roi = sum(e.get('roi_score', 0) for e in processed_events) / max(total_events, 1)
            
            # Event type distribution
            event_types = {}
            for event in processed_events:
                event_type = event.get('event_type', 'unknown')
                event_types[event_type] = event_types.get(event_type, 0) + 1
            
            # Topic distribution
            all_topics = []
            for event in processed_events:
                all_topics.extend(event.get('topics', []))
            
            topic_counts = {}
            for topic in all_topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Format categories
            format_distribution = {}
            for event in processed_events:
                format_type = event.get('format', 'unknown')
                format_distribution[format_type] = format_distribution.get(format_type, 0) + 1
            
            return {
                'events': processed_events,
                'upcoming_events': upcoming_events[:20],  # Top 20 upcoming
                'high_quality_events': high_quality_events[:10],  # Top 10 high quality
                'free_events': free_events[:15],  # Top 15 free events
                'statistics': {
                    'total_events': total_events,
                    'upcoming_count': upcoming_count,
                    'high_quality_count': high_quality_count,
                    'free_events_count': free_events_count,
                    'avg_quality_score': round(avg_quality, 1),
                    'avg_relevance_score': round(avg_relevance, 1),
                    'avg_networking_score': round(avg_networking, 1),
                    'avg_roi_score': round(avg_roi, 1)
                },
                'distributions': {
                    'event_types': event_types,
                    'formats': format_distribution,
                    'top_topics': top_topics
                },
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Tech events intelligence error: {e}")
            return {'error': str(e)}
    
    def _generate_demo_events_data(self) -> Dict[str, Any]:
        """Generate demo events data for when ETL hasn't run yet.
        
        Returns:
            Demo events intelligence data.
        """
        demo_events = [
            {
                'name': 'AI & Machine Learning Conference 2024',
                'description': 'Join industry leaders for the latest in AI and ML innovations, featuring keynotes, workshops, and networking opportunities.',
                'start_date': (datetime.utcnow() + timedelta(days=30)).isoformat(),
                'event_type': 'conference',
                'format': 'in_person',
                'is_virtual': False,
                'location': 'San Francisco, CA',
                'organizer': 'AI Society',
                'estimated_cost': 299.0,
                'is_free': False,
                'topics': ['artificial intelligence', 'machine learning', 'deep learning'],
                'categories': ['AI/ML'],
                'quality_score': 85.0,
                'relevance_score': 90.0,
                'networking_score': 80.0,
                'roi_score': 75.0,
                'registration_url': 'https://example.com/ai-conference-2024',
                'website_url': 'https://example.com/ai-conference-2024',
                'tags': ['conference', 'ai', 'premium'],
                'source_name': 'eventbrite'
            },
            {
                'name': 'Python Data Science Workshop',
                'description': 'Hands-on workshop for data science with Python, covering pandas, scikit-learn, and machine learning fundamentals.',
                'start_date': (datetime.utcnow() + timedelta(days=21)).isoformat(),
                'event_type': 'workshop',
                'format': 'in_person',
                'is_virtual': False,
                'location': 'Austin, TX',
                'organizer': 'Austin Python Meetup',
                'estimated_cost': 50.0,
                'is_free': False,
                'topics': ['python', 'data science', 'workshop'],
                'categories': ['Data Science'],
                'quality_score': 70.0,
                'relevance_score': 85.0,
                'networking_score': 65.0,
                'roi_score': 85.0,
                'registration_url': 'https://example.com/python-workshop',
                'website_url': 'https://example.com/python-workshop',
                'tags': ['workshop', 'python', 'affordable'],
                'source_name': 'meetup'
            },
            {
                'name': 'React Developer Meetup',
                'description': 'Monthly meetup for React developers to share knowledge, network, and learn about the latest React ecosystem updates.',
                'start_date': (datetime.utcnow() + timedelta(days=14)).isoformat(),
                'event_type': 'meetup',
                'format': 'in_person',
                'is_virtual': False,
                'location': 'New York, NY',
                'organizer': 'React NYC',
                'estimated_cost': 0.0,
                'is_free': True,
                'topics': ['react', 'javascript', 'frontend'],
                'categories': ['Web Development'],
                'quality_score': 65.0,
                'relevance_score': 80.0,
                'networking_score': 75.0,
                'roi_score': 90.0,
                'registration_url': 'https://example.com/react-meetup',
                'website_url': 'https://example.com/react-meetup',
                'tags': ['meetup', 'react', 'free'],
                'source_name': 'meetup'
            },
            {
                'name': 'Blockchain & Web3 Summit',
                'description': 'Explore the future of decentralized web, featuring talks on DeFi, NFTs, and blockchain technology.',
                'start_date': (datetime.utcnow() + timedelta(days=60)).isoformat(),
                'event_type': 'summit',
                'format': 'virtual',
                'is_virtual': True,
                'location': 'Online',
                'organizer': 'Web3 Community',
                'estimated_cost': 150.0,
                'is_free': False,
                'topics': ['blockchain', 'web3', 'cryptocurrency', 'DeFi'],
                'categories': ['Blockchain/Web3'],
                'quality_score': 78.0,
                'relevance_score': 75.0,
                'networking_score': 60.0,
                'roi_score': 70.0,
                'registration_url': 'https://example.com/web3-summit',
                'website_url': 'https://example.com/web3-summit',
                'tags': ['summit', 'blockchain', 'virtual'],
                'source_name': 'dev_events'
            }
        ]
        
        return {
            'events': demo_events,
            'upcoming_events': demo_events,
            'high_quality_events': [e for e in demo_events if e['quality_score'] >= 75],
            'free_events': [e for e in demo_events if e['is_free']],
            'statistics': {
                'total_events': len(demo_events),
                'upcoming_count': len(demo_events),
                'high_quality_count': len([e for e in demo_events if e['quality_score'] >= 75]),
                'free_events_count': len([e for e in demo_events if e['is_free']]),
                'avg_quality_score': 74.5,
                'avg_relevance_score': 82.5,
                'avg_networking_score': 70.0,
                'avg_roi_score': 80.0
            },
            'distributions': {
                'event_types': {'conference': 1, 'workshop': 1, 'meetup': 1, 'summit': 1},
                'formats': {'in_person': 3, 'virtual': 1},
                'top_topics': [('python', 1), ('react', 1), ('blockchain', 1), ('machine learning', 1)]
            },
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def get_enhanced_github_trends(self) -> Dict[str, Any]:
        """Get enhanced GitHub trends with technology analysis.
        
        Returns:
            Enhanced GitHub trends data with technology insights.
        """
        try:
            # Get base GitHub data
            base_data = self.get_github_trends()
            
            if isinstance(base_data, dict) and 'error' in base_data:
                return base_data
            
            # Add technology analysis insights
            enhanced_data = {
                'base_data': base_data,
                'technology_insights': self._analyze_github_technologies(base_data),
                'trending_frameworks': self._extract_trending_frameworks(base_data),
                'language_trends': self._analyze_language_trends(base_data),
                'last_analyzed': datetime.utcnow().isoformat()
            }
            
            return enhanced_data
            
        except Exception as e:
            self.logger.error(f"Enhanced GitHub trends error: {e}")
            return {'error': str(e)}
    
    def _analyze_github_technologies(self, github_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze technology patterns in GitHub data.
        
        Args:
            github_data: GitHub repository data.
            
        Returns:
            Technology analysis insights.
        """
        try:
            insights = {
                'popular_categories': {},
                'emerging_technologies': [],
                'activity_hotspots': []
            }
            
            # Analyze repository categories
            category_counts = {}
            for repo in github_data[:50]:  # Analyze top 50
                category = repo.get('category', 'general')
                category_counts[category] = category_counts.get(category, 0) + 1
            
            insights['popular_categories'] = dict(
                sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            )
            
            # Identify emerging technologies (high activity, relatively new)
            for repo in github_data:
                if (repo.get('activity_score', 0) > 80 and 
                    repo.get('maturity') == 'new' and
                    repo.get('stars', 0) > 1000):
                    
                    insights['emerging_technologies'].append({
                        'name': repo.get('name'),
                        'description': repo.get('description', '')[:100],
                        'activity_score': repo.get('activity_score'),
                        'stars': repo.get('stars'),
                        'language': repo.get('language')
                    })
            
            # Find activity hotspots
            high_activity_repos = [
                repo for repo in github_data 
                if repo.get('activity_score', 0) > 70
            ][:10]
            
            insights['activity_hotspots'] = [
                {
                    'name': repo.get('name'),
                    'activity_score': repo.get('activity_score'),
                    'category': repo.get('category'),
                    'language': repo.get('language')
                }
                for repo in high_activity_repos
            ]
            
            return insights
            
        except Exception as e:
            self.logger.warning(f"Failed to analyze GitHub technologies: {e}")
            return {}
    
    def _extract_trending_frameworks(self, github_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract trending frameworks from GitHub data.
        
        Args:
            github_data: GitHub repository data.
            
        Returns:
            List of trending frameworks.
        """
        try:
            framework_keywords = {
                'frontend': ['react', 'vue', 'angular', 'svelte'],
                'backend': ['django', 'flask', 'fastapi', 'express'],
                'mobile': ['flutter', 'react-native', 'ionic'],
                'ml': ['tensorflow', 'pytorch', 'scikit-learn']
            }
            
            trending_frameworks = []
            
            for repo in github_data[:30]:  # Top 30 repos
                repo_name = repo.get('name', '').lower()
                repo_description = repo.get('description', '').lower()
                
                for category, frameworks in framework_keywords.items():
                    for framework in frameworks:
                        if (framework in repo_name or framework in repo_description):
                            trending_frameworks.append({
                                'framework': framework,
                                'category': category,
                                'repository': repo.get('name'),
                                'stars': repo.get('stars', 0),
                                'activity_score': repo.get('activity_score', 0),
                                'trending_rank': github_data.index(repo) + 1
                            })
                            break
            
            # Remove duplicates and sort by activity
            seen_frameworks = set()
            unique_frameworks = []
            
            for fw in sorted(trending_frameworks, key=lambda x: x['activity_score'], reverse=True):
                if fw['framework'] not in seen_frameworks:
                    unique_frameworks.append(fw)
                    seen_frameworks.add(fw['framework'])
            
            return unique_frameworks[:10]  # Top 10
            
        except Exception as e:
            self.logger.warning(f"Failed to extract trending frameworks: {e}")
            return []
    
    def _analyze_language_trends(self, github_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze programming language trends from GitHub data.
        
        Args:
            github_data: GitHub repository data.
            
        Returns:
            Language trend analysis.
        """
        try:
            language_stats = {}
            total_repos = len(github_data)
            
            for repo in github_data:
                language = repo.get('language')
                if language:
                    if language not in language_stats:
                        language_stats[language] = {
                            'count': 0,
                            'total_stars': 0,
                            'total_activity': 0,
                            'avg_activity': 0
                        }
                    
                    language_stats[language]['count'] += 1
                    language_stats[language]['total_stars'] += repo.get('stars', 0)
                    language_stats[language]['total_activity'] += repo.get('activity_score', 0)
            
            # Calculate averages and percentages
            for language, stats in language_stats.items():
                stats['percentage'] = round((stats['count'] / total_repos) * 100, 1)
                stats['avg_stars'] = round(stats['total_stars'] / stats['count'], 1)
                stats['avg_activity'] = round(stats['total_activity'] / stats['count'], 1)
            
            # Sort by count and return top languages
            top_languages = dict(
                sorted(language_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:8]
            )
            
            return {
                'top_languages': top_languages,
                'total_languages': len(language_stats),
                'language_diversity': round(len(language_stats) / total_repos, 2)
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to analyze language trends: {e}")
            return {} 