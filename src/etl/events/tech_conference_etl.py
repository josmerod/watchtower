"""ETL for technology conferences and events intelligence."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse

import aiohttp
import requests
from bs4 import BeautifulSoup
from feedparser import parse as parse_feed

from src.etl.base import BaseETL
from src.exceptions.etl import ExtractionError, TransformationError
from src.models.events import (
    TechEventModel, SpeakerModel, VenueModel, EventType, EventFormat, EventStatus
)
from src.utils.logging import get_logger


class TechConferenceETL(BaseETL):
    """Technology conference and event intelligence ETL.
    
    This ETL gathers comprehensive technology event data from multiple sources:
    - Eventbrite tech events
    - Meetup.com developer meetups  
    - Conference websites via RSS/API
    - Technology conference aggregators
    """
    
    def __init__(
        self,
        name: str = "tech_conference",
        max_events_per_source: int = 100,
        days_ahead: int = 365,
        **kwargs
    ):
        """Initialize the Tech Conference ETL.
        
        Args:
            name: ETL process name
            max_events_per_source: Maximum events to fetch per source
            days_ahead: How many days ahead to look for events
            **kwargs: Additional arguments for base class
        """
        super().__init__(name, **kwargs)
        
        self.max_events_per_source = max_events_per_source
        self.days_ahead = days_ahead
        
        # Event data sources configuration
        self.data_sources = {
            "eventbrite": {
                "enabled": True,
                "api_base": "https://www.eventbriteapi.com/v3/",
                "search_terms": ["developer", "programming", "tech", "software", "AI", "machine learning", "blockchain"],
                "categories": ["102", "103"]  # Technology, Business categories
            },
            "meetup": {
                "enabled": True,
                "api_base": "https://api.meetup.com/",
                "topics": ["tech", "programming", "python", "javascript", "react", "ai", "ml"]
            },
            "dev_events": {
                "enabled": True,
                "feeds": [
                    "https://dev.events/feed.xml",
                    "https://events.python.org/en/feed.xml"
                ]
            },
            "conference_sites": {
                "enabled": True,
                "sites": [
                    {
                        "name": "TechCrunch Events",
                        "url": "https://techcrunch.com/events/",
                        "type": "html_scrape"
                    },
                    {
                        "name": "IEEE Events",
                        "url": "https://www.ieee.org/conferences/index.html",
                        "type": "html_scrape"
                    }
                ]
            }
        }
        
        # Technology keywords for relevance scoring
        self.tech_keywords = {
            "high_priority": [
                "artificial intelligence", "machine learning", "AI", "ML", "deep learning",
                "blockchain", "cryptocurrency", "web3", "NFT", "DeFi",
                "cloud computing", "AWS", "Azure", "kubernetes", "docker",
                "python", "javascript", "react", "vue", "angular", "node.js",
                "data science", "big data", "analytics", "business intelligence",
                "cybersecurity", "security", "devops", "CI/CD", "automation"
            ],
            "medium_priority": [
                "software development", "programming", "coding", "development",
                "mobile development", "iOS", "android", "flutter", "react native",
                "web development", "frontend", "backend", "full stack",
                "database", "SQL", "NoSQL", "API", "microservices",
                "agile", "scrum", "project management", "product management"
            ],
            "general": [
                "technology", "tech", "innovation", "startup", "entrepreneur",
                "digital transformation", "IT", "computer science", "engineering"
            ]
        }
        
        # Speaker influence indicators
        self.speaker_influence_indicators = [
            "CTO", "CEO", "founder", "lead engineer", "principal", "senior",
            "author", "speaker", "trainer", "consultant", "evangelist",
            "Google", "Microsoft", "Amazon", "Facebook", "Apple", "Netflix",
            "published", "book", "conference speaker", "keynote"
        ]
    
    def extract(self) -> List[Dict[str, Any]]:
        """Extract events from all configured sources.
        
        Returns:
            List of raw event data from all sources.
            
        Raises:
            ExtractionError: If extraction from all sources fails.
        """
        all_events = []
        extraction_errors = []
        
        try:
            # Extract from each source
            for source_name, config in self.data_sources.items():
                if not config.get("enabled", False):
                    self.logger.info(f"Skipping disabled source: {source_name}")
                    continue
                
                self.logger.info(f"Extracting events from {source_name}")
                
                try:
                    if source_name == "eventbrite":
                        events = self._extract_eventbrite_events(config)
                    elif source_name == "meetup":
                        events = self._extract_meetup_events(config)
                    elif source_name == "dev_events":
                        events = self._extract_dev_events_feeds(config)
                    elif source_name == "conference_sites":
                        events = self._extract_conference_sites(config)
                    else:
                        self.logger.warning(f"Unknown source: {source_name}")
                        continue
                    
                    # Add source information to each event
                    for event in events:
                        event["source_name"] = source_name
                        event["extracted_at"] = datetime.utcnow().isoformat()
                    
                    all_events.extend(events)
                    self.logger.info(f"Extracted {len(events)} events from {source_name}")
                    
                except Exception as e:
                    error_msg = f"Failed to extract from {source_name}: {e}"
                    self.logger.error(error_msg)
                    extraction_errors.append(error_msg)
                    continue
            
            if not all_events and extraction_errors:
                raise ExtractionError(
                    "Failed to extract events from any source",
                    context={"errors": extraction_errors}
                )
            
            self.logger.info(f"Total events extracted: {len(all_events)}")
            return all_events
            
        except Exception as e:
            if isinstance(e, ExtractionError):
                raise
            raise ExtractionError(f"Event extraction failed: {e}")
    
    def _extract_eventbrite_events(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract events from Eventbrite API.
        
        Args:
            config: Eventbrite configuration.
            
        Returns:
            List of raw event data from Eventbrite.
        """
        events = []
        
        # Note: Eventbrite API requires authentication
        # For demo purposes, we'll create mock data
        # In production, you would need to:
        # 1. Register for Eventbrite API access
        # 2. Use OAuth token for authentication
        # 3. Make actual API calls
        
        self.logger.info("Generating mock Eventbrite events for demonstration")
        
        # Mock Eventbrite events
        mock_events = [
            {
                "name": "AI & Machine Learning Conference 2024",
                "description": "Join industry leaders for the latest in AI and ML innovations",
                "start_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=32)).isoformat(),
                "venue": {
                    "name": "San Francisco Convention Center",
                    "address": "747 Howard St, San Francisco, CA 94103",
                    "city": "San Francisco",
                    "country": "USA"
                },
                "organizer": "AI Society",
                "url": "https://example.com/ai-conference-2024",
                "cost": 299.0,
                "is_virtual": False,
                "topics": ["artificial intelligence", "machine learning", "deep learning"],
                "event_type": "conference"
            },
            {
                "name": "React Developer Meetup",
                "description": "Monthly meetup for React developers",
                "start_date": (datetime.utcnow() + timedelta(days=14)).isoformat(),
                "venue": {
                    "name": "Tech Hub",
                    "address": "123 Tech St",
                    "city": "New York",
                    "country": "USA"
                },
                "organizer": "React NYC",
                "url": "https://example.com/react-meetup",
                "cost": 0.0,
                "is_virtual": False,
                "topics": ["react", "javascript", "frontend"],
                "event_type": "meetup"
            }
        ]
        
        events.extend(mock_events)
        return events
    
    def _extract_meetup_events(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract events from Meetup.com API.
        
        Args:
            config: Meetup configuration.
            
        Returns:
            List of raw event data from Meetup.
        """
        events = []
        
        # Note: Meetup API also requires authentication
        # For demo purposes, generating mock data
        
        self.logger.info("Generating mock Meetup events for demonstration")
        
        mock_events = [
            {
                "name": "Python Data Science Workshop",
                "description": "Hands-on workshop for data science with Python",
                "start_date": (datetime.utcnow() + timedelta(days=21)).isoformat(),
                "venue": {
                    "name": "Data Science Institute",
                    "address": "456 Data Ave",
                    "city": "Austin",
                    "country": "USA"
                },
                "organizer": "Austin Python Meetup",
                "url": "https://example.com/python-workshop",
                "cost": 50.0,
                "is_virtual": False,
                "topics": ["python", "data science", "workshop"],
                "event_type": "workshop",
                "attendee_count": 45
            },
            {
                "name": "Blockchain & Web3 Summit",
                "description": "Explore the future of decentralized web",
                "start_date": (datetime.utcnow() + timedelta(days=60)).isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=61)).isoformat(),
                "venue": {
                    "name": "Virtual Event Platform",
                    "city": "Online",
                    "country": "Global"
                },
                "organizer": "Web3 Community",
                "url": "https://example.com/web3-summit",
                "cost": 150.0,
                "is_virtual": True,
                "topics": ["blockchain", "web3", "cryptocurrency", "DeFi"],
                "event_type": "summit"
            }
        ]
        
        events.extend(mock_events)
        return events
    
    def _extract_dev_events_feeds(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract events from RSS/Atom feeds.
        
        Args:
            config: Feed configuration.
            
        Returns:
            List of raw event data from feeds.
        """
        events = []
        
        for feed_url in config.get("feeds", []):
            try:
                self.logger.info(f"Parsing feed: {feed_url}")
                
                # Parse RSS/Atom feed
                feed = parse_feed(feed_url)
                
                for entry in feed.entries[:self.max_events_per_source]:
                    # Extract event information from feed entry
                    event_data = {
                        "name": entry.get("title", "").strip(),
                        "description": entry.get("summary", "").strip(),
                        "url": entry.get("link", ""),
                        "published_date": entry.get("published", ""),
                        "topics": self._extract_topics_from_text(entry.get("title", "") + " " + entry.get("summary", "")),
                        "event_type": "conference",  # Default assumption
                        "is_virtual": "virtual" in entry.get("title", "").lower() or "online" in entry.get("summary", "").lower()
                    }
                    
                    # Try to extract date information
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        event_data["start_date"] = datetime(*entry.published_parsed[:6]).isoformat()
                    
                    events.append(event_data)
                
            except Exception as e:
                self.logger.warning(f"Failed to parse feed {feed_url}: {e}")
                continue
        
        return events
    
    def _extract_conference_sites(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract events by scraping conference websites.
        
        Args:
            config: Conference sites configuration.
            
        Returns:
            List of raw event data from conference sites.
        """
        events = []
        
        for site in config.get("sites", []):
            try:
                site_name = site.get("name", "Unknown")
                site_url = site.get("url", "")
                
                self.logger.info(f"Scraping events from {site_name}")
                
                # For demo purposes, we'll generate mock data
                # In production, you would implement actual web scraping
                mock_event = {
                    "name": f"{site_name} Developer Conference 2024",
                    "description": f"Annual conference hosted by {site_name}",
                    "start_date": (datetime.utcnow() + timedelta(days=90)).isoformat(),
                    "url": site_url,
                    "organizer": site_name,
                    "topics": ["technology", "innovation", "development"],
                    "event_type": "conference",
                    "is_virtual": False
                }
                
                events.append(mock_event)
                
            except Exception as e:
                self.logger.warning(f"Failed to scrape {site.get('name', 'unknown site')}: {e}")
                continue
        
        return events
    
    def transform(self, data: List[Dict[str, Any]]) -> List[TechEventModel]:
        """Transform raw event data into structured models.
        
        Args:
            data: List of raw event data.
            
        Returns:
            List of transformed TechEventModel objects.
            
        Raises:
            TransformationError: If transformation fails for all events.
        """
        transformed_events = []
        transformation_errors = []
        
        for i, event_data in enumerate(data):
            try:
                # Transform single event
                transformed_event = self._transform_single_event(event_data, i)
                
                if transformed_event:
                    transformed_events.append(transformed_event)
                    
            except Exception as e:
                error_msg = f"Failed to transform event {i}: {e}"
                self.logger.warning(error_msg)
                transformation_errors.append(error_msg)
                continue
        
        if not transformed_events and transformation_errors:
            raise TransformationError(
                "Failed to transform any events",
                context={"errors": transformation_errors}
            )
        
        self.logger.info(f"Successfully transformed {len(transformed_events)} events")
        return transformed_events
    
    def _transform_single_event(self, event_data: Dict[str, Any], index: int) -> Optional[TechEventModel]:
        """Transform a single event data record.
        
        Args:
            event_data: Raw event data.
            index: Event index for tracking.
            
        Returns:
            Transformed TechEventModel or None if transformation fails.
        """
        try:
            # Extract basic information
            name = event_data.get("name", "").strip()
            if not name:
                self.logger.warning(f"Event {index} missing name, skipping")
                return None
            
            # Determine event type
            event_type = self._determine_event_type(event_data)
            
            # Determine event format
            event_format = self._determine_event_format(event_data)
            
            # Parse dates
            start_date = self._parse_event_date(event_data.get("start_date"))
            end_date = self._parse_event_date(event_data.get("end_date"))
            
            if not start_date:
                # If no start date, skip this event
                self.logger.warning(f"Event {index} missing start date, skipping")
                return None
            
            # Create venue if venue data exists
            venue = self._create_venue_model(event_data.get("venue"))
            
            # Extract and analyze topics
            topics = event_data.get("topics", [])
            if isinstance(topics, str):
                topics = [topics]
            
            # Calculate intelligence scores
            speaker_influence_score = self._analyze_speaker_influence(event_data.get("speakers", []))
            relevance_score = self._calculate_topic_relevance(event_data)
            networking_score = self._assess_networking_potential(event_data)
            roi_score = self._calculate_event_roi(event_data)
            quality_score = self._calculate_quality_score(
                speaker_influence_score, relevance_score, networking_score
            )
            
            # Create the enhanced event model
            enhanced_event = TechEventModel(
                # Core information
                name=name,
                description=event_data.get("description", ""),
                event_type=event_type,
                format=event_format,
                status=EventStatus.UPCOMING,
                
                # Date information
                start_date=start_date,
                end_date=end_date,
                
                # Location information
                venue=venue,
                location=event_data.get("location"),
                is_virtual=event_data.get("is_virtual", False),
                virtual_platform=event_data.get("virtual_platform"),
                
                # Content
                topics=topics,
                technologies=self._extract_technologies(event_data),
                
                # Organization
                organizer=event_data.get("organizer"),
                
                # Registration
                registration_url=event_data.get("url"),
                estimated_cost=event_data.get("cost", 0.0),
                is_free=event_data.get("cost", 0.0) == 0.0,
                
                # Intelligence scores
                speaker_influence_score=speaker_influence_score,
                relevance_score=relevance_score,
                networking_score=networking_score,
                roi_score=roi_score,
                quality_score=quality_score,
                
                # Social metrics
                attendee_count=event_data.get("attendee_count"),
                
                # Links
                website_url=event_data.get("url"),
                
                # Source information
                source_name=event_data.get("source_name", "unknown"),
                source_url=event_data.get("url"),
                
                # Additional data
                tags=self._generate_event_tags(event_data),
                categories=self._classify_event_categories(event_data)
            )
            
            return enhanced_event
            
        except Exception as e:
            self.logger.error(f"Failed to transform event {index}: {e}")
            return None
    
    def _determine_event_type(self, event_data: Dict[str, Any]) -> EventType:
        """Determine the event type from event data.
        
        Args:
            event_data: Raw event data.
            
        Returns:
            EventType enum value.
        """
        event_type_str = event_data.get("event_type", "").lower()
        name_and_desc = (event_data.get("name", "") + " " + event_data.get("description", "")).lower()
        
        # Direct mapping
        if event_type_str in ["conference", "summit", "festival"]:
            return getattr(EventType, event_type_str.upper())
        elif event_type_str in ["workshop", "meetup", "webinar", "hackathon", "bootcamp"]:
            return getattr(EventType, event_type_str.upper())
        
        # Keyword-based detection
        if any(keyword in name_and_desc for keyword in ["workshop", "hands-on", "training"]):
            return EventType.WORKSHOP
        elif any(keyword in name_and_desc for keyword in ["meetup", "gathering", "meet-up"]):
            return EventType.MEETUP
        elif any(keyword in name_and_desc for keyword in ["webinar", "online session", "virtual talk"]):
            return EventType.WEBINAR
        elif any(keyword in name_and_desc for keyword in ["hackathon", "hack day", "coding competition"]):
            return EventType.HACKATHON
        elif any(keyword in name_and_desc for keyword in ["bootcamp", "intensive", "immersive"]):
            return EventType.BOOTCAMP
        elif any(keyword in name_and_desc for keyword in ["summit", "festival"]):
            return EventType.SUMMIT if "summit" in name_and_desc else EventType.FESTIVAL
        else:
            return EventType.CONFERENCE  # Default
    
    def _determine_event_format(self, event_data: Dict[str, Any]) -> EventFormat:
        """Determine the event format from event data.
        
        Args:
            event_data: Raw event data.
            
        Returns:
            EventFormat enum value.
        """
        is_virtual = event_data.get("is_virtual", False)
        has_venue = event_data.get("venue") is not None
        name_and_desc = (event_data.get("name", "") + " " + event_data.get("description", "")).lower()
        
        if is_virtual and not has_venue:
            return EventFormat.VIRTUAL
        elif is_virtual and has_venue:
            return EventFormat.HYBRID
        elif "hybrid" in name_and_desc:
            return EventFormat.HYBRID
        elif "virtual" in name_and_desc or "online" in name_and_desc:
            return EventFormat.VIRTUAL
        else:
            return EventFormat.IN_PERSON
    
    def _parse_event_date(self, date_str: Union[str, datetime, None]) -> Optional[datetime]:
        """Parse event date from various formats.
        
        Args:
            date_str: Date string or datetime object.
            
        Returns:
            Parsed datetime or None if parsing fails.
        """
        if not date_str:
            return None
        
        if isinstance(date_str, datetime):
            return date_str
        
        try:
            # Try ISO format first
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pass
        
        # Add more date parsing logic as needed
        try:
            from dateutil.parser import parse
            return parse(date_str)
        except:
            self.logger.warning(f"Failed to parse date: {date_str}")
            return None
    
    def _create_venue_model(self, venue_data: Optional[Dict[str, Any]]) -> Optional[VenueModel]:
        """Create a VenueModel from venue data.
        
        Args:
            venue_data: Raw venue data.
            
        Returns:
            VenueModel instance or None.
        """
        if not venue_data or not venue_data.get("name"):
            return None
        
        try:
            return VenueModel(
                name=venue_data["name"],
                address=venue_data.get("address"),
                city=venue_data.get("city"),
                country=venue_data.get("country"),
                venue_type=venue_data.get("venue_type"),
                capacity=venue_data.get("capacity"),
                website_url=venue_data.get("website_url")
            )
        except Exception as e:
            self.logger.warning(f"Failed to create venue model: {e}")
            return None
    
    def _analyze_speaker_influence(self, speakers_data: List[Dict[str, Any]]) -> float:
        """Analyze speaker influence score.
        
        Args:
            speakers_data: List of speaker data.
            
        Returns:
            Speaker influence score (0-100).
        """
        if not speakers_data:
            return 0.0
        
        total_influence = 0.0
        
        for speaker in speakers_data:
            speaker_influence = 0.0
            speaker_text = " ".join([
                speaker.get("name", ""),
                speaker.get("title", ""),
                speaker.get("company", ""),
                speaker.get("bio", "")
            ]).lower()
            
            # Check for influence indicators
            for indicator in self.speaker_influence_indicators:
                if indicator.lower() in speaker_text:
                    speaker_influence += 10.0
            
            # Cap individual speaker influence
            speaker_influence = min(speaker_influence, 100.0)
            total_influence += speaker_influence
        
        # Average influence across all speakers
        average_influence = total_influence / len(speakers_data)
        return min(average_influence, 100.0)
    
    def _calculate_topic_relevance(self, event_data: Dict[str, Any]) -> float:
        """Calculate topic relevance score based on tech keywords.
        
        Args:
            event_data: Raw event data.
            
        Returns:
            Topic relevance score (0-100).
        """
        text_content = " ".join([
            event_data.get("name", ""),
            event_data.get("description", ""),
            " ".join(event_data.get("topics", []))
        ]).lower()
        
        relevance_score = 0.0
        
        # High priority keywords
        for keyword in self.tech_keywords["high_priority"]:
            if keyword.lower() in text_content:
                relevance_score += 15.0
        
        # Medium priority keywords
        for keyword in self.tech_keywords["medium_priority"]:
            if keyword.lower() in text_content:
                relevance_score += 10.0
        
        # General tech keywords
        for keyword in self.tech_keywords["general"]:
            if keyword.lower() in text_content:
                relevance_score += 5.0
        
        return min(relevance_score, 100.0)
    
    def _assess_networking_potential(self, event_data: Dict[str, Any]) -> float:
        """Assess networking potential of the event.
        
        Args:
            event_data: Raw event data.
            
        Returns:
            Networking potential score (0-100).
        """
        networking_score = 0.0
        
        # Base score for all events
        networking_score += 20.0
        
        # Attendee count bonus
        attendee_count = event_data.get("attendee_count", 0)
        if attendee_count > 500:
            networking_score += 30.0
        elif attendee_count > 100:
            networking_score += 20.0
        elif attendee_count > 50:
            networking_score += 10.0
        
        # Event type bonuses
        event_type = event_data.get("event_type", "").lower()
        if event_type in ["conference", "summit"]:
            networking_score += 25.0
        elif event_type in ["meetup", "workshop"]:
            networking_score += 15.0
        
        # Multi-day events have better networking
        start_date = self._parse_event_date(event_data.get("start_date"))
        end_date = self._parse_event_date(event_data.get("end_date"))
        if start_date and end_date and (end_date - start_date).days > 0:
            networking_score += 15.0
        
        # In-person events have better networking
        if not event_data.get("is_virtual", False):
            networking_score += 10.0
        
        return min(networking_score, 100.0)
    
    def _calculate_event_roi(self, event_data: Dict[str, Any]) -> float:
        """Calculate return on investment score for the event.
        
        Args:
            event_data: Raw event data.
            
        Returns:
            ROI score (0-100).
        """
        roi_score = 0.0
        
        # Cost factor (lower cost = higher ROI)
        cost = event_data.get("cost", 0.0)
        if cost == 0.0:
            roi_score += 40.0  # Free events get high ROI
        elif cost < 100.0:
            roi_score += 30.0
        elif cost < 500.0:
            roi_score += 20.0
        else:
            roi_score += 10.0
        
        # Value indicators
        text_content = " ".join([
            event_data.get("name", ""),
            event_data.get("description", "")
        ]).lower()
        
        value_keywords = [
            "certification", "certificate", "training", "workshop",
            "hands-on", "practical", "project", "portfolio",
            "networking", "career", "job", "recruitment"
        ]
        
        for keyword in value_keywords:
            if keyword in text_content:
                roi_score += 8.0
        
        # Duration factor (longer events often provide more value)
        start_date = self._parse_event_date(event_data.get("start_date"))
        end_date = self._parse_event_date(event_data.get("end_date"))
        if start_date and end_date:
            duration_days = (end_date - start_date).days
            if duration_days >= 2:
                roi_score += 15.0
            elif duration_days >= 1:
                roi_score += 10.0
        
        return min(roi_score, 100.0)
    
    def _calculate_quality_score(
        self, 
        speaker_influence: float, 
        relevance: float, 
        networking: float
    ) -> float:
        """Calculate overall quality score.
        
        Args:
            speaker_influence: Speaker influence score.
            relevance: Topic relevance score.
            networking: Networking potential score.
            
        Returns:
            Overall quality score (0-100).
        """
        # Weighted average of component scores
        quality_score = (
            speaker_influence * 0.4 +
            relevance * 0.4 +
            networking * 0.2
        )
        
        return min(quality_score, 100.0)
    
    def _extract_topics_from_text(self, text: str) -> List[str]:
        """Extract topics from text using keyword matching.
        
        Args:
            text: Text to extract topics from.
            
        Returns:
            List of identified topics.
        """
        topics = []
        text_lower = text.lower()
        
        # Check all tech keywords
        for priority_level, keywords in self.tech_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    topics.append(keyword)
        
        return list(set(topics))  # Remove duplicates
    
    def _extract_technologies(self, event_data: Dict[str, Any]) -> List[str]:
        """Extract specific technologies mentioned.
        
        Args:
            event_data: Raw event data.
            
        Returns:
            List of technologies.
        """
        text_content = " ".join([
            event_data.get("name", ""),
            event_data.get("description", ""),
            " ".join(event_data.get("topics", []))
        ])
        
        # Technology-specific keywords
        tech_patterns = [
            r'\b(Python|JavaScript|Java|C\+\+|C#|Go|Rust|Swift|Kotlin)\b',
            r'\b(React|Vue|Angular|Django|Flask|FastAPI|Node\.js|Express)\b',
            r'\b(AWS|Azure|GCP|Docker|Kubernetes|Jenkins|GitLab)\b',
            r'\b(TensorFlow|PyTorch|Scikit-learn|Pandas|NumPy)\b',
            r'\b(PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch)\b'
        ]
        
        technologies = []
        for pattern in tech_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            technologies.extend(matches)
        
        return list(set(technologies))
    
    def _generate_event_tags(self, event_data: Dict[str, Any]) -> List[str]:
        """Generate tags for the event.
        
        Args:
            event_data: Raw event data.
            
        Returns:
            List of tags.
        """
        tags = []
        
        # Add event type as tag
        event_type = event_data.get("event_type", "")
        if event_type:
            tags.append(event_type)
        
        # Add format tags
        if event_data.get("is_virtual"):
            tags.append("virtual")
        else:
            tags.append("in-person")
        
        # Add cost tags
        cost = event_data.get("cost", 0.0)
        if cost == 0.0:
            tags.append("free")
        elif cost < 100.0:
            tags.append("affordable")
        else:
            tags.append("premium")
        
        # Add topic-based tags
        topics = event_data.get("topics", [])
        if isinstance(topics, list):
            tags.extend(topics[:5])  # Limit to 5 topic tags
        
        return tags
    
    def _classify_event_categories(self, event_data: Dict[str, Any]) -> List[str]:
        """Classify event into categories.
        
        Args:
            event_data: Raw event data.
            
        Returns:
            List of categories.
        """
        categories = []
        
        text_content = " ".join([
            event_data.get("name", ""),
            event_data.get("description", "")
        ]).lower()
        
        # Technology categories
        if any(keyword in text_content for keyword in ["ai", "artificial intelligence", "machine learning", "ml"]):
            categories.append("AI/ML")
        
        if any(keyword in text_content for keyword in ["web development", "frontend", "backend", "javascript", "react"]):
            categories.append("Web Development")
        
        if any(keyword in text_content for keyword in ["mobile", "ios", "android", "flutter", "react native"]):
            categories.append("Mobile Development")
        
        if any(keyword in text_content for keyword in ["data science", "analytics", "big data", "data"]):
            categories.append("Data Science")
        
        if any(keyword in text_content for keyword in ["blockchain", "cryptocurrency", "web3", "defi"]):
            categories.append("Blockchain/Web3")
        
        if any(keyword in text_content for keyword in ["cloud", "aws", "azure", "kubernetes", "docker"]):
            categories.append("Cloud Computing")
        
        if any(keyword in text_content for keyword in ["security", "cybersecurity", "infosec"]):
            categories.append("Security")
        
        if any(keyword in text_content for keyword in ["devops", "ci/cd", "automation", "deployment"]):
            categories.append("DevOps")
        
        # Default category if none matched
        if not categories:
            categories.append("Technology")
        
        return categories
    
    def load(self, data: List[TechEventModel]) -> None:
        """Load transformed events to storage.
        
        Args:
            data: List of transformed TechEventModel objects.
        """
        if not data:
            self.logger.warning("No events to load")
            return
        
        # Save as JSON file
        output_data = []
        for event in data:
            try:
                # Convert to dict for JSON serialization
                event_dict = event.model_dump()
                # Convert datetime objects to ISO strings
                for key, value in event_dict.items():
                    if isinstance(value, datetime):
                        event_dict[key] = value.isoformat()
                    elif isinstance(value, dict):
                        # Handle nested datetime objects
                        for nested_key, nested_value in value.items():
                            if isinstance(nested_value, datetime):
                                value[nested_key] = nested_value.isoformat()
                
                output_data.append(event_dict)
                
            except Exception as e:
                self.logger.warning(f"Failed to serialize event: {e}")
                continue
        
        # Save to output file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"tech_events_{timestamp}.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
        
        # Also save as latest
        latest_file = self.output_dir / "tech_events_latest.json"
        with open(latest_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)
        
        self.logger.info(f"Saved {len(output_data)} events to {output_file}")
    
    def generate_event_recommendations(
        self, 
        user_profile: Dict[str, Any],
        events: Optional[List[TechEventModel]] = None
    ) -> List[Dict[str, Any]]:
        """Generate personalized event recommendations.
        
        Args:
            user_profile: User preferences and profile.
            events: Optional list of events to recommend from.
            
        Returns:
            List of event recommendations with scores.
        """
        if events is None:
            # Load events from latest file
            latest_file = self.output_dir / "tech_events_latest.json"
            if latest_file.exists():
                with open(latest_file, "r", encoding="utf-8") as f:
                    events_data = json.load(f)
                    events = [TechEventModel(**event) for event in events_data]
            else:
                return []
        
        recommendations = []
        user_interests = user_profile.get("interests", [])
        user_location = user_profile.get("location", "")
        budget = user_profile.get("budget", float("inf"))
        
        for event in events:
            try:
                # Calculate recommendation components
                interest_match = self._calculate_interest_match(event.topics, user_interests)
                location_convenience = self._calculate_location_convenience(
                    event.location or (event.venue.city if event.venue else ""), 
                    user_location
                )
                budget_fit = 1.0 if (event.estimated_cost or 0.0) <= budget else 0.0
                
                # Calculate overall recommendation score
                recommendation_score = (
                    interest_match * 0.4 +
                    event.relevance_score / 100.0 * 0.3 +
                    location_convenience * 0.2 +
                    budget_fit * 0.1
                ) * 100.0
                
                if recommendation_score >= 50.0:  # Threshold for recommendations
                    recommendation = {
                        "event": event.model_dump(),
                        "recommendation_score": recommendation_score,
                        "recommendation_reason": self._generate_recommendation_reason(
                            event, interest_match, location_convenience, budget_fit
                        ),
                        "interest_match": interest_match,
                        "location_convenience": location_convenience,
                        "budget_fit": budget_fit
                    }
                    recommendations.append(recommendation)
                    
            except Exception as e:
                self.logger.warning(f"Failed to generate recommendation for event {event.name}: {e}")
                continue
        
        # Sort by recommendation score
        recommendations.sort(key=lambda x: x["recommendation_score"], reverse=True)
        
        return recommendations[:10]  # Return top 10 recommendations
    
    def _calculate_interest_match(self, event_topics: List[str], user_interests: List[str]) -> float:
        """Calculate how well event topics match user interests.
        
        Args:
            event_topics: List of event topics.
            user_interests: List of user interests.
            
        Returns:
            Interest match score (0-1).
        """
        if not user_interests or not event_topics:
            return 0.5  # Default neutral score
        
        # Convert to lowercase for comparison
        event_topics_lower = [topic.lower() for topic in event_topics]
        user_interests_lower = [interest.lower() for interest in user_interests]
        
        # Calculate overlap
        matches = 0
        for interest in user_interests_lower:
            for topic in event_topics_lower:
                if interest in topic or topic in interest:
                    matches += 1
                    break
        
        # Calculate match ratio
        match_ratio = matches / len(user_interests)
        return min(match_ratio, 1.0)
    
    def _calculate_location_convenience(self, event_location: str, user_location: str) -> float:
        """Calculate location convenience score.
        
        Args:
            event_location: Event location.
            user_location: User location.
            
        Returns:
            Location convenience score (0-1).
        """
        if not event_location or not user_location:
            return 0.5  # Default neutral score
        
        event_location = event_location.lower()
        user_location = user_location.lower()
        
        # Virtual events are always convenient
        if "virtual" in event_location or "online" in event_location:
            return 1.0
        
        # Same city/country matching
        if user_location in event_location or event_location in user_location:
            return 1.0
        
        # Regional matching (simplified)
        user_words = user_location.split()
        event_words = event_location.split()
        
        common_words = set(user_words) & set(event_words)
        if common_words:
            return 0.7
        
        return 0.3  # Default for different locations
    
    def _generate_recommendation_reason(
        self, 
        event: TechEventModel, 
        interest_match: float, 
        location_convenience: float, 
        budget_fit: float
    ) -> str:
        """Generate a human-readable recommendation reason.
        
        Args:
            event: Event being recommended.
            interest_match: Interest match score.
            location_convenience: Location convenience score.
            budget_fit: Budget fit score.
            
        Returns:
            Recommendation reason string.
        """
        reasons = []
        
        if interest_match > 0.7:
            reasons.append("closely matches your interests")
        elif interest_match > 0.5:
            reasons.append("aligns with your interests")
        
        if location_convenience > 0.8:
            reasons.append("is conveniently located")
        elif event.is_virtual:
            reasons.append("is virtual and accessible from anywhere")
        
        if budget_fit > 0.9 and event.is_free:
            reasons.append("is free to attend")
        elif budget_fit > 0.9:
            reasons.append("fits within your budget")
        
        if event.quality_score > 80:
            reasons.append("has high-quality speakers and content")
        elif event.quality_score > 60:
            reasons.append("has good quality content")
        
        if event.networking_score > 70:
            reasons.append("offers excellent networking opportunities")
        
        if not reasons:
            reasons.append("is a relevant technology event")
        
        return f"This event {', '.join(reasons[:3])}.{' Plus, it has a high overall quality score.' if event.quality_score > 75 else ''}" 