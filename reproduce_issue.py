from src.models.ai_research_model import AIResearchPaper, ResearchDomain
import json

data = {
    "title": "Test Paper",
    "authors": ["Author"],
    "published_at": "2025-01-01T00:00:00Z",
    "url": "http://example.com",
    "source": "arxiv",
    "abstract": "Abstract",
    "primary_domain": "Computer Vision",
    "complexity": "Medium"
}

try:
    paper = AIResearchPaper(**data)
    print(f"Paper created successfully.")
    print(f"primary_domain type: {type(paper.primary_domain)}")
    print(f"primary_domain value: {paper.primary_domain}")
    print(f"Has .value attribute? {hasattr(paper.primary_domain, 'value')}")
    
    if hasattr(paper.primary_domain, 'value'):
        print(f"primary_domain.value: {paper.primary_domain.value}")
    
    print(f"str(primary_domain): {str(paper.primary_domain)}")
    print(f"str(ResearchDomain.CV): {str(ResearchDomain.CV)}")
    
    # Test containment
    domains_list = [ResearchDomain.CV]
    domain_str = "Computer Vision"
    print(f"'{domain_str}' in {domains_list}: {domain_str in domains_list}")
    
    # Test equality
    print(f"'{domain_str}' == ResearchDomain.CV: {domain_str == ResearchDomain.CV}")
        
except Exception as e:
    print(f"Error: {e}")
