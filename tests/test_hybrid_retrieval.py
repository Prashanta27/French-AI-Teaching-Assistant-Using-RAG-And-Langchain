"""
Regression tests for Hybrid Retrieval: when ExactRetriever finds
nothing for a fetch_exact_section plan, Retriever should
automatically retry as a semantic search scoped to the same book/
filters, rather than returning empty-handed.

Uses a mocked SemanticRetriever (no real vector store/embedding
model needed) -- these tests check the fallback *logic*, not
semantic search quality itself.
"""

from unittest.mock import MagicMock

from src.retriever.retriever import Retriever


class FakeExactResult:

    def __init__(self, found, title=None, page=None, chapter=None,
                 exercise=None, activity=None, line=None, content=None):

        self.found = found
        self.title = title
        self.page = page
        self.chapter = chapter
        self.exercise = exercise
        self.activity = activity
        self.line = line
        self.content = content


class FakeSemanticResult:

    def __init__(self, found, title=None, page=None, score=0.0, content=None):

        self.found = found
        self.title = title
        self.page = page
        self.score = score
        self.content = content


class FakePlan:

    def __init__(self, action, needs_retrieval, filters=None,
                 target_books=None, exact_location=None, search_text="", top_k=5):

        self.action = action
        self.needs_retrieval = needs_retrieval
        self.filters = filters or {}
        self.target_books = target_books or []
        self.exact_location = exact_location or {}
        self.search_text = search_text
        self.top_k = top_k


def _make_retriever(exact_return, semantic_return):

    metadata_engine = MagicMock()

    exact_retriever = MagicMock()

    exact_retriever.retrieve.return_value = exact_return

    semantic_retriever = MagicMock()

    semantic_retriever.retrieve.return_value = semantic_return

    return Retriever(metadata_engine, exact_retriever, semantic_retriever), semantic_retriever


def test_falls_back_to_semantic_when_exact_finds_nothing():

    retriever, semantic_retriever = _make_retriever(
        exact_return=[FakeExactResult(found=False, title="Cosmopolite A2 main book", page=24, exercise=3)],
        semantic_return=[FakeSemanticResult(found=True, title="Cosmopolite A2 main book", page=23,
                                             score=0.78, content="Completez avec a, au ou en...")]
    )

    plan = FakePlan(
        "fetch_exact_section", True,
        filters={"series": "Cosmopolite", "level": "A2"},
        target_books=["Cosmopolite A2 main book"],
        exact_location={"page": 24, "exercise": 3},
        search_text="Exercise 3 of page 24 Cosmopolite A2"
    )

    bundle = retriever.retrieve(plan)

    assert bundle.found is True
    assert bundle.hybrid_fallback_used is True
    assert "Completez" in bundle.context

    semantic_retriever.retrieve.assert_called_once()


def test_exact_success_does_not_trigger_fallback():

    retriever, semantic_retriever = _make_retriever(
        exact_return=[FakeExactResult(found=True, title="Cosmopolite A2 main book",
                                       page=24, exercise=3, content="Real exact content.")],
        semantic_return=[]
    )

    plan = FakePlan(
        "fetch_exact_section", True,
        exact_location={"page": 24, "exercise": 3}
    )

    bundle = retriever.retrieve(plan)

    assert bundle.found is True
    assert bundle.hybrid_fallback_used is False

    semantic_retriever.retrieve.assert_not_called()


def test_both_exact_and_fallback_failing_returns_not_found_gracefully():

    retriever, _ = _make_retriever(
        exact_return=[FakeExactResult(found=False, page=99)],
        semantic_return=[]
    )

    plan = FakePlan("fetch_exact_section", True, exact_location={"page": 99})

    bundle = retriever.retrieve(plan)

    assert bundle.found is False
    assert bundle.hybrid_fallback_used is False


def test_no_semantic_retriever_configured_skips_fallback_without_crashing():

    metadata_engine = MagicMock()

    exact_retriever = MagicMock()

    exact_retriever.retrieve.return_value = [FakeExactResult(found=False, page=99)]

    retriever = Retriever(metadata_engine, exact_retriever, semantic_retriever=None)

    plan = FakePlan("fetch_exact_section", True, exact_location={"page": 99})

    bundle = retriever.retrieve(plan)

    assert bundle.found is False
    assert bundle.hybrid_fallback_used is False