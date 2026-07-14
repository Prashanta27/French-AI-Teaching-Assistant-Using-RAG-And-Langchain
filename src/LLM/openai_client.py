"""
OpenAI LLM client implementing the BaseLLM contract.

Drop-in replacement for the raw model-call part of the old
`ollama_client.py` (its `_call_ollama` method) -- everything else in
LLMGenerator (query_analyzer, retriever, prompt_builder) stays
unchanged. LLMGenerator should call this client's `.generate(prompt)`
or `.chat(messages)` instead of hitting `requests.post(...)` directly.

Features:
    - Non-streaming and streaming chat completions
    - Automatic retry with exponential backoff + jitter
    - Configurable per-request timeout
    - Structured logging
    - Type hints + Google-style docstrings

Example:
    >>> client = OpenAILLM(model="gpt-4.1-mini")
    >>> client.generate("What is the capital of France?")
    'The capital of France is Paris.'
"""

import logging
import random
import time
from typing import Dict, Generator, List, Optional

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

from src.LLM.base_llm import BaseLLM
from src import config

logger = logging.getLogger(__name__)

# Transient errors worth retrying (network hiccups, rate limits, 5xx, timeouts).
RETRYABLE_EXCEPTIONS = (APITimeoutError, APIConnectionError, RateLimitError)


class OpenAILLM(BaseLLM):
    """OpenAI Chat Completions client with retry, timeout and streaming support."""

    def __init__(
        self,
        model: str = "gpt-4.1-mini",
        api_key: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 5,
        backoff_base: float = 1.5,
        backoff_max: float = 30.0,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
    ) -> None:
        """
        Args:
            model: OpenAI chat model name (e.g. "gpt-4o-mini", "gpt-4o").
            api_key: Overrides `config.OPENAI_API_KEY` if provided.
            timeout: Per-request timeout in seconds.
            max_retries: Max retry attempts on transient failures.
            backoff_base: Base seconds used to compute exponential backoff.
            backoff_max: Upper cap for backoff delay, in seconds.
            temperature: Default sampling temperature for completions.
            max_tokens: Default max output tokens (None = provider default).

        Raises:
            ValueError: If no API key is available from config or argument.
        """
        key = api_key or config.OPENAI_API_KEY

        if not key:
            raise ValueError(
                "OPENAI_API_KEY not found. Set it in your .env file "
                "or pass api_key explicitly."
            )

        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.temperature = temperature
        self.max_tokens = max_tokens

        self._client = OpenAI(api_key=key, timeout=timeout)

        logger.info("OpenAILLM initialized (model=%s, timeout=%.1fs)", model, timeout)

    # -----------------------------------------------------
    # Public API (BaseLLM contract)
    # -----------------------------------------------------

    def generate(self, prompt: str, **kwargs) -> str:
        """See BaseLLM.generate. Wraps prompt as a single user message."""
        return self.chat([{"role": "user", "content": prompt}], **kwargs)

    def generate_stream(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        """See BaseLLM.generate_stream. Wraps prompt as a single user message."""
        yield from self.chat_stream([{"role": "user", "content": prompt}], **kwargs)

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """See BaseLLM.chat."""
        params = self._build_params(messages, stream=False, **kwargs)

        response = self._call_with_retry(params)

        try:
            return response.choices[0].message.content or ""
        except (IndexError, AttributeError):
            logger.exception("Unexpected OpenAI response shape: %s", response)
            return "Received an unexpected response from OpenAI."

    def chat_stream(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        """Stream a chat completion chunk by chunk.

        Args:
            messages: List of {"role": ..., "content": ...} dicts.
            **kwargs: Provider-specific overrides.

        Yields:
            Successive text chunks of the response.
        """
        params = self._build_params(messages, stream=True, **kwargs)

        stream = self._call_with_retry(params)

        try:
            for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
        except RETRYABLE_EXCEPTIONS as exc:
            logger.exception("Streaming interrupted: %s", exc)
            yield f"\n[Stream interrupted: {exc}]"

    # -----------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------

    def _build_params(self, messages: List[Dict[str, str]], stream: bool, **kwargs) -> Dict:
        """Merge instance defaults with per-call overrides into request params."""
        return {
            "model": kwargs.pop("model", self.model),
            "messages": messages,
            "temperature": kwargs.pop("temperature", self.temperature),
            "max_tokens": kwargs.pop("max_tokens", self.max_tokens),
            "stream": stream,
            **kwargs,
        }

    def _call_with_retry(self, params: Dict):
        """Call chat.completions.create with exponential backoff retry.

        Args:
            params: Request parameters for the OpenAI SDK call.

        Returns:
            The raw OpenAI SDK response (or stream object if stream=True).

        Raises:
            The last encountered exception once max_retries is exhausted,
            or immediately for non-retryable errors (e.g. bad request, auth).
        """
        attempt = 0

        while True:
            try:
                return self._client.chat.completions.create(**params)

            except RETRYABLE_EXCEPTIONS as exc:
                attempt += 1

                if attempt > self.max_retries:
                    logger.error(
                        "OpenAI request failed after %d attempts: %s", attempt, exc
                    )
                    raise

                delay = min(
                    self.backoff_base * (2 ** (attempt - 1)) + random.uniform(0, 0.5),
                    self.backoff_max,
                )

                logger.warning(
                    "OpenAI request failed (attempt %d/%d): %s. Retrying in %.1fs...",
                    attempt, self.max_retries, exc, delay,
                )

                time.sleep(delay)

            except APIStatusError as exc:
                # Non-transient errors (4xx: bad request, auth, invalid model, ...).
                logger.exception("OpenAI API returned an error status: %s", exc)
                raise


if __name__ == "__main__":  # Manual smoke test -- python -m src.LLM.openai_client
    logging.basicConfig(level=logging.INFO)

    llm = OpenAILLM()

    print(llm.generate("Say hello in French."))