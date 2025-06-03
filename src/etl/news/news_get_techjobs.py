"""Tech Jobs ETL Module

This module fetches and processes technology job postings, salary trends,
and skill demand information from various job sites and APIs.

Usage:
    python src/etl/news/news_get_techjobs.py

Output:
    - JSON file: data/tech_jobs/tech_jobs_latest.json
    - CSV file: data/tech_jobs/tech_jobs_latest.csv
"""

import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Add the project root to the path to ensure imports work correctly
from src.utils.file_system import ensure_directories, get_project_root
from src.utils.logging import get_logger

# Initialize logger for this module
logger = get_logger("TechJobsETL")


def create_session() -> requests.Session:
    """Create a requests session with retry strategy and proper headers."""
    session = requests.Session()

    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set headers
    session.headers.update(
        {
            "User-Agent": "Watchtower-ETL/1.0 (Tech Jobs Analytics)",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
    )

    return session


def scrape_tech_job_sites(session: requests.Session) -> list[dict[str, Any]]:
    """Scrape tech job information from various sites.

    Args:
        session: Requests session with retry configuration

    Returns:
        List of job dictionaries
    """
    # For demonstration, we'll generate mock job data
    # In production, you'd integrate with job APIs or scrape job sites
    return generate_mock_tech_jobs()


def generate_mock_tech_jobs() -> list[dict[str, Any]]:
    """Generate mock tech job data for demonstration.
    In production, replace with actual job site APIs or scraping.

    Returns:
        List of mock job dictionaries
    """
    import random
    from datetime import datetime

    jobs = []

    # Job titles and their typical salary ranges
    job_data = {
        "Software Engineer": {
            "min_salary": 80000,
            "max_salary": 180000,
            "level": "mid",
        },
        "Senior Software Engineer": {
            "min_salary": 120000,
            "max_salary": 250000,
            "level": "senior",
        },
        "Frontend Developer": {
            "min_salary": 70000,
            "max_salary": 160000,
            "level": "mid",
        },
        "Backend Developer": {
            "min_salary": 85000,
            "max_salary": 190000,
            "level": "mid",
        },
        "Full Stack Developer": {
            "min_salary": 75000,
            "max_salary": 170000,
            "level": "mid",
        },
        "Data Scientist": {"min_salary": 90000, "max_salary": 200000, "level": "mid"},
        "Machine Learning Engineer": {
            "min_salary": 110000,
            "max_salary": 220000,
            "level": "senior",
        },
        "DevOps Engineer": {
            "min_salary": 95000,
            "max_salary": 200000,
            "level": "senior",
        },
        "Product Manager": {
            "min_salary": 100000,
            "max_salary": 210000,
            "level": "senior",
        },
        "Engineering Manager": {
            "min_salary": 140000,
            "max_salary": 280000,
            "level": "senior",
        },
        "Junior Developer": {
            "min_salary": 50000,
            "max_salary": 80000,
            "level": "junior",
        },
        "Python Developer": {"min_salary": 80000, "max_salary": 170000, "level": "mid"},
        "JavaScript Developer": {
            "min_salary": 75000,
            "max_salary": 160000,
            "level": "mid",
        },
        "React Developer": {"min_salary": 70000, "max_salary": 150000, "level": "mid"},
        "Node.js Developer": {
            "min_salary": 80000,
            "max_salary": 165000,
            "level": "mid",
        },
        "Cloud Architect": {
            "min_salary": 130000,
            "max_salary": 260000,
            "level": "senior",
        },
        "Cybersecurity Engineer": {
            "min_salary": 100000,
            "max_salary": 200000,
            "level": "senior",
        },
        "Mobile Developer": {"min_salary": 75000, "max_salary": 160000, "level": "mid"},
        "AI Engineer": {"min_salary": 120000, "max_salary": 240000, "level": "senior"},
        "Site Reliability Engineer": {
            "min_salary": 110000,
            "max_salary": 220000,
            "level": "senior",
        },
    }

    companies = [
        "Google",
        "Meta",
        "Amazon",
        "Microsoft",
        "Apple",
        "Netflix",
        "Uber",
        "Airbnb",
        "Stripe",
        "Snowflake",
        "Databricks",
        "OpenAI",
        "Anthropic",
        "Discord",
        "Figma",
        "Notion",
        "Slack",
        "Zoom",
        "Shopify",
        "Square",
        "PayPal",
        "Adobe",
        "Salesforce",
        "Twitter",
        "LinkedIn",
        "GitHub",
        "GitLab",
        "Atlassian",
        "Spotify",
        "Reddit",
    ]

    locations = [
        {"city": "San Francisco", "state": "CA", "country": "USA", "remote": False},
        {"city": "New York", "state": "NY", "country": "USA", "remote": False},
        {"city": "Seattle", "state": "WA", "country": "USA", "remote": False},
        {"city": "Austin", "state": "TX", "country": "USA", "remote": False},
        {"city": "Boston", "state": "MA", "country": "USA", "remote": False},
        {"city": "Remote", "state": "", "country": "USA", "remote": True},
        {"city": "London", "state": "", "country": "UK", "remote": False},
        {"city": "Berlin", "state": "", "country": "Germany", "remote": False},
        {"city": "Toronto", "state": "ON", "country": "Canada", "remote": False},
        {"city": "Remote", "state": "", "country": "Global", "remote": True},
    ]

    skills_by_role = {
        "Software Engineer": ["Python", "Java", "JavaScript", "SQL", "Git", "AWS"],
        "Frontend Developer": [
            "JavaScript",
            "React",
            "Vue.js",
            "CSS",
            "HTML",
            "TypeScript",
        ],
        "Backend Developer": [
            "Python",
            "Java",
            "Node.js",
            "SQL",
            "Docker",
            "Kubernetes",
        ],
        "Data Scientist": [
            "Python",
            "R",
            "SQL",
            "Machine Learning",
            "Statistics",
            "Pandas",
        ],
        "DevOps Engineer": [
            "AWS",
            "Docker",
            "Kubernetes",
            "Terraform",
            "Jenkins",
            "Python",
        ],
        "Machine Learning Engineer": [
            "Python",
            "TensorFlow",
            "PyTorch",
            "MLOps",
            "SQL",
            "AWS",
        ],
    }

    # Generate job postings
    for i in range(100):
        job_title = random.choice(list(job_data.keys()))
        job_info = job_data[job_title]
        company = random.choice(companies)
        location = random.choice(locations)

        # Generate salary within range
        min_sal = job_info["min_salary"]
        max_sal = job_info["max_salary"]
        salary = random.randint(min_sal, max_sal)

        # Posted date (within last 30 days)
        days_ago = random.randint(0, 30)
        posted_date = datetime.now() - timedelta(days=days_ago)

        # Get relevant skills
        base_skills = skills_by_role.get(job_title, ["Programming", "Problem Solving"])
        required_skills = random.sample(
            base_skills, min(len(base_skills), random.randint(3, 6))
        )

        # Generate job description
        description = (
            f"We are looking for a talented {job_title} to join our {company} team. "
            f"You will be working on exciting projects involving {', '.join(required_skills[:3])}. "
            f"This role offers competitive compensation and great benefits."
        )

        job = {
            "id": f"job_{i}_{int(time.time())}",
            "title": job_title,
            "company": company,
            "location": {
                "city": location["city"],
                "state": location["state"],
                "country": location["country"],
                "remote": location["remote"],
            },
            "location_string": f"{location['city']}, {location['state']}"
            if location["state"]
            else location["city"],
            "salary": {
                "amount": salary,
                "currency": "USD",
                "period": "yearly",
                "min_range": min_sal,
                "max_range": max_sal,
            },
            "experience_level": job_info["level"],
            "employment_type": random.choice(["full_time", "contract", "part_time"]),
            "remote_option": location["remote"] or random.choice([True, False]),
            "description": description,
            "required_skills": required_skills,
            "posted_date": posted_date.isoformat(),
            "application_deadline": (posted_date + timedelta(days=30)).isoformat(),
            "benefits": random.sample(
                [
                    "Health Insurance",
                    "Dental Insurance",
                    "401k",
                    "Stock Options",
                    "Flexible Hours",
                    "Remote Work",
                    "Paid Time Off",
                    "Professional Development",
                ],
                random.randint(3, 6),
            ),
            "job_source": random.choice(
                ["LinkedIn", "Indeed", "AngelList", "Stack Overflow", "Company Website"]
            ),
            "fetched_at": datetime.now().isoformat(),
        }

        jobs.append(job)

    return jobs


def process_tech_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Process and enrich tech job data with additional metrics and categorization.

    Args:
        jobs: List of job dictionaries

    Returns:
        List of processed and enriched job data
    """
    logger.info(f"Processing {len(jobs)} tech job postings")

    processed_jobs = []
    current_time = datetime.now()

    for job in jobs:
        try:
            # Parse posted date
            posted_date_str = job.get("posted_date")
            if posted_date_str:
                posted_date = datetime.fromisoformat(
                    posted_date_str.replace("Z", "+00:00")
                )
                days_since_posted = (
                    current_time.replace(tzinfo=posted_date.tzinfo) - posted_date
                ).days
            else:
                days_since_posted = 0

            # Salary analysis
            salary_info = job.get("salary", {})
            salary_amount = salary_info.get("amount", 0)

            # Categorize salary level
            if salary_amount >= 200000:
                salary_level = "very_high"
            elif salary_amount >= 150000:
                salary_level = "high"
            elif salary_amount >= 100000:
                salary_level = "medium_high"
            elif salary_amount >= 80000:
                salary_level = "medium"
            elif salary_amount >= 60000:
                salary_level = "low_medium"
            else:
                salary_level = "low"

            # Location analysis
            location = job.get("location", {})
            is_remote = job.get("remote_option", False)
            city = location.get("city", "")

            # Tech hub classification
            tech_hubs = {
                "San Francisco": "tier_1",
                "New York": "tier_1",
                "Seattle": "tier_1",
                "Austin": "tier_2",
                "Boston": "tier_2",
                "Los Angeles": "tier_2",
                "Chicago": "tier_2",
                "Denver": "tier_3",
                "Atlanta": "tier_3",
                "Remote": "remote",
            }

            location_tier = tech_hubs.get(city, "other")

            # Skills analysis
            required_skills = job.get("required_skills", [])

            # Hot skills in 2024/2025
            hot_skills = [
                "AI",
                "Machine Learning",
                "React",
                "Python",
                "AWS",
                "Kubernetes",
                "TypeScript",
                "Go",
                "Rust",
            ]
            hot_skills_count = len(
                [skill for skill in required_skills if skill in hot_skills]
            )

            # Experience level scoring
            experience_level = job.get("experience_level", "mid")
            exp_score = {
                "junior": 1,
                "mid": 2,
                "senior": 3,
                "staff": 4,
                "principal": 5,
            }.get(experience_level, 2)

            # Calculate attractiveness score
            attractiveness_score = 0

            # Salary component
            attractiveness_score += min(salary_amount / 20000, 10)

            # Remote work bonus
            if is_remote:
                attractiveness_score += 2

            # Hot skills bonus
            attractiveness_score += hot_skills_count * 0.5

            # Company tier (simplified)
            company = job.get("company", "")
            if company in ["Google", "Meta", "Amazon", "Microsoft", "Apple", "Netflix"]:
                attractiveness_score += 3
            elif company in ["Uber", "Airbnb", "Stripe", "OpenAI", "Anthropic"]:
                attractiveness_score += 2

            # Location tier bonus
            if location_tier == "tier_1":
                attractiveness_score += 2
            elif location_tier == "tier_2":
                attractiveness_score += 1

            # Freshness bonus
            if days_since_posted <= 7:
                attractiveness_score += 1

            # Job category classification
            title_lower = job.get("title", "").lower()
            if any(
                word in title_lower
                for word in ["ai", "machine learning", "ml", "data scientist"]
            ):
                job_category = "ai_ml"
            elif any(
                word in title_lower for word in ["frontend", "react", "vue", "angular"]
            ):
                job_category = "frontend"
            elif any(word in title_lower for word in ["backend", "api", "server"]):
                job_category = "backend"
            elif any(word in title_lower for word in ["full stack", "fullstack"]):
                job_category = "fullstack"
            elif any(
                word in title_lower for word in ["devops", "site reliability", "sre"]
            ):
                job_category = "devops"
            elif any(word in title_lower for word in ["mobile", "ios", "android"]):
                job_category = "mobile"
            elif any(word in title_lower for word in ["manager", "lead", "director"]):
                job_category = "management"
            elif any(word in title_lower for word in ["security", "cybersecurity"]):
                job_category = "security"
            else:
                job_category = "general"

            # Market demand estimation (simplified)
            demand_keywords = [
                "urgent",
                "immediate",
                "asap",
                "multiple positions",
                "hiring now",
            ]
            description = job.get("description", "").lower()
            has_urgency = any(keyword in description for keyword in demand_keywords)

            processed_job = {
                **job,
                "days_since_posted": days_since_posted,
                "salary_level": salary_level,
                "location_tier": location_tier,
                "hot_skills_count": hot_skills_count,
                "experience_score": exp_score,
                "attractiveness_score": round(attractiveness_score, 2),
                "job_category": job_category,
                "has_urgency_indicators": has_urgency,
                "is_fresh": days_since_posted <= 7,
                "platform": "tech_jobs",
                "skills_count": len(required_skills),
                "benefits_count": len(job.get("benefits", [])),
            }

            processed_jobs.append(processed_job)

        except Exception as e:
            logger.warning(f"Error processing job {job.get('id', 'unknown')}: {e}")
            continue

    # Sort by attractiveness score
    processed_jobs.sort(key=lambda x: x.get("attractiveness_score", 0), reverse=True)

    logger.info(f"Successfully processed {len(processed_jobs)} tech jobs")
    return processed_jobs


def analyze_job_market(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze job market trends and statistics.

    Args:
        jobs: List of processed jobs

    Returns:
        Market analysis dictionary
    """
    if not jobs:
        return {}

    from collections import Counter

    # Salary analysis
    salaries = [
        job.get("salary", {}).get("amount", 0)
        for job in jobs
        if job.get("salary", {}).get("amount", 0) > 0
    ]
    avg_salary = sum(salaries) / len(salaries) if salaries else 0

    # Skills demand
    all_skills = []
    for job in jobs:
        all_skills.extend(job.get("required_skills", []))

    top_skills = Counter(all_skills).most_common(15)

    # Location trends
    locations = [job.get("location_string", "Unknown") for job in jobs]
    top_locations = Counter(locations).most_common(10)

    # Company distribution
    companies = [job.get("company", "Unknown") for job in jobs]
    top_companies = Counter(companies).most_common(10)

    # Remote work trends
    remote_jobs = len([job for job in jobs if job.get("remote_option", False)])
    remote_percentage = (remote_jobs / len(jobs)) * 100 if jobs else 0

    # Experience level distribution
    exp_levels = [job.get("experience_level", "Unknown") for job in jobs]
    exp_distribution = Counter(exp_levels)

    # Category distribution
    categories = [job.get("job_category", "Unknown") for job in jobs]
    category_distribution = Counter(categories)

    return {
        "total_jobs": len(jobs),
        "average_salary": round(avg_salary, 2),
        "salary_range": {
            "min": min(salaries) if salaries else 0,
            "max": max(salaries) if salaries else 0,
            "median": sorted(salaries)[len(salaries) // 2] if salaries else 0,
        },
        "top_skills": top_skills,
        "top_locations": top_locations,
        "top_companies": top_companies,
        "remote_work": {
            "total_remote_jobs": remote_jobs,
            "percentage": round(remote_percentage, 1),
        },
        "experience_distribution": dict(exp_distribution),
        "category_distribution": dict(category_distribution),
        "analysis_date": datetime.now().isoformat(),
    }


def save_data(
    data: list[dict[str, Any]], analysis: dict[str, Any], output_dir: str
) -> dict[str, str]:
    """Save processed data to JSON and CSV files.

    Args:
        data: List of processed jobs
        analysis: Market analysis data
        output_dir: Directory to save files

    Returns:
        Dictionary with file paths
    """
    ensure_directories([output_dir])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # File paths
    json_file = os.path.join(output_dir, f"tech_jobs_{timestamp}.json")
    csv_file = os.path.join(output_dir, f"tech_jobs_{timestamp}.csv")
    analysis_file = os.path.join(output_dir, f"tech_jobs_analysis_{timestamp}.json")
    latest_json = os.path.join(output_dir, "tech_jobs_latest.json")
    latest_csv = os.path.join(output_dir, "tech_jobs_latest.csv")
    latest_analysis = os.path.join(output_dir, "tech_jobs_analysis_latest.json")

    # Save jobs data
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    # Save analysis
    with open(analysis_file, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)

    with open(latest_analysis, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)

    # Save CSV
    if data:
        # Flatten nested data for CSV
        csv_data = []
        for item in data:
            flat_item = {**item}

            # Flatten nested objects
            location_data = flat_item.pop("location", {})
            salary_data = flat_item.pop("salary", {})

            flat_item.update({f"location_{k}": v for k, v in location_data.items()})
            flat_item.update({f"salary_{k}": v for k, v in salary_data.items()})

            # Convert lists to strings
            if isinstance(flat_item.get("required_skills"), list):
                flat_item["required_skills"] = ", ".join(flat_item["required_skills"])
            if isinstance(flat_item.get("benefits"), list):
                flat_item["benefits"] = ", ".join(flat_item["benefits"])

            csv_data.append(flat_item)

        fieldnames = csv_data[0].keys() if csv_data else []

        for csv_path in [csv_file, latest_csv]:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_data)

    logger.info(f"Data saved to {json_file}, {csv_file}, and {analysis_file}")

    return {
        "json_file": json_file,
        "csv_file": csv_file,
        "analysis_file": analysis_file,
        "latest_json": latest_json,
        "latest_csv": latest_csv,
        "latest_analysis": latest_analysis,
    }


def main():
    """Main function to run the Tech Jobs ETL process."""
    logger.info("Starting Tech Jobs ETL process")

    try:
        # Setup
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data", "tech_jobs")
        session = create_session()

        # Fetch data
        logger.info("Fetching tech job data")
        jobs = scrape_tech_job_sites(session)

        if not jobs:
            logger.warning("No jobs fetched. Exiting.")
            return

        # Process data
        logger.info("Processing and enriching job data")
        processed_jobs = process_tech_jobs(jobs)

        # Analyze market
        logger.info("Analyzing job market trends")
        market_analysis = analyze_job_market(processed_jobs)

        # Save data
        file_paths = save_data(processed_jobs, market_analysis, output_dir)

        # Summary
        total_jobs = len(processed_jobs)
        high_salary_jobs = len(
            [
                j
                for j in processed_jobs
                if j.get("salary_level") in ["high", "very_high"]
            ]
        )
        remote_jobs = len([j for j in processed_jobs if j.get("remote_option", False)])

        logger.info("Tech Jobs ETL completed successfully!")
        logger.info(f"Total jobs processed: {total_jobs}")
        logger.info(f"High salary jobs: {high_salary_jobs}")
        logger.info(f"Remote jobs: {remote_jobs}")
        logger.info(f"Average salary: ${market_analysis.get('average_salary', 0):,.2f}")
        logger.info(f"Files saved: {list(file_paths.values())}")

        # Print top trends
        if market_analysis.get("top_skills"):
            top_skills = market_analysis["top_skills"][:5]
            logger.info(f"Top in-demand skills: {[skill[0] for skill in top_skills]}")

    except Exception as e:
        logger.error(f"Tech Jobs ETL failed: {e}")
        raise


if __name__ == "__main__":
    main()
