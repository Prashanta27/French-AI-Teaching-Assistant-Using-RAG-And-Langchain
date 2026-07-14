"""
Abstract base class for all embedding provider implementations.

Every concrete embedding client (OpenAI, Azure OpenAI, Gemini, local
SentenceTransformer via EmbeddingManager, ...) implements this
interface so ingest.py / semantic_retriever.py can swap providers
without any code change -- only config.py / a factory function needs
to change.
"""

import logging
from abc import ABC, abstractmethod
from typing import List

import numpy as np

logger = logging.getLogger(__name__)


class BaseEmbedding(ABC):
    """Abstract contract every embedding client must satisfy."""

    @abstractmethod
    def generate_embedding(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            numpy array of shape (len(texts), embedding_dim).
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def embedding_dimension(self) -> int:
        """Dimensionality of the embedding vectors produced by this client."""
        raise NotImplementedError