"""
Factory for constructing LLM clients based on a provider name.

Centralizes provider selection so callers (LLMGenerator, scripts,
tests, api.py) never import a concrete provider class directly --
they ask the factory for "whichever LLM_PROVIDER is configured" and
get back an object satisfying BaseLLM. Adding a new provider later
means adding one branch here, nothing else in the codebase changes.

Currently supported:
    - "openai" -> src.LLM.openai_client.OpenAILLM

Recognized but not yet implemented (raise a clear error until a
client is added for them):
    - "ollama", "azure", "gemini", "anthropic"
"""

import logging
from typing import Optional

from src.LLM.base_llm import BaseLLM
from src import config

logger = logging.getLogger(__name__)

_SUPPORTED = ("openai", "ollama", "azure", "gemini", "anthropic")


def get_llm(provider: Optional[str] = None, **kwargs) -> BaseLLM:
    """Build and return an LLM client for the given provider.

    Args:
        provider: One of "openai", "ollama", "azure", "gemini",
            "anthropic" (case-insensitive). Defaults to
            `config.LLM_PROVIDER` if not given, or "openai" if that
            setting doesn't exist either.
        **kwargs: Forwarded as-is to the concrete client's constructor
            (e.g. model="gpt-4o", timeout=30, max_retries=3, ...).

    Returns:
        A BaseLLM instance ready to use.

    Raises:
        ValueError: If `provider` isn't one of the recognized names.
        NotImplementedError: If `provider` is recognized but no
            concrete client has been wired up for it yet.

    Example:
        >>> llm = get_llm()                       # uses config.LLM_PROVIDER
        >>> llm = get_llm("openai", model="gpt-4o")  # explicit override
    """
    resolved = (provider or getattr(config, "LLM_PROVIDER", None) or "openai").lower()

    if resolved not in _SUPPORTED:
        raise ValueError(
            f"Unknown LLM provider '{resolved}'. Supported: {_SUPPORTED}"
        )

    logger.info("Building LLM client for provider=%s", resolved)

    if resolved == "openai":
        from src.LLM.openai_client import OpenAILLM
        return OpenAILLM(**kwargs)

    # --- Recognized, planned for the future -----------------------------
    # Each of these needs a BaseLLM-compliant client class added under
    # src/LLM/ before it can be returned here (mirroring openai_client.py).

    if resolved == "ollama":
        raise NotImplementedError(
            "The 'ollama' provider isn't migrated to the BaseLLM interface "
            "yet -- the old src/LLM/ollama_client.py still talks to Ollama "
            "directly via requests.post(). Build src/LLM/ollama_llm.py "
            "(implementing BaseLLM) and add a branch here to enable it."
        )

    raise NotImplementedError(
        f"Provider '{resolved}' is planned but not implemented yet. "
        f"Add a BaseLLM-compliant client under src/LLM/ and wire it up here."
    )