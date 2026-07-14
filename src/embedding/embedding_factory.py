"""
Factory for constructing embedding clients based on a provider name.

Mirrors llm_factory.py: centralizes provider selection so callers
(LLMGenerator, ingest.py, semantic_retriever.py) never import a
concrete provider class directly -- they ask the factory for
"whichever EMBEDDING_PROVIDER is configured" and get back an object
exposing `generate_embedding(texts) -> np.ndarray`.

Currently supported:
    - "openai"              -> src.embedding.openai_embedding.OpenAIEmbedding
    - "sentence_transformer" -> src.embedding.embedding.EmbeddingManager
                                (the original local/offline model -- kept
                                available so you can fall back to it, or
                                A/B compare, without deleting anything)

Recognized but not yet implemented:
    - "azure", "gemini"

Note:
    "sentence_transformer" (EmbeddingManager) predates BaseEmbedding
    and doesn't formally subclass it (no `embedding_dimension`
    property yet) -- but it does implement `generate_embedding`, which
    is all the current pipeline (ingest.py, semantic_retriever.py)
    actually calls, so it's safe to return here as-is.
"""

import logging
from typing import Optional

from src import config

logger = logging.getLogger(__name__)

_SUPPORTED = ("openai", "sentence_transformer", "azure", "gemini")


def get_embedding(provider: Optional[str] = None, **kwargs):
    """Build and return an embedding client for the given provider.

    Args:
        provider: One of "openai", "sentence_transformer", "azure",
            "gemini" (case-insensitive). Defaults to
            `config.EMBEDDING_PROVIDER` if not given, or "openai" if
            that setting doesn't exist either.
        **kwargs: Forwarded as-is to the concrete client's constructor
            (e.g. model="text-embedding-3-large", batch_size=50, ...).

    Returns:
        An embedding client exposing `generate_embedding(texts) -> np.ndarray`.

    Raises:
        ValueError: If `provider` isn't one of the recognized names.
        NotImplementedError: If `provider` is recognized but no
            concrete client has been wired up for it yet.

    Example:
        >>> embedder = get_embedding()                  # config default
        >>> embedder = get_embedding("sentence_transformer")  # explicit
    """
    resolved = (provider or getattr(config, "EMBEDDING_PROVIDER", None) or "openai").lower()

    if resolved not in _SUPPORTED:
        raise ValueError(
            f"Unknown embedding provider '{resolved}'. Supported: {_SUPPORTED}"
        )

    logger.info("Building embedding client for provider=%s", resolved)

    if resolved == "openai":
        from src.embedding.openai_embedding import OpenAIEmbedding
        return OpenAIEmbedding(**kwargs)

    if resolved == "sentence_transformer":
        from src.embedding.embedding import EmbeddingManager
        return EmbeddingManager(**kwargs)

    raise NotImplementedError(
        f"Provider '{resolved}' is planned but not implemented yet. "
        f"Add a BaseEmbedding-compliant client under src/embedding/ and "
        f"wire it up here."
    )