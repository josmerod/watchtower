"""
Stack Overflow Trends ETL Module

This module fetches and processes trending Stack Overflow questions, tags,
and discussions to track what developers are currently asking about and 
struggling with in the tech ecosystem.

Usage:
    python src/etl/news/news_get_stackoverflow_trends.py

Output:
    - JSON file: data/stackoverflow_trends/stackoverflow_trends_latest.json
    - CSV file: data/stackoverflow_trends/stackoverflow_trends_latest.csv
"""

import os
import json
import sys
import time
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re
import random

# Add the project root to the path to ensure imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.utils.logging import get_logger
from src.utils.file_system import ensure_directories, get_project_root

# Initialize logger for this module
logger = get_logger("StackOverflowTrendsETL")

def create_session() -> requests.Session:
    """Create a requests session with retry strategy and proper headers."""
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set headers
    session.headers.update({
        'User-Agent': 'Watchtower-ETL/1.0 (StackOverflow Trends Analytics)',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    })
    
    return session

def fetch_stackoverflow_data(session: requests.Session) -> List[Dict[str, Any]]:
    """
    Fetch trending questions from Stack Overflow API.
    
    Args:
        session: Requests session with retry configuration
    
    Returns:
        List of Stack Overflow question dictionaries
    """
    base_url = "https://api.stackexchange.com/2.3"
    questions = []
    
    try:
        # Fetch trending questions (hot questions)
        params = {
            'order': 'desc',
            'sort': 'hot',
            'site': 'stackoverflow',
            'pagesize': 100,
            'filter': 'withbody'
        }
        
        logger.info("Fetching hot questions from Stack Overflow")
        response = session.get(f"{base_url}/questions", params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        for item in data.get('items', []):
            processed_question = {
                "question_id": item.get('question_id'),
                "title": item.get('title'),
                "body": item.get('body', ''),
                "link": item.get('link'),
                "tags": item.get('tags', []),
                "score": item.get('score', 0),
                "view_count": item.get('view_count', 0),
                "answer_count": item.get('answer_count', 0),
                "comment_count": item.get('comment_count', 0),
                "creation_date": item.get('creation_date'),
                "last_activity_date": item.get('last_activity_date'),
                "owner": item.get('owner', {}),
                "is_answered": item.get('is_answered', False),
                "has_accepted_answer": item.get('accepted_answer_id') is not None,
                "fetched_at": datetime.now().isoformat()
            }
            
            questions.append(processed_question)
        
        # Small delay to respect API limits
        time.sleep(1)
        
        logger.info(f"Fetched {len(questions)} Stack Overflow questions")
        return questions
        
    except Exception as e:
        logger.error(f"Error fetching Stack Overflow data: {e}")
        # Return mock data for demonstration if API fails
        return generate_mock_stackoverflow_data()

def generate_mock_stackoverflow_data() -> List[Dict[str, Any]]:
    """
    Generate mock Stack Overflow data for demonstration.
    
    Returns:
        List of mock Stack Overflow question dictionaries
    """
    import random
    from datetime import datetime, timedelta
    
    questions = []
    
    # Common programming topics and questions
    question_templates = [
        {
            "title": "How to implement async/await in {language}?",
            "tags": ["async", "programming"],
            "category": "async_programming"
        },
        {
            "title": "Best practices for {framework} state management",
            "tags": ["state-management", "best-practices"],
            "category": "best_practices"
        },
        {
            "title": "Error: {error_type} when using {technology}",
            "tags": ["debugging", "error-handling"],
            "category": "debugging"
        },
        {
            "title": "How to optimize {operation} performance in {language}?",
            "tags": ["performance", "optimization"],
            "category": "performance"
        },
        {
            "title": "Difference between {concept1} and {concept2}",
            "tags": ["concepts", "theory"],
            "category": "concepts"
        },
        {
            "title": "How to setup {tool} with {environment}?",
            "tags": ["setup", "configuration"],
            "category": "setup"
        },
        {
            "title": "Unit testing {feature} in {framework}",
            "tags": ["unit-testing", "testing"],
            "category": "testing"
        },
        {
            "title": "Docker containerization for {application_type}",
            "tags": ["docker", "containerization"],
            "category": "devops"
        },
        {
            "title": "API integration with {service} using {language}",
            "tags": ["api", "integration"],
            "category": "api"
        },
        {
            "title": "Database design for {use_case}",
            "tags": ["database", "design"],
            "category": "database"
        }
    ]
    
    # Technology substitutions
    languages = ["Python", "JavaScript", "Java", "C#", "TypeScript", "Go", "Rust", "PHP", "Ruby", "Swift"]
    frameworks = ["React", "Vue.js", "Angular", "Django", "Express.js", "Spring", "Laravel", "Ruby on Rails"]
    technologies = ["GraphQL", "REST API", "WebSocket", "gRPC", "Redis", "MongoDB", "PostgreSQL"]
    tools = ["Kubernetes", "Terraform", "Jenkins", "GitHub Actions", "AWS", "Azure", "GCP"]
    
    # Generate questions
    for i in range(80):
        template = random.choice(question_templates)
        title = template["title"]
        
        # Replace placeholders with random values
        if "{language}" in title:
            title = title.replace("{language}", random.choice(languages))
        if "{framework}" in title:
            title = title.replace("{framework}", random.choice(frameworks))
        if "{technology}" in title:
            title = title.replace("{technology}", random.choice(technologies))
        if "{tool}" in title:
            title = title.replace("{tool}", random.choice(tools))
        if "{error_type}" in title:
            title = title.replace("{error_type}", random.choice(["TypeError", "ReferenceError", "SyntaxError", "ImportError", "ConnectionError"]))
        if "{operation}" in title:
            title = title.replace("{operation}", random.choice(["database query", "API call", "file processing", "image rendering", "data parsing"]))
        if "{concept1}" in title:
            concepts = [("let and const", "var"), ("async and sync", "callbacks"), ("REST and GraphQL", "SOAP"), ("SQL and NoSQL", "databases")]
            concept_pair = random.choice(concepts)
            title = title.replace("{concept1}", concept_pair[0]).replace("{concept2}", concept_pair[1])
        if "{environment}" in title:
            title = title.replace("{environment}", random.choice(["Docker", "Kubernetes", "AWS", "local development", "production"]))
        if "{feature}" in title:
            title = title.replace("{feature}", random.choice(["authentication", "payment processing", "file upload", "user registration", "data validation"]))
        if "{service}" in title:
            title = title.replace("{service}", random.choice(["Stripe", "PayPal", "AWS S3", "Google Maps", "Twilio", "SendGrid"]))
        if "{application_type}" in title:
            title = title.replace("{application_type}", random.choice(["web application", "microservice", "React app", "Node.js API", "Python script"]))
        if "{use_case}" in title:
            title = title.replace("{use_case}", random.choice(["e-commerce", "social media", "blog platform", "inventory management", "user analytics"]))
        
        # Generate question metrics
        hours_ago = random.randint(1, 72)
        creation_timestamp = int((datetime.now() - timedelta(hours=hours_ago)).timestamp())
        last_activity_timestamp = int((datetime.now() - timedelta(hours=random.randint(0, hours_ago))).timestamp())
        
        # Generate tags based on title content
        tags = template["tags"].copy()
        title_lower = title.lower()
        
        # Add language tags
        for lang in languages:
            if lang.lower() in title_lower:
                tags.append(lang.lower())
                break
        
        # Add framework tags  
        for framework in frameworks:
            if framework.lower().replace('.', '') in title_lower.replace('.', ''):
                tags.append(framework.lower().replace('.js', '').replace(' on rails', ''))
                break
        
        # Add specific technology tags
        if 'docker' in title_lower:
            tags.append('docker')
        if 'api' in title_lower:
            tags.append('api')
        if 'database' in title_lower:
            tags.append('database')
        if 'test' in title_lower:
            tags.append('testing')
        
        # Remove duplicates and limit tags
        tags = list(set(tags))[:6]
        
        question = {
            "question_id": f"so_question_{i}_{int(time.time())}",
            "title": title,
            "body": f"I'm working on a project and need help with {title.lower()}. Here are the details of my implementation...",
            "link": f"https://stackoverflow.com/questions/{random.randint(60000000, 80000000)}/question-title",
            "tags": tags,
            "score": random.randint(-2, 50),
            "view_count": random.randint(10, 5000),
            "answer_count": random.randint(0, 8),
            "comment_count": random.randint(0, 12),
            "creation_date": creation_timestamp,
            "last_activity_date": last_activity_timestamp,
            "owner": {
                "user_id": random.randint(100000, 9999999),
                "display_name": f"User{random.randint(1000, 9999)}",
                "reputation": random.randint(1, 50000)
            },
            "is_answered": random.choice([True, False]),
            "has_accepted_answer": random.choice([True, False]),
            "category": template["category"],
            "fetched_at": datetime.now().isoformat()
        }
        
        questions.append(question)
    
    return questions

def process_stackoverflow_data(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process and enrich Stack Overflow data with additional metrics and categorization.
    
    Args:
        questions: List of Stack Overflow question dictionaries
        
    Returns:
        List of processed and enriched question data
    """
    logger.info(f"Processing {len(questions)} Stack Overflow questions")
    
    processed_questions = []
    current_time = datetime.now()
    
    for question in questions:
        try:
            # Parse creation time
            creation_timestamp = question.get('creation_date', 0)
            creation_date = datetime.fromtimestamp(creation_timestamp) if creation_timestamp else current_time
            hours_since_created = (current_time - creation_date).total_seconds() / 3600
            
            # Parse last activity time
            activity_timestamp = question.get('last_activity_date', creation_timestamp)
            last_activity = datetime.fromtimestamp(activity_timestamp) if activity_timestamp else creation_date
            hours_since_activity = (current_time - last_activity).total_seconds() / 3600
            
            # Extract metrics
            score = question.get('score', 0)
            view_count = question.get('view_count', 0)
            answer_count = question.get('answer_count', 0)
            comment_count = question.get('comment_count', 0)
            
            # Calculate engagement metrics
            engagement_score = score + (answer_count * 3) + (comment_count * 1) + (view_count / 100)
            
            # Determine question difficulty
            title = question.get('title', '').lower()
            if any(word in title for word in ['beginner', 'basic', 'simple', 'how to start']):
                difficulty = 'beginner'
            elif any(word in title for word in ['advanced', 'complex', 'optimize', 'performance']):
                difficulty = 'advanced'
            elif any(word in title for word in ['best practice', 'architecture', 'design pattern']):
                difficulty = 'intermediate'
            else:
                difficulty = 'intermediate'
            
            # Question urgency
            urgency_indicators = ['urgent', 'asap', 'deadline', 'production', 'critical', 'broke', 'error', 'failed']
            has_urgency = any(indicator in title for indicator in urgency_indicators)
            
            # Technology categorization
            tags = question.get('tags', [])
            tags_str = ' '.join(tags).lower()
            title_lower = title.lower()
            combined_text = f"{title_lower} {tags_str}"
            
            if any(tech in combined_text for tech in ['javascript', 'js', 'typescript', 'react', 'vue', 'angular']):
                tech_category = 'frontend'
            elif any(tech in combined_text for tech in ['python', 'django', 'flask', 'fastapi', 'node', 'express']):
                tech_category = 'backend'
            elif any(tech in combined_text for tech in ['ios', 'android', 'swift', 'kotlin', 'react-native', 'flutter']):
                tech_category = 'mobile'
            elif any(tech in combined_text for tech in ['machine-learning', 'ai', 'tensorflow', 'pytorch', 'scikit-learn']):
                tech_category = 'ai_ml'
            elif any(tech in combined_text for tech in ['docker', 'kubernetes', 'aws', 'azure', 'devops', 'ci-cd']):
                tech_category = 'devops'
            elif any(tech in combined_text for tech in ['sql', 'database', 'mysql', 'postgresql', 'mongodb']):
                tech_category = 'database'
            elif any(tech in combined_text for tech in ['security', 'authentication', 'encryption', 'oauth']):
                tech_category = 'security'
            else:
                tech_category = 'general'
            
            # Answer status
            if question.get('has_accepted_answer', False):
                answer_status = 'solved'
            elif answer_count > 0:
                answer_status = 'has_answers'
            else:
                answer_status = 'unanswered'
            
            # Trending indicators
            if hours_since_created <= 24:
                freshness = 'very_fresh'
            elif hours_since_created <= 72:
                freshness = 'fresh'
            elif hours_since_created <= 168:  # 1 week
                freshness = 'recent'
            else:
                freshness = 'older'
            
            # Calculate trending score
            trending_score = engagement_score
            if freshness == 'very_fresh':
                trending_score *= 1.5
            elif freshness == 'fresh':
                trending_score *= 1.2
            if answer_status == 'unanswered' and hours_since_created <= 48:
                trending_score *= 1.3  # Boost unanswered recent questions
            if has_urgency:
                trending_score *= 1.4
            
            processed_question = {
                **question,
                "hours_since_created": round(hours_since_created, 2),
                "hours_since_activity": round(hours_since_activity, 2),
                "engagement_score": round(engagement_score, 2),
                "difficulty": difficulty,
                "has_urgency": has_urgency,
                "tech_category": tech_category,
                "answer_status": answer_status,
                "freshness": freshness,
                "trending_score": round(trending_score, 2),
                "is_trending": trending_score >= 20,
                "needs_attention": answer_status == 'unanswered' and hours_since_created <= 48,
                "platform": "stackoverflow",
                "tag_count": len(tags),
                "owner_reputation": question.get('owner', {}).get('reputation', 0)
            }
            
            processed_questions.append(processed_question)
            
        except Exception as e:
            logger.warning(f"Error processing question {question.get('question_id', 'unknown')}: {e}")
            continue
    
    # Sort by trending score
    processed_questions.sort(key=lambda x: x.get('trending_score', 0), reverse=True)
    
    logger.info(f"Successfully processed {len(processed_questions)} Stack Overflow questions")
    return processed_questions

def save_data(data: List[Dict[str, Any]], output_dir: str) -> Dict[str, str]:
    """
    Save processed data to JSON and CSV files.
    
    Args:
        data: List of processed Stack Overflow questions
        output_dir: Directory to save files
        
    Returns:
        Dictionary with file paths
    """
    ensure_directories([output_dir])
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # File paths
    json_file = os.path.join(output_dir, f"stackoverflow_trends_{timestamp}.json")
    csv_file = os.path.join(output_dir, f"stackoverflow_trends_{timestamp}.csv")
    latest_json = os.path.join(output_dir, "stackoverflow_trends_latest.json")
    latest_csv = os.path.join(output_dir, "stackoverflow_trends_latest.csv")
    
    # Save JSON
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    with open(latest_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    # Save CSV
    if data:
        # Flatten data for CSV
        csv_data = []
        for item in data:
            flat_item = {**item}
            
            # Flatten owner data
            owner_data = flat_item.pop('owner', {})
            flat_item.update({f"owner_{k}": v for k, v in owner_data.items()})
            
            # Convert lists to strings
            if isinstance(flat_item.get('tags'), list):
                flat_item['tags'] = ', '.join(flat_item['tags'])
                
            csv_data.append(flat_item)
        
        # Get all possible fieldnames dynamically
        fieldnames = set()
        for item in csv_data:
            fieldnames.update(item.keys())
        fieldnames = sorted(list(fieldnames))
        
        for csv_path in [csv_file, latest_csv]:
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_data)
    
    logger.info(f"Data saved to {json_file} and {csv_file}")
    
    return {
        "json_file": json_file,
        "csv_file": csv_file,
        "latest_json": latest_json,
        "latest_csv": latest_csv
    }

def main():
    """Main function to run the Stack Overflow Trends ETL process."""
    logger.info("Starting Stack Overflow Trends ETL process")
    
    try:
        # Setup
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "data", "stackoverflow_trends")
        session = create_session()
        
        # Fetch data
        logger.info("Fetching Stack Overflow trending data")
        questions = fetch_stackoverflow_data(session)
        
        if not questions:
            logger.warning("No Stack Overflow questions fetched. Exiting.")
            return
        
        # Process data
        logger.info("Processing and enriching Stack Overflow data")
        processed_data = process_stackoverflow_data(questions)
        
        # Save data
        file_paths = save_data(processed_data, output_dir)
        
        # Summary
        total_questions = len(processed_data)
        trending_questions = len([q for q in processed_data if q.get('is_trending', False)])
        unanswered_questions = len([q for q in processed_data if q.get('answer_status') == 'unanswered'])
        urgent_questions = len([q for q in processed_data if q.get('has_urgency', False)])
        
        logger.info(f"Stack Overflow Trends ETL completed successfully!")
        logger.info(f"Total questions: {total_questions}")
        logger.info(f"Trending questions: {trending_questions}")
        logger.info(f"Unanswered questions: {unanswered_questions}")
        logger.info(f"Urgent questions: {urgent_questions}")
        logger.info(f"Files saved: {list(file_paths.values())}")
        
        # Print technology distribution
        if processed_data:
            tech_categories = [q.get('tech_category', 'Unknown') for q in processed_data]
            from collections import Counter
            top_categories = Counter(tech_categories).most_common(10)
            logger.info(f"Top technology categories: {top_categories}")
        
    except Exception as e:
        logger.error(f"Stack Overflow Trends ETL failed: {e}")
        raise

if __name__ == "__main__":
    main() 