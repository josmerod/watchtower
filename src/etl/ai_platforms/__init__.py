"""AI Platform Monitoring ETL module.

Monitors AI/ML platforms: Anthropic Claude, GitHub Copilot usage, and the
Replicate/Ollama model catalogs. Older submodules (OpenAI platform, Hugging
Face trends, the class-based AIMonitoringETL) were removed in earlier
cleanups — keep this init importable so module-level ETLs in this package
(anthropic, github_copilot, replicate, ollama_library) can be imported for
tests and tooling.
"""

from .anthropic_etl import AnthropicETL
from .github_copilot_etl import GitHubCopilotETL

__all__ = [
    "AnthropicETL",
    "GitHubCopilotETL",
]
