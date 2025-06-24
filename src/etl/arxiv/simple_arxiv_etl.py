#!/usr/bin/env python3
"""
Simple ArXiv ETL - fetches papers from ArXiv API without external dependencies
"""

import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
from urllib.parse import urlencode, quote
import xml.etree.ElementTree as ET

import requests
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SimpleArxivETL")

# ArXiv API configuration
ARXIV_API_BASE = "http://export.arxiv.org/api/query"
ARXIV_NAMESPACE = {"atom": "http://www.w3.org/2005/Atom"}

# Search queries for different AI/ML topics
ARXIV_QUERIES = {
    "machine_learning": "cat:cs.LG OR cat:stat.ML",
    "computer_vision": "cat:cs.CV",
    "artificial_intelligence": "cat:cs.AI",
    "natural_language": "cat:cs.CL",
    "neural_networks": "all:neural AND (cat:cs.LG OR cat:cs.AI OR cat:cs.CV OR cat:cs.CL)",
    "deep_learning": "all:\"deep learning\" AND (cat:cs.LG OR cat:cs.AI OR cat:cs.CV OR cat:cs.CL)",
}

def build_arxiv_query(search_query: str, max_results: int = 50, days_back: int = 7) -> str:
    """Build ArXiv API query URL."""
    # Calculate date range for recent papers
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    # Format dates for ArXiv (YYYYMMDD format)
    date_filter = f"submittedDate:[{start_date.strftime('%Y%m%d')}0000 TO {end_date.strftime('%Y%m%d')}2359]"
    
    # Combine search query with date filter
    full_query = f"({search_query}) AND {date_filter}"
    
    params = {
        'search_query': full_query,
        'start': 0,
        'max_results': max_results,
        'sortBy': 'submittedDate',
        'sortOrder': 'descending'
    }
    
    return f"{ARXIV_API_BASE}?{urlencode(params)}"

def fetch_arxiv_papers(category: str, search_query: str, max_results: int = 50) -> List[Dict[str, Any]]:
    """Fetch papers from ArXiv API."""
    try:
        query_url = build_arxiv_query(search_query, max_results)
        logger.info(f"Fetching {category} papers from ArXiv API")
        logger.info(f"Query URL: {query_url}")
        
        response = requests.get(query_url, timeout=30)
        response.raise_for_status()
        
        # Parse XML response
        root = ET.fromstring(response.content)
        
        papers = []
        
        # Find all entry elements (papers)
        entries = root.findall('.//atom:entry', ARXIV_NAMESPACE)
        logger.info(f"Found {len(entries)} entries in API response")
        
        for entry in entries:
            try:
                paper = parse_arxiv_entry(entry, category)
                if paper:
                    papers.append(paper)
            except Exception as e:
                logger.error(f"Error parsing paper entry: {e}")
                continue
        
        logger.info(f"Successfully parsed {len(papers)} papers for {category}")
        return papers
        
    except Exception as e:
        logger.error(f"Error fetching {category} papers: {e}")
        return []

