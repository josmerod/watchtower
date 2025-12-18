
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.intelligence.ai_engines import AITrendDetector
from src.models.ai_research_model import AIResearchPaper, ImplementationComplexity, ResearchDomain
from src.config.settings import get_settings

def test_llm_integration():
    print("Testing LLM Integration...")
    
    # 1. Check Configuration
    settings = get_settings()
    print(f"LLM Provider: {settings.llm.provider}")
    print(f"API Key Present: {bool(settings.llm.openai_api_key)}")
    
    # 2. Create Dummy Paper
    paper = AIResearchPaper(
        title="Autonomous Agents with Reasoning Capabilities",
        abstract="We present a new method for autonomous agents that can reason about complex tasks using LLMs.",
        published_at="2023-12-01T00:00:00",
        authors=["Alice", "Bob"],
        primary_domain=ResearchDomain.GENERATIVE,
        url="http://example.com",
        source="Test",
        trend_score=0.0,
        complexity=ImplementationComplexity.MEDIUM
    )
    
    # 3. Run Analysis
    detector = AITrendDetector()
    score = detector.analyze_trend(paper)
    
    print(f"Analysis Result Trend Score: {score}")
    
    # Validate result
    if score > 0.6:
        print("PASS: High trend score detected (as expected for 'Autonomous Agents').")
    else:
        print("WARN: Low trend score. Valid if running MOCK or API failed.")

    print("\nTest Complete.")

if __name__ == "__main__":
    test_llm_integration()
