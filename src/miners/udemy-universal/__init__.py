"""Udemy course mining and enrollment module.

This module provides tools for discovering free Udemy courses
from multiple sources and enrolling in them automatically.

Main components:
- Domain models (Course, Instructor, EnrollmentResult)
- Scrapers (Strategy pattern for site-specific scrapers)
- Services (Enrollment, link cleaning, filtering)
- Infrastructure (Udemy API client)
- Configuration (Centralized settings)
"""

from .config import Config, EnrollmentConfig, FilterSettings, LoggingConfig, UdemyClientConfig
from .domain import Course, CourseDetails, EnrollmentResult, Instructor, ScraperResult
from .infrastructure import LoginError, UdemyClient
from .scrapers import BaseScraper, DiscudemyScraper, PlaywrightScraper, ScraperFactory
from .services import CourseFilter, EnrollmentService, LinkCleaner

__version__ = "3.0.0"

__all__ = [
    # Configuration
    "Config",
    "EnrollmentConfig",
    "FilterSettings",
    "LoggingConfig",
    "UdemyClientConfig",
    # Domain models
    "Course",
    "CourseDetails",
    "EnrollmentResult",
    "Instructor",
    "ScraperResult",
    # Infrastructure
    "LoginError",
    "UdemyClient",
    # Scrapers
    "BaseScraper",
    "DiscudemyScraper",
    "PlaywrightScraper",
    "ScraperFactory",
    # Services
    "CourseFilter",
    "EnrollmentService",
    "LinkCleaner",
]
