"""
Regression tests for CrossEncoderReranker -- uses a mocked
cross-encoder model (no real download/network needed) to verify the
reranking, truncation, and graceful-failure logic.
"""

from unittest.mock import MagicMock

import numpy as np

from src.retriever.reranker import CrossEncoderReranker
from src.retriever.semantic_retriever import SemanticRetriever


class FakeResult:

    def __init__(self, content, score):

        self.content = content
        self.score = score


def _mocked_reranker(predict_return):

    reranker = CrossEncoderReranker()

    fake_model = MagicMock()

    fake_model.predict.return_value = predict_return

    reranker._model = fake_model

    return reranker


def test_reranker_promotes_the_true_best_match():

    candidates = [
        FakeResult("Le subjonctif est utilise pour exprimer un doute.", score=0.85),
        FakeResult("Vocabulaire de la nourriture.", score=0.60),
        FakeResult("Conjugaison du verbe etre au present.", score=0.55),
    ]

    # Cross-encoder disagrees with the bi-encoder: candidate 3 (worst
    # bi-encoder score) is actually the most relevant.
    reranker = _mocked_reranker(predict_return=[0.2, 0.3, 0.95])

    result = reranker.rerank("comment conjuguer etre", candidates, top_k=2)

    assert len(result) == 2
    assert result[0].content.startswith("Conjugaison")
    assert result[0].score == 0.95


def test_reranker_degrades_gracefully_on_model_failure():

    candidates = [FakeResult("a", 0.5), FakeResult("b", 0.6)]

    reranker = _mocked_reranker(predict_return=None)

    reranker._model.predict.side_effect = RuntimeError("model unavailable")

    result = reranker.rerank("query", candidates, top_k=2)

    # Falls back to the original (bi-encoder-ordered) candidates,
    # doesn't crash or return nothing.
    assert len(result) == 2


def test_reranker_handles_empty_candidates():

    reranker = CrossEncoderReranker()

    assert reranker.rerank("query", [], top_k=5) == []


# ---------------------------------------------------------
# Wiring into SemanticRetriever
# ---------------------------------------------------------

class FakeCollection:

    def __init__(self, records):

        self.records = records

    def count(self):

        return len(self.records)

    def query(self, query_embeddings, n_results, include, where=None):

        filtered = self.records[:n_results]

        return {
            "ids": [[r["id"] for r in filtered]],
            "documents": [[r["document"] for r in filtered]],
            "metadatas": [[r["metadata"] for r in filtered]],
            "distances": [[r["distance"] for r in filtered]]
        }


class FakeVectorStore:

    def __init__(self, records):

        self.collection = FakeCollection(records)


class FakeEmbeddingManager:

    def generate_embedding(self, texts):

        return [np.array([0.1, 0.2, 0.3]) for _ in texts]


class FakeSemanticPlan:

    action = "semantic_search"
    filters = {}
    target_books = []
    search_text = "comment conjuguer"
    top_k = 2


_RECORDS = [
    {"id": "c1", "document": "Conjugaison du verbe etre au present.", "distance": 0.5,
     "metadata": {"book_id": "b1", "title": "Book A", "page": 10}},
    {"id": "c2", "document": "Vocabulaire de la nourriture.", "distance": 0.3,
     "metadata": {"book_id": "b1", "title": "Book A", "page": 20}},
    {"id": "c3", "document": "Le subjonctif exprime le doute.", "distance": 0.4,
     "metadata": {"book_id": "b1", "title": "Book A", "page": 30}},
]


def test_semantic_retriever_without_reranker_uses_biencoder_order():

    retriever = SemanticRetriever(
        FakeVectorStore(_RECORDS), FakeEmbeddingManager(), MagicMock(), reranker=None
    )

    results = retriever.retrieve(FakeSemanticPlan())

    # Highest similarity (1 - distance) first: c2 (0.7), then c3 (0.6)
    assert [r.content for r in results] == [
        "Vocabulaire de la nourriture.",
        "Le subjonctif exprime le doute.",
    ]


def test_semantic_retriever_with_reranker_uses_crossencoder_order():

    reranker = _mocked_reranker(predict_return=[0.99, 0.1, 0.5])

    retriever = SemanticRetriever(
        FakeVectorStore(_RECORDS), FakeEmbeddingManager(), MagicMock(), reranker=reranker
    )

    results = retriever.retrieve(FakeSemanticPlan())

    assert results[0].content == "Conjugaison du verbe etre au present."
    assert results[0].rank == 1