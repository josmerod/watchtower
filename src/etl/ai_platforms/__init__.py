"""AI Platform Monitoring ETL Module.

This module implements comprehensive monitoring for AI/ML platforms including:
- OpenAI API ecosystem
- Anthropic Claude platform
- Google AI (Gemini/Bard)
- Microsoft Copilot suite (placeholder)
- Meta AI research (placeholder)
- GitHub Copilot usage
- Hugging Face model trends

Based on Watchtower Platform Expansion Proposals: AI & ML Platform Monitoring.
"""

from .ai_monitoring_etl import AIMonitoringETL
from .openai_platform_etl import OpenAIPlatformETL
from .anthropic_etl import AnthropicETL
from .huggingface_etl import HuggingFaceETL
from .github_copilot_etl import GitHubCopilotETL

__all__ = [
    'AIMonitoringETL',
    'OpenAIPlatformETL', 
    'AnthropicETL',
    'HuggingFaceETL',
    'GitHubCopilotETL'
] 