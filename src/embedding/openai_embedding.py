"""
OpenAI embedding client implementing the BaseEmbedding contract.

Drop-in replacement for `src.embedding.embedding.EmbeddingManager`:
same `generate_embedding(texts) -> np.ndarray` method signature, so
existing callers (ingest.py, semantic_retriever.py, ...) don't need
any change beyond swapping which class gets instantiated.

Features:
    - Automatic batching (OpenAI limits items per request)
    - Automatic retry with exponential backoff + jitter
    - Configurable per-request timeout
    - Structured logging
    - Type hints + Google-style docstrings

Example:
    >>> embedder = OpenAIEmbedding(model="text-embedding-3-small")
    >>> vectors = embedder.generate_embedding(["Hello", "Bonjour"])
    >>> vectors.shape
    (2, 1536)
"""

import logging
import random
import time
from typing import Dict, List, Optional
from src.config import OPENAI_API_KEY
import numpy as np
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

from src.embedding.base_embedding import BaseEmbedding
from src import config

logger = logging.getLogger(__name__)

RETRYABLE_EXCEPTIONS = (APITimeoutError, APIConnectionError, RateLimitError)

# Known dimensions for common OpenAI embedding models (used before the
# first real API call, so callers can inspect `embedding_dimension` early).
_MODEL_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class OpenAIEmbedding(BaseEmbedding):
    """OpenAI embeddings client with batching, retry, and timeout handling."""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 5,
        backoff_base: float = 1.5,
        backoff_max: float = 30.0,
        batch_size: int = 100,
        dimensions: Optional[int] = None,
    ) -> None:
        """
        Args:
            model: OpenAI embedding model name.
            api_key: Overrides `config.OPENAI_API_KEY` if provided.
            timeout: Per-request timeout in seconds.
            max_retries: Max retry attempts on transient failures.
            backoff_base: Base seconds used to compute exponential backoff.
            backoff_max: Upper cap for backoff delay, in seconds.
            batch_size: Number of texts sent per API call (keeps requests
                small/fast and avoids hitting per-request item limits).
            dimensions: Optional output-dimension override, only supported
                by the `text-embedding-3-*` model family.

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
        self.batch_size = batch_size
        self.dimensions = dimensions

        self._client = OpenAI(api_key=key, timeout=timeout)
        self._dim = dimensions or _MODEL_DIMENSIONS.get(model)

        logger.info("OpenAIEmbedding initialized (model=%s, timeout=%.1fs)", model, timeout)

    # -----------------------------------------------------
    # Public API (BaseEmbedding contract)
    # -----------------------------------------------------

    def generate_embedding(self, texts: List[str]) -> np.ndarray:
        """See BaseEmbedding.generate_embedding. Batches requests automatically."""
        if not texts:
            return np.empty((0, self._dim or 0))

        logger.info("Generating OpenAI embeddings for %d texts...", len(texts))

        all_vectors: List[List[float]] = []

        for start in range(0, len(texts), self.batch_size):
            batch = texts[start:start + self.batch_size]
            # OpenAI rejects empty strings -- substitute a single space.
            batch = [t if t and t.strip() else " " for t in batch]
            vectors = self._embed_batch(batch)
            all_vectors.extend(vectors)

        embeddings = np.array(all_vectors, dtype=np.float32)

        if self._dim is None and embeddings.size:
            self._dim = embeddings.shape[1]

        logger.info("Generated embeddings with shape: %s", embeddings.shape)

        return embeddings

    @property
    def embedding_dimension(self) -> int:
        """See BaseEmbedding.embedding_dimension."""
        if self._dim is None:
            raise ValueError(
                "Embedding dimension unknown until generate_embedding() has "
                "been called at least once (or pass dimensions=... explicitly)."
            )
        return self._dim

    # -----------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------

    def _embed_batch(self, batch: List[str]) -> List[List[float]]:
        """Embed a single batch of texts (<= batch_size items)."""
        params: Dict = {"model": self.model, "input": batch}

        if self.dimensions:
            params["dimensions"] = self.dimensions

        response = self._call_with_retry(params)

        return [item.embedding for item in response.data]

    def _call_with_retry(self, params: Dict):
        """Call embeddings.create with exponential backoff retry.

        Args:
            params: Request parameters for the OpenAI SDK call.

        Returns:
            The raw OpenAI SDK embeddings response.

        Raises:
            The last encountered exception once max_retries is exhausted,
            or immediately for non-retryable errors (e.g. bad request, auth).
        """
        attempt = 0

        while True:
            try:
                return self._client.embeddings.create(**params)

            except RETRYABLE_EXCEPTIONS as exc:
                attempt += 1

                if attempt > self.max_retries:
                    logger.error(
                        "OpenAI embedding request failed after %d attempts: %s",
                        attempt, exc,
                    )
                    raise

                delay = min(
                    self.backoff_base * (2 ** (attempt - 1)) + random.uniform(0, 0.5),
                    self.backoff_max,
                )

                logger.warning(
                    "OpenAI embedding request failed (attempt %d/%d): %s. "
                    "Retrying in %.1fs...",
                    attempt, self.max_retries, exc, delay,
                )

                time.sleep(delay)

            except APIStatusError as exc:
                logger.exception("OpenAI API returned an error status: %s", exc)
                raise


if __name__ == "__main__":  # Manual smoke test -- python -m src.embedding.openai_embedding
    logging.basicConfig(level=logging.INFO)

    embedder = OpenAIEmbedding()

    emb = embedder.generate_embedding(["Hello", "Bonjour"])

    print(emb.shape)