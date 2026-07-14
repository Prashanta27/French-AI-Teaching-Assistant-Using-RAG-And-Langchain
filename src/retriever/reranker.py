"""
CrossEncoderReranker
=====================

Bi-encoder embedding search (SemanticRetriever) is fast but
approximate: query and passage are embedded independently, so
similarity is just a cosine distance between two vectors that never
"saw" each other. A cross-encoder jointly encodes (query, passage)
pairs and directly predicts a relevance score -- much more accurate,
but too slow to run over an entire vector store collection.

The standard pattern (used here): let SemanticRetriever's bi-encoder
overfetch a modest candidate pool cheaply, then use the cross-encoder
to precisely re-rank just that pool and keep the real top_k.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """
    Parameters
    ----------
    model_name:
        A multilingual cross-encoder is used by default since this
        corpus is French -- an English-only cross-encoder (e.g. the
        common "ms-marco-MiniLM" ones) would silently underperform
        here without an obvious error to signal it.
    """

    DEFAULT_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"

    def __init__(self, model_name: str = DEFAULT_MODEL):

        self.model_name = model_name

        self._model = None
        # Lazy-loaded on first use, not at construction -- same
        # pattern as EmbeddingManager, so constructing a
        # CrossEncoderReranker (e.g. to check whether one is
        # configured) never triggers a model download by itself, and
        # tests/wiring code can inject a fake without ever touching
        # the network.

    # -----------------------------------------------------

    def _load_model(self):

        if self._model is not None:

            return self._model

        from sentence_transformers import CrossEncoder

        logger.info("Loading cross-encoder model: %s", self.model_name)

        self._model = CrossEncoder(self.model_name)

        return self._model

    # -----------------------------------------------------

    def rerank(self, query: str, candidates: List, top_k: int) -> List:
        """
        candidates: a list of objects with a `.content` attribute and
        a `.score` attribute (SemanticRetrievalResult-shaped -- kept
        duck-typed rather than importing that class here, to avoid a
        circular import between semantic_retriever.py and this file).

        Returns the top_k candidates, re-ordered by cross-encoder
        relevance, with `.score` overwritten to reflect that (so
        callers/logging always see the score that was actually used
        to rank, not a stale bi-encoder similarity).
        """

        if not candidates:

            return []

        if len(candidates) <= 1:

            return candidates[:top_k]

        try:

            model = self._load_model()

            pairs = [(query, c.content or "") for c in candidates]

            scores = model.predict(pairs)

        except Exception:

            logger.exception(
                "Cross-encoder reranking failed -- falling back to the "
                "original bi-encoder ranking unchanged."
            )

            return candidates[:top_k]

        for candidate, score in zip(candidates, scores):

            candidate.score = float(score)

        reranked = sorted(candidates, key=lambda c: c.score, reverse=True)

        return reranked[:top_k]


# ---------------------------------------------------------
# Testing (mocked model -- no real download/network needed)
# ---------------------------------------------------------

if __name__ == "__main__":

    from unittest.mock import MagicMock

    class FakeResult:

        def __init__(self, content, score):

            self.content = content
            self.score = score

    reranker = CrossEncoderReranker()

    fake_model = MagicMock()

    # Deliberately invert the bi-encoder's ranking: the cross-encoder
    # decides candidate 3 (originally lowest bi-encoder score) is
    # actually the most relevant. This is exactly the scenario
    # reranking exists for.
    fake_model.predict.return_value = [0.2, 0.9, 0.95]

    reranker._model = fake_model

    candidates = [
        FakeResult("Le subjonctif est utilise pour exprimer un doute.", score=0.85),
        FakeResult("Vocabulaire de la nourriture: le pain, le fromage.", score=0.60),
        FakeResult("Conjugaison du verbe etre au present.", score=0.55),
    ]

    result = reranker.rerank("comment conjuguer etre", candidates, top_k=2)

    print("Reranked order:")

    for r in result:

        print(f"  score={r.score:.2f}  {r.content}")

    assert result[0].content.startswith("Conjugaison")
    assert len(result) == 2

    print("\nOK: reranker correctly promoted the cross-encoder's top pick.")

    # Failure path -- model.predict raises, should degrade gracefully
    fake_model.predict.side_effect = RuntimeError("boom")

    fallback = reranker.rerank("test", candidates, top_k=2)

    assert len(fallback) == 2

    print("OK: reranker failure degrades to original order without crashing.")