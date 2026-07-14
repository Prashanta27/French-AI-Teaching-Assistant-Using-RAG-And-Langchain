"""
Abstract base class for all LLM client implementations.

Every concrete LLM client (OpenAI, Azure OpenAI, Anthropic, Gemini,
Ollama, ...) implements this interface so that the rest of the
pipeline (LLMGenerator, PromptBuilder, etc.) can swap providers
without touching pipeline code -- only config.py / a factory function
needs to change.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Generator, List

logger = logging.getLogger(__name__)


class BaseLLM(ABC):
    """Abstract contract every LLM client must satisfy."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate a single completion for a plain-text prompt.

        Args:
            prompt: The user prompt / question to send to the model.
            **kwargs: Provider-specific overrides (temperature, max_tokens, ...).

        Returns:
            The full generated text response.
        """
        raise NotImplementedError

    @abstractmethod
    def generate_stream(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        """Generate a completion, yielding text chunks as they arrive.

        Args:
            prompt: The user prompt / question to send to the model.
            **kwargs: Provider-specific overrides.

        Yields:
            Successive text chunks of the response.
        """
        raise NotImplementedError

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a completion from a full chat message history.

        Args:
            messages: List of {"role": ..., "content": ...} dicts.
            **kwargs: Provider-specific overrides.

        Returns:
            The full generated text response.
        """
        raise NotImplementedError