def parse_arxiv_entry(entry: ET.Element, category: str) -> Dict[str, Any]:
    """Parse a single ArXiv API entry."""
    paper = {}
    
    # Extract title
    title_elem = entry.find('atom:title', ARXIV_NAMESPACE)
    if title_elem is not None:
        # Clean up title (ArXiv often has extra whitespace)
        title = re.sub(r'\s+', ' ', title_elem.text.strip())
        paper['title'] = title
    else:
        return None
    
    # Extract abstract/summary
    summary_elem = entry.find('atom:summary', ARXIV_NAMESPACE)
    if summary_elem is not None:
        # Clean up abstract
        abstract = re.sub(r'\s+', ' ', summary_elem.text.strip())
        paper['abstract'] = abstract[:2000]  # Limit length
    
    # Extract ArXiv ID and URL
    id_elem = entry.find('atom:id', ARXIV_NAMESPACE)
    if id_elem is not None:
        paper['url'] = id_elem.text.strip()
        # Extract ArXiv ID from URL
        arxiv_match = re.search(r'arxiv\.org/abs/(\d+\.\d+)', paper['url'])
        if arxiv_match:
            paper['arxiv_id'] = arxiv_match.group(1)
    
    # Extract publication/submission date
    published_elem = entry.find('atom:published', ARXIV_NAMESPACE)
    if published_elem is not None:
        try:
            # Parse ISO format date
            pub_date = datetime.fromisoformat(published_elem.text.strip().replace('Z', '+00:00'))
            paper['published_date'] = pub_date.isoformat()
        except:
            paper['published_date'] = datetime.now().isoformat()
    else:
        paper['published_date'] = datetime.now().isoformat()
    
    # Extract updated date
    updated_elem = entry.find('atom:updated', ARXIV_NAMESPACE)
    if updated_elem is not None:
        try:
            updated_date = datetime.fromisoformat(updated_elem.text.strip().replace('Z', '+00:00'))
            paper['updated_date'] = updated_date.isoformat()
        except:
            pass
    
    # Extract authors
    authors = []
    author_elems = entry.findall('atom:author', ARXIV_NAMESPACE)
    for author_elem in author_elems:
        name_elem = author_elem.find('atom:name', ARXIV_NAMESPACE)
        if name_elem is not None:
            authors.append(name_elem.text.strip())
    paper['authors'] = authors[:10]  # Limit to 10 authors
    
    # Extract categories
    categories = []
    category_elems = entry.findall('atom:category', ARXIV_NAMESPACE)
    for cat_elem in category_elems:
        term = cat_elem.get('term')
        if term:
            categories.append(term)
    paper['categories'] = categories
    
    # Extract primary category
    primary_cat_elem = entry.find('arxiv:primary_category', {'arxiv': 'http://arxiv.org/schemas/atom'})
    if primary_cat_elem is not None:
        paper['primary_category'] = primary_cat_elem.get('term')
    elif categories:
        paper['primary_category'] = categories[0]
    
    # Extract DOI if available
    doi_elem = entry.find('arxiv:doi', {'arxiv': 'http://arxiv.org/schemas/atom'})
    if doi_elem is not None:
        paper['doi'] = doi_elem.text.strip()
    
    # Extract journal reference if available
    journal_elem = entry.find('arxiv:journal_ref', {'arxiv': 'http://arxiv.org/schemas/atom'})
    if journal_elem is not None:
        paper['journal_reference'] = journal_elem.text.strip()
    
    # Extract comment if available
    comment_elem = entry.find('arxiv:comment', {'arxiv': 'http://arxiv.org/schemas/atom'})
    if comment_elem is not None:
        paper['comment'] = comment_elem.text.strip()
    
    # Add metadata
    paper.update({
        'search_category': category,
        'source': 'arxiv',
        'platform': 'arxiv_api',
        'fetched_at': datetime.now().isoformat(),
        'quality_score': calculate_quality_score(paper),
    })
    
    return paper

def calculate_quality_score(paper: Dict[str, Any]) -> int:
    """Calculate a quality score for the paper."""
    score = 0
    
    # Title quality
    title_len = len(paper.get('title', ''))
    if 20 <= title_len <= 200:
        score += 3
    elif 10 <= title_len <= 300:
        score += 1
    
    # Abstract quality
    abstract_len = len(paper.get('abstract', ''))
    if 100 <= abstract_len <= 2000:
        score += 3
    elif 50 <= abstract_len <= 3000:
        score += 1
    
    # Has multiple authors (indicates collaboration)
    author_count = len(paper.get('authors', []))
    if author_count >= 3:
        score += 3
    elif author_count >= 1:
        score += 1
    
    # Has ArXiv ID
    if paper.get('arxiv_id'):
        score += 2
    
    # Has DOI (published paper)
    if paper.get('doi'):
        score += 3
    
    # Has journal reference (published paper)
    if paper.get('journal_reference'):
        score += 2
    
    # Recent paper (within last 7 days)
    if paper.get('published_date'):
        try:
            pub_date = datetime.fromisoformat(paper['published_date'].replace('Z', '+00:00'))
            days_old = (datetime.now(pub_date.tzinfo) - pub_date).days
            if days_old <= 7:
                score += 2
            elif days_old <= 30:
                score += 1
        except:
            pass
    
    # AI/ML keywords boost
    content = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    ai_keywords = [
        'neural', 'deep learning', 'machine learning', 'artificial intelligence', 
        'transformer', 'attention', 'embedding', 'classification', 'regression',
        'cnn', 'rnn', 'lstm', 'gpt', 'bert', 'vision', 'nlp', 'reinforcement'
    ]
    
    keyword_count = sum(1 for keyword in ai_keywords if keyword in content)
    score += min(keyword_count, 5)  # Max 5 points for keywords
    
    return score

