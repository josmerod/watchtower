"""LLM Client Abstraction and Implementations."""

import abc
import json
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI
from pydantic import BaseModel

from src.config.models import LLMProvider
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class LLMClient(abc.ABC):
    """Abstract base class for LLM clients."""

    @abc.abstractmethod
    def analyze_text(self, text: str, prompt: str, system_message: str = "You are a helpful AI assistant.") -> str:
        """Analyze text and return raw string response.
        
        Args:
            text: The content to analyze.
            prompt: Specific instructions for analysis.
            system_message: System role definition.
            
        Returns:
            str: The LLM's response.
        """
        pass
    
    @abc.abstractmethod
    def extract_structured_data(self, text: str, schema: BaseModel, prompt: str) -> Optional[BaseModel]:
        """Extract structured data matching a Pydantic schema.
        
        Args:
            text: Content to analyze.
            schema: Pydantic model class to validate against.
            prompt: Instructions for extraction.
            
        Returns:
            Optional[BaseModel]: Instance of schema or None if failure.
        """
        pass


class OpenAIClient(LLMClient):
    """OpenAI API implementation."""


    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: Optional[str] = None):
        """Initialize OpenAI client."""
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def analyze_text(self, text: str, prompt: str, system_message: str = "You are a helpful AI assistant.") -> str:
        """Analyze text using Chat Completions API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"{prompt}\n\nContext:\n{text[:10000]}"} # Truncate to avoid context limits
                ],
                temperature=0.3
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return f"Error analyzing text: {str(e)}"

    def extract_structured_data(self, text: str, schema: Any, prompt: str) -> Optional[Any]:
        """Extract structured data using OpenAI tools/function calling."""
        
        # Check if using a custom provider (base_url != default)
        # OpenAI Python SDK defaults base_url to "https://api.openai.com/v1"
        is_custom_provider = str(self.client.base_url) != "https://api.openai.com/v1/"
        
        # Strategy 1: Manual JSON Parsing (Preferred for Custom Providers like z.ai, vllm)
        if is_custom_provider:
            try:
                schema_json = json.dumps(schema.model_json_schema(), indent=2)
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": f"You are a helpful AI assistant. Output ONLY valid JSON matching this schema:\n{schema_json}"},
                        {"role": "user", "content": f"{prompt}\n\nContext:\n{text[:15000]}"}
                    ],
                    response_format={"type": "json_object"}, 
                    temperature=0.1
                )
                content = response.choices[0].message.content
                if content:
                    return schema.model_validate_json(content)
            except Exception as e:
                logger.warning(f"Manual extraction failed for custom provider ({e}). Trying strict mode...")

        # Strategy 2: Strict Structured Outputs (Beta SDK) - Default for OpenAI
        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                   {"role": "system", "content": "Extract the requested information structured exactly according to the schema."},
                   {"role": "user", "content": f"{prompt}\n\nContext:\n{text[:15000]}"}
                ],
                response_format=schema,
            )
            return completion.choices[0].message.parsed
        except Exception as e:
            # If we haven't tried manual yet (i.e., we are standard OpenAI), try manual as fallback
            if not is_custom_provider:
                logger.warning(f"Strict structured extraction failed ({e}). Falling back to manual parsing.")
                try:
                    schema_json = json.dumps(schema.model_json_schema(), indent=2)
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": f"You are a helpful AI assistant. Output ONLY valid JSON matching this schema:\n{schema_json}"},
                            {"role": "user", "content": f"{prompt}\n\nContext:\n{text[:15000]}"}
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.1
                    )
                    content = response.choices[0].message.content
                    if content:
                        return schema.model_validate_json(content)
                except Exception as ex:
                    logger.error(f"Manual fallback also failed: {ex}")
            else:
                logger.error(f"Structured extraction (strict) also failed: {e}")
            
            return None


class MockLLMClient(LLMClient):
    """Mock client for testing/dev without API keys."""
    
    def analyze_text(self, text: str, prompt: str, system_message: str = "") -> str:
        return "[MOCK] AI analysis of text."
        
    def extract_structured_data(self, text: str, schema: Any, prompt: str) -> Optional[Any]:
        # Return empty/default instance if possible, or None
        try:
            return schema()
        except:
            return None


def get_llm_client() -> LLMClient:
    """Factory to get the configured LLM client."""
    settings = get_settings()
    config = settings.llm
    
    if config.provider == LLMProvider.OPENAI:
        if not config.openai_api_key:
            logger.warning("OpenAI Provider selected but no API Key found. Falling back to Mock.")
            return MockLLMClient()
        return OpenAIClient(
            api_key=config.openai_api_key, 
            model=config.model,
            base_url=config.openai_base_url
        )
        
    elif config.provider == LLMProvider.ANTHROPIC:
        # Placeholder for future implementation
        logger.warning("Anthropic not yet implemented. Falling back to Mock.")
        return MockLLMClient()
        
    else:
        return MockLLMClient()
