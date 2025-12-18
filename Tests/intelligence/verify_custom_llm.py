
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Environment variables should be loaded from .env by the Settings class
# or already set in the environment.

from src.intelligence.ai_engines import AITrendDetector
from src.models.ai_research_model import AIResearchPaper, ImplementationComplexity, ResearchDomain
from src.config.settings import get_settings, reload_settings

def test_custom_endpoint():
    print("Testing Custom LLM Endpoint (api.z.ai)...")
    
    # Reload settings to pick up env vars
    reload_settings()
    settings = get_settings()
    
    print(f"Provider: {settings.llm.provider}")
    print(f"Base URL: {settings.llm.openai_base_url}")
    print(f"API Key Set: {bool(settings.llm.openai_api_key)}")
    
    # Create Dummy Paper
    paper = AIResearchPaper(
        title="Generative Agents in Python",
        abstract="A comprehensive guide to building autonomous agents using Python and LLMs.",
        published_at="2024-01-15T00:00:00",
        authors=["Dev"],
        primary_domain=ResearchDomain.GENERATIVE,
        url="http://example.com",
        source="Test",
        trend_score=0.0,
        complexity=ImplementationComplexity.MEDIUM
    )
    
    # Run Analysis
    detector = AITrendDetector()
    try:
        score = detector.analyze_trend(paper)
        print(f"Analysis Success! Trend Score: {score}")
        if score > 0.3: # Heuristic threshold
             print("LLM was likely called (or heuristic was high).")
    except Exception as e:
        print(f"Analysis Failed: {e}")

    print("Test Complete.")

if __name__ == "__main__":
    test_custom_endpoint()