def categorize_papers_by_content(papers: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Categorize papers by content analysis."""
    categories = {
        'computer_vision': [],
        'natural_language': [],
        'machine_learning': [],
        'neural_networks': [],
        'reinforcement_learning': [],
        'robotics': [],
        'other': []
    }
    
    for paper in papers:
        content = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
        primary_cat = paper.get('primary_category', '')
        
        # Content-based categorization
        if any(kw in content for kw in ['computer vision', 'image', 'visual', 'cnn', 'vision', 'object detection']):
            categories['computer_vision'].append(paper)
        elif any(kw in content for kw in ['nlp', 'language', 'text', 'linguistic', 'bert', 'gpt', 'translation']):
            categories['natural_language'].append(paper)
        elif any(kw in content for kw in ['reinforcement', 'rl', 'policy', 'reward', 'agent']):
            categories['reinforcement_learning'].append(paper)
        elif any(kw in content for kw in ['robot', 'robotic', 'manipulation', 'navigation', 'control']):
            categories['robotics'].append(paper)
        elif any(kw in content for kw in ['neural', 'network', 'deep', 'cnn', 'rnn', 'lstm', 'transformer']):
            categories['neural_networks'].append(paper)
        elif any(kw in content for kw in ['machine learning', 'ml', 'learning', 'supervised', 'unsupervised']) or 'cs.LG' in primary_cat:
            categories['machine_learning'].append(paper)
        else:
            categories['other'].append(paper)
    
    return categories

def save_arxiv_data(papers: List[Dict[str, Any]], output_dir: str):
    """Save ArXiv papers to JSON and CSV files."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Save main data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = os.path.join(output_dir, f"arxiv_papers_{timestamp}.json")
    latest_file = os.path.join(output_dir, "arxiv_papers_latest.json")
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)
    
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump(papers, f, indent=2, ensure_ascii=False)
    
    # Save categorized data
    categorized = categorize_papers_by_content(papers)
    for category, category_papers in categorized.items():
        if category_papers:
            cat_file = os.path.join(output_dir, f"arxiv_{category}_{timestamp}.json")
            with open(cat_file, 'w', encoding='utf-8') as f:
                json.dump(category_papers, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(papers)} papers to {json_file}")
    
    # Save summary stats
    stats = {
        'total_papers': len(papers),
        'categories': {cat: len(papers) for cat, papers in categorized.items()},
        'avg_quality_score': sum(p.get('quality_score', 0) for p in papers) / len(papers) if papers else 0,
        'date_range': {
            'oldest': min((p.get('published_date') for p in papers if p.get('published_date')), default=None),
            'newest': max((p.get('published_date') for p in papers if p.get('published_date')), default=None)
        },
        'last_updated': datetime.now().isoformat()
    }
    
    stats_file = os.path.join(output_dir, "arxiv_stats.json")
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

def main():
    """Main ETL process."""
    logger.info("Starting Simple ArXiv ETL process with API")
    
    all_papers = []
    
    # Fetch from all search queries
    for category, search_query in ARXIV_QUERIES.items():
        logger.info(f"Fetching papers for category: {category}")
        papers = fetch_arxiv_papers(category, search_query, max_results=100)
        all_papers.extend(papers)
        
        # Rate limiting - ArXiv recommends 3 second delays
        time.sleep(3)
    
    if not all_papers:
        logger.warning("No papers fetched from any query")
        return
    
    # Remove duplicates based on ArXiv ID
    seen_ids = set()
    unique_papers = []
    for paper in all_papers:
        arxiv_id = paper.get('arxiv_id')
        if arxiv_id and arxiv_id not in seen_ids:
            seen_ids.add(arxiv_id)
            unique_papers.append(paper)
        elif not arxiv_id:  # Keep papers without ID (shouldn't happen with API)
            unique_papers.append(paper)
    
    logger.info(f"Total unique papers: {len(unique_papers)}")
    
    # Sort by quality score and date
    unique_papers.sort(key=lambda x: (x.get('quality_score', 0), x.get('published_date', '')), reverse=True)
    
    # Save data
    output_dir = os.path.join(project_root, "data", "arxiv")
    save_arxiv_data(unique_papers, output_dir)
    
    logger.info("Simple ArXiv ETL completed successfully!")
    logger.info(f"Total papers processed: {len(unique_papers)}")
    
    # Print category breakdown
    categorized = categorize_papers_by_content(unique_papers)
    logger.info("Category breakdown:")
    for category, papers in categorized.items():
        if papers:
            logger.info(f"  {category}: {len(papers)} papers")
    
    # Print quality distribution
    quality_scores = [p.get('quality_score', 0) for p in unique_papers]
    if quality_scores:
        logger.info(f"Quality scores - Min: {min(quality_scores)}, Max: {max(quality_scores)}, Avg: {sum(quality_scores)/len(quality_scores):.1f}")

if __name__ == "__main__":
    main() 