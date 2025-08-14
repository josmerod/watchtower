"""Software & Productivity Tools Deals ETL Module

This module aggregates software deals, SaaS offers, productivity tools,
and development software from various platforms and marketplaces.

Usage:
    python src/etl/deals/software_deals_etl.py

Output:
    - JSON file: data/deals/software_deals.json
    - CSV file: data/deals/software_deals.csv
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
import requests
from bs4 import BeautifulSoup
import re

# Add the project root to the path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger
from src.etl.base import BaseETL

# Initialize logger
logger = get_logger("SoftwareDealsETL")


class SoftwareDealsETL(BaseETL):
    """ETL for software and productivity tools deals."""

    def __init__(self):
        super().__init__("software_deals")
        self.sources = {
            "github_free": {
                "name": "GitHub",
                "education_url": "https://education.github.com/pack",
                "sponsors_url": "https://github.com/sponsors",
                "category": "development_tools",
            },
            "microsoft_free": {
                "name": "Microsoft",
                "dev_tools_url": "https://visualstudio.microsoft.com/free-developer-offers/",
                "education_url": "https://azure.microsoft.com/en-us/free/students/",
                "category": "development_tools",
            },
            "jetbrains_free": {
                "name": "JetBrains",
                "community_url": "https://www.jetbrains.com/community/",
                "education_url": "https://www.jetbrains.com/community/education/",
                "category": "development_tools",
            },
            "google_workspace": {
                "name": "Google Workspace",
                "free_url": "https://workspace.google.com/pricing.html",
                "category": "productivity",
            },
        }

    def extract(self) -> Dict[str, Any]:
        """Extract software deals from multiple sources."""
        logger.info("Starting software deals extraction...")

        all_deals = []

        # Add curated software deals and free sources
        curated_deals = self._get_curated_software_deals()
        all_deals.extend(curated_deals)

        logger.info(f"Total extracted {len(all_deals)} software deals")
        return {"deals": all_deals, "total_count": len(all_deals)}

    def _get_curated_software_deals(self) -> List[Dict[str, Any]]:
        """Get manually curated list of software deals and free sources."""
        curated = [
            {
                "title": "GitHub Student Developer Pack",
                "description": "Free developer tools worth $200k+ for students including domain names, cloud credits, and premium software",
                "url": "https://education.github.com/pack",
                "platform": "GitHub Education",
                "category": "development_tools",
                "deal_type": "student_pack",
                "original_price": 200000,  # Claimed total value
                "current_price": 0,
                "savings": 200000,
                "discount_percentage": 100,
                "software_type": "development_suite",
                "license_type": "student",
                "target_audience": "students",
                "renewal_required": True,
                "platform_compatibility": ["Windows", "macOS", "Linux"],
                "included_tools": 50,
                "trial_period_days": 0,  # Permanent for students
                "support_level": "community",
                "tags": ["student", "development", "cloud credits", "domains"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Visual Studio Community",
                "description": "Free, full-featured IDE for students, open-source contributors, and individual developers",
                "url": "https://visualstudio.microsoft.com/vs/community/",
                "platform": "Microsoft",
                "category": "development_tools",
                "deal_type": "free_ide",
                "original_price": 250,  # Professional equivalent
                "current_price": 0,
                "savings": 250,
                "discount_percentage": 100,
                "software_type": "ide",
                "license_type": "community",
                "target_audience": "individual_developers",
                "renewal_required": False,
                "platform_compatibility": ["Windows", "macOS"],
                "included_tools": 25,
                "trial_period_days": 0,  # Permanent
                "support_level": "community",
                "tags": ["ide", "microsoft", "c#", "free"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "JetBrains Community Editions",
                "description": "Free community versions of IntelliJ IDEA, PyCharm, and other professional IDEs",
                "url": "https://www.jetbrains.com/community/",
                "platform": "JetBrains",
                "category": "development_tools",
                "deal_type": "community_edition",
                "original_price": 200,  # Professional version cost
                "current_price": 0,
                "savings": 200,
                "discount_percentage": 100,
                "software_type": "ide_suite",
                "license_type": "community",
                "target_audience": "developers",
                "renewal_required": False,
                "platform_compatibility": ["Windows", "macOS", "Linux"],
                "included_tools": 8,
                "trial_period_days": 0,
                "support_level": "community",
                "tags": ["jetbrains", "ide", "python", "java"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Google Workspace for Personal Use",
                "description": "Free Gmail, Drive (15GB), Docs, Sheets, and more for personal productivity",
                "url": "https://workspace.google.com/pricing.html",
                "platform": "Google",
                "category": "productivity",
                "deal_type": "freemium",
                "original_price": 72,  # Annual business cost
                "current_price": 0,
                "savings": 72,
                "discount_percentage": 100,
                "software_type": "office_suite",
                "license_type": "personal",
                "target_audience": "personal_users",
                "renewal_required": False,
                "platform_compatibility": ["Web", "Android", "iOS"],
                "included_tools": 15,
                "trial_period_days": 0,
                "support_level": "basic",
                "tags": ["google", "productivity", "cloud storage", "office"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Microsoft Office Online",
                "description": "Free web versions of Word, Excel, PowerPoint, and OneNote with OneDrive storage",
                "url": "https://www.office.com/",
                "platform": "Microsoft",
                "category": "productivity",
                "deal_type": "web_free",
                "original_price": 100,  # Annual subscription
                "current_price": 0,
                "savings": 100,
                "discount_percentage": 100,
                "software_type": "office_suite",
                "license_type": "web_free",
                "target_audience": "general_users",
                "renewal_required": False,
                "platform_compatibility": ["Web"],
                "included_tools": 8,
                "trial_period_days": 0,
                "support_level": "basic",
                "tags": ["microsoft office", "web apps", "onedrive", "free"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Notion Personal Plan",
                "description": "Free personal workspace for notes, databases, and project management",
                "url": "https://www.notion.so/pricing",
                "platform": "Notion",
                "category": "productivity",
                "deal_type": "freemium",
                "original_price": 48,  # Annual personal pro
                "current_price": 0,
                "savings": 48,
                "discount_percentage": 100,
                "software_type": "workspace",
                "license_type": "personal",
                "target_audience": "individuals",
                "renewal_required": False,
                "platform_compatibility": ["Web", "Windows", "macOS", "Android", "iOS"],
                "included_tools": 10,
                "trial_period_days": 0,
                "support_level": "community",
                "tags": ["notion", "notes", "databases", "productivity"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Figma Personal",
                "description": "Free design tool for UI/UX with collaborative features and unlimited personal files",
                "url": "https://www.figma.com/pricing/",
                "platform": "Figma",
                "category": "design_tools",
                "deal_type": "freemium",
                "original_price": 144,  # Annual professional
                "current_price": 0,
                "savings": 144,
                "discount_percentage": 100,
                "software_type": "design_tool",
                "license_type": "personal",
                "target_audience": "designers",
                "renewal_required": False,
                "platform_compatibility": ["Web", "Windows", "macOS"],
                "included_tools": 5,
                "trial_period_days": 0,
                "support_level": "community",
                "tags": ["figma", "ui design", "collaboration", "prototyping"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "GIMP Free Image Editor",
                "description": "Professional-grade image editing software, completely free and open source",
                "url": "https://www.gimp.org/",
                "platform": "GIMP",
                "category": "design_tools",
                "deal_type": "open_source",
                "original_price": 600,  # Photoshop equivalent
                "current_price": 0,
                "savings": 600,
                "discount_percentage": 100,
                "software_type": "image_editor",
                "license_type": "open_source",
                "target_audience": "designers",
                "renewal_required": False,
                "platform_compatibility": ["Windows", "macOS", "Linux"],
                "included_tools": 20,
                "trial_period_days": 0,
                "support_level": "community",
                "tags": [
                    "gimp",
                    "image editing",
                    "open source",
                    "photoshop alternative",
                ],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Blender 3D Creation Suite",
                "description": "Professional 3D creation software for modeling, animation, rendering, and more",
                "url": "https://www.blender.org/",
                "platform": "Blender Foundation",
                "category": "3d_software",
                "deal_type": "open_source",
                "original_price": 3000,  # Maya/3ds Max equivalent
                "current_price": 0,
                "savings": 3000,
                "discount_percentage": 100,
                "software_type": "3d_suite",
                "license_type": "open_source",
                "target_audience": "3d_artists",
                "renewal_required": False,
                "platform_compatibility": ["Windows", "macOS", "Linux"],
                "included_tools": 25,
                "trial_period_days": 0,
                "support_level": "community",
                "tags": ["blender", "3d modeling", "animation", "open source"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "LibreOffice Complete Suite",
                "description": "Full office suite with Writer, Calc, Impress, and more - completely free",
                "url": "https://www.libreoffice.org/",
                "platform": "The Document Foundation",
                "category": "productivity",
                "deal_type": "open_source",
                "original_price": 100,  # MS Office equivalent
                "current_price": 0,
                "savings": 100,
                "discount_percentage": 100,
                "software_type": "office_suite",
                "license_type": "open_source",
                "target_audience": "general_users",
                "renewal_required": False,
                "platform_compatibility": ["Windows", "macOS", "Linux"],
                "included_tools": 6,
                "trial_period_days": 0,
                "support_level": "community",
                "tags": ["libreoffice", "office suite", "open source", "documents"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Slack Free Plan",
                "description": "Team communication with 10,000 message history and essential integrations",
                "url": "https://slack.com/pricing",
                "platform": "Slack",
                "category": "collaboration",
                "deal_type": "freemium",
                "original_price": 96,  # Annual pro plan
                "current_price": 0,
                "savings": 96,
                "discount_percentage": 100,
                "software_type": "communication",
                "license_type": "freemium",
                "target_audience": "small_teams",
                "renewal_required": False,
                "platform_compatibility": ["Web", "Windows", "macOS", "Android", "iOS"],
                "included_tools": 10,
                "trial_period_days": 0,
                "support_level": "basic",
                "tags": [
                    "slack",
                    "team communication",
                    "collaboration",
                    "integrations",
                ],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Discord for Communities",
                "description": "Free voice, video, and text communication for communities and teams",
                "url": "https://discord.com/",
                "platform": "Discord",
                "category": "collaboration",
                "deal_type": "freemium",
                "original_price": 120,  # Annual Nitro
                "current_price": 0,
                "savings": 120,
                "discount_percentage": 100,
                "software_type": "communication",
                "license_type": "freemium",
                "target_audience": "communities",
                "renewal_required": False,
                "platform_compatibility": ["Web", "Windows", "macOS", "Android", "iOS"],
                "included_tools": 8,
                "trial_period_days": 0,
                "support_level": "community",
                "tags": ["discord", "voice chat", "communities", "gaming"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Canva Free Design Platform",
                "description": "Free graphic design tool with thousands of templates and design elements",
                "url": "https://www.canva.com/pricing/",
                "platform": "Canva",
                "category": "design_tools",
                "deal_type": "freemium",
                "original_price": 120,  # Annual pro
                "current_price": 0,
                "savings": 120,
                "discount_percentage": 100,
                "software_type": "design_tool",
                "license_type": "freemium",
                "target_audience": "non_designers",
                "renewal_required": False,
                "platform_compatibility": ["Web", "Android", "iOS"],
                "included_tools": 15,
                "trial_period_days": 0,
                "support_level": "basic",
                "tags": ["canva", "graphic design", "templates", "social media"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
            {
                "title": "Zoom Basic Plan",
                "description": "Free video conferencing for up to 100 participants with 40-minute limit",
                "url": "https://zoom.us/pricing",
                "platform": "Zoom",
                "category": "collaboration",
                "deal_type": "freemium",
                "original_price": 180,  # Annual pro
                "current_price": 0,
                "savings": 180,
                "discount_percentage": 100,
                "software_type": "video_conferencing",
                "license_type": "freemium",
                "target_audience": "small_teams",
                "renewal_required": False,
                "platform_compatibility": ["Web", "Windows", "macOS", "Android", "iOS"],
                "included_tools": 5,
                "trial_period_days": 0,
                "support_level": "basic",
                "tags": ["zoom", "video conferencing", "meetings", "webinars"],
                "created_date": datetime.now(timezone.utc).isoformat(),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "source": "Curated",
            },
        ]

        logger.info(f"Added {len(curated)} curated software deals")
        return curated

    def transform(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform software deals data."""
        logger.info("Starting software deals transformation...")

        deals = raw_data.get("deals", [])
        transformed_deals = []

        for deal in deals:
            try:
                # Clean up title
                title = deal["title"].strip()
                if len(title) > 150:
                    title = title[:147] + "..."

                # Calculate software value score
                software_score = self._calculate_software_value_score(deal)

                # Determine software tier
                software_tier = self._determine_software_tier(deal)

                transformed_deal = {
                    "title": title,
                    "description": deal.get("description", "")[:400],
                    "url": deal["url"],
                    "platform": deal["platform"],
                    "category": deal["category"],
                    "deal_type": deal["deal_type"],
                    "original_price": deal.get("original_price", 0),
                    "current_price": deal.get("current_price", 0),
                    "savings": deal.get("savings", 0),
                    "discount_percentage": deal.get("discount_percentage", 0),
                    "software_score": software_score,
                    "software_tier": software_tier,
                    "software_type": deal.get("software_type", "unknown"),
                    "license_type": deal.get("license_type", "unknown"),
                    "target_audience": deal.get("target_audience", "general"),
                    "renewal_required": deal.get("renewal_required", True),
                    "platform_compatibility": deal.get("platform_compatibility", []),
                    "included_tools": deal.get("included_tools", 1),
                    "trial_period_days": deal.get("trial_period_days", 0),
                    "support_level": deal.get("support_level", "basic"),
                    "tags": deal.get("tags", []),
                    "created_date": deal.get("created_date"),
                    "fetched_at": deal["fetched_at"],
                    "source": deal["source"],
                }

                transformed_deals.append(transformed_deal)

            except Exception as e:
                logger.warning(f"Error transforming software deal: {e}")
                continue

        # Sort by software score and savings
        transformed_deals.sort(
            key=lambda x: (x["software_score"], x["savings"]), reverse=True
        )

        logger.info(f"Transformed {len(transformed_deals)} software deals")
        return transformed_deals

    def _calculate_software_value_score(self, deal: Dict[str, Any]) -> float:
        """Calculate software value score for ranking deals."""
        score = 0.0

        # Platform quality weight
        platform = deal.get("platform", "").lower()
        if any(name in platform for name in ["microsoft", "google", "github"]):
            score += 5.0  # Major tech companies
        elif any(name in platform for name in ["jetbrains", "slack", "zoom"]):
            score += 4.5  # Professional tools
        elif any(name in platform for name in ["notion", "figma", "canva"]):
            score += 4.0  # Modern productivity tools
        else:
            score += 2.0

        # Deal type weight
        deal_type = deal.get("deal_type", "")
        if deal_type == "open_source":
            score += 5.0  # Completely free forever
        elif deal_type in ["student_pack", "free_ide"]:
            score += 4.5  # Great value programs
        elif deal_type in ["freemium", "community_edition"]:
            score += 4.0  # Good free tiers
        elif deal_type in ["web_free", "free_trial"]:
            score += 3.0  # Limited free access

        # License type bonus
        license_type = deal.get("license_type", "").lower()
        if license_type == "open_source":
            score += 2.0
        elif license_type in ["student", "community"]:
            score += 1.5
        elif license_type == "personal":
            score += 1.0

        # Platform compatibility bonus
        platforms = deal.get("platform_compatibility", [])
        if len(platforms) >= 4:
            score += 2.0  # Cross-platform
        elif len(platforms) >= 2:
            score += 1.0

        # Tools included bonus
        tools_count = deal.get("included_tools", 1)
        if tools_count > 20:
            score += 2.0
        elif tools_count > 10:
            score += 1.5
        elif tools_count > 5:
            score += 1.0

        # No renewal required bonus
        if not deal.get("renewal_required", True):
            score += 1.0

        # Savings consideration
        savings = deal.get("savings", 0)
        if savings > 1000:
            score += 3.0
        elif savings > 500:
            score += 2.0
        elif savings > 100:
            score += 1.0

        # Professional audience bonus
        audience = deal.get("target_audience", "").lower()
        if any(
            keyword in audience
            for keyword in ["developers", "designers", "professionals"]
        ):
            score += 1.0
        elif "students" in audience:
            score += 0.5

        return round(score, 2)

    def _determine_software_tier(self, deal: Dict[str, Any]) -> str:
        """Determine software quality tier."""
        license_type = deal.get("license_type", "").lower()
        platform = deal.get("platform", "").lower()
        savings = deal.get("savings", 0)
        tools_count = deal.get("included_tools", 1)

        # Enterprise tier indicators
        if savings > 1000 and tools_count > 20:
            return "enterprise"
        elif (
            any(name in platform for name in ["microsoft", "google"]) and savings > 500
        ):
            return "enterprise"

        # Professional tier indicators
        if license_type == "open_source" and savings > 500:
            return "professional"
        elif (
            any(name in platform for name in ["jetbrains", "github"]) and savings > 200
        ):
            return "professional"
        elif tools_count > 15:
            return "professional"

        # Standard tier indicators
        if license_type in ["community", "freemium"] and savings > 100:
            return "standard"
        elif tools_count > 5:
            return "standard"

        # Basic tier
        if savings > 50 or tools_count > 1:
            return "basic"

        return "limited"

    def load(self, transformed_data: List[Dict[str, Any]]) -> bool:
        """Load transformed software deals data to files."""
        try:
            # Ensure output directory exists
            output_dir = os.path.join(get_project_root(), "data", "deals")
            ensure_directories([output_dir])

            # Save as JSON
            json_path = os.path.join(output_dir, "software_deals.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(transformed_data, f, indent=2, ensure_ascii=False)

            # Save as CSV
            if transformed_data:
                csv_path = os.path.join(output_dir, "software_deals.csv")
                import pandas as pd

                df = pd.DataFrame(transformed_data)
                df.to_csv(csv_path, index=False, encoding="utf-8")

            logger.info(
                f"Successfully saved {len(transformed_data)} software deals to {output_dir}"
            )
            return True

        except Exception as e:
            logger.error(f"Error saving software deals data: {e}")
            return False


def main():
    """Main function to run the Software Deals ETL."""
    etl = SoftwareDealsETL()
    success = etl.run()

    if success:
        logger.info("Software Deals ETL completed successfully")
    else:
        logger.error("Software Deals ETL failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
