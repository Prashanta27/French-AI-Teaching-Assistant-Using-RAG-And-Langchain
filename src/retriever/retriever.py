"""
Retriever
=========

Unified retrieval dispatcher. Given a SearchPlan, decides which
underlying mechanism actually answers it -- MetadataFilterEngine
(catalog-only), ExactRetriever (deterministic chapter/page/exercise/
line lookup), or SemanticRetriever (embedding search) -- and returns
both a ready-to-use context string (for the prompt) and the raw
result objects (for anything that wants structured data, e.g.
showing sources/citations in a UI, not just a text blob).

This is the single place that knows "SearchPlan.action X maps to
retrieval mechanism Y" -- callers (LLMGenerator, an API endpoint that
just wants retrieved passages, tests, ...) don't need to know that
mapping themselves.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, List

from src.retriever.metadata_filter import MetadataFilterEngine
from src.retriever.exact_retriever import ExactRetriever
from src.retriever.semantic_retriever import SemanticRetriever


logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Result bundle
# ---------------------------------------------------------

@dataclass
class RetrievalBundle:

    action: str

    found: bool

    context: str
    # Formatted, ready to drop straight into a prompt.

    raw_results: List[Any] = field(default_factory=list)
    # The underlying ExactRetrievalResult / SemanticRetrievalResult
    # list, or raw book dicts for fetch_metadata, or [] for
    # no_search -- kept around so a caller that wants structured
    # data (source titles/pages for a citation UI, for example)
    # isn't stuck re-parsing the formatted context string.


# ---------------------------------------------------------
# Retriever
# ---------------------------------------------------------

class Retriever:

    def __init__(
        self,
        metadata_engine: MetadataFilterEngine,
        exact_retriever: ExactRetriever,
        semantic_retriever: SemanticRetriever
    ):

        self.metadata_engine = metadata_engine

        self.exact_retriever = exact_retriever

        self.semantic_retriever = semantic_retriever

    # -----------------------------------------------------
    # Public API
    # -----------------------------------------------------

    def retrieve(self, plan) -> RetrievalBundle:

        if not plan.needs_retrieval:

            logger.debug("action=%s needs no retrieval.", plan.action)

            return RetrievalBundle(action=plan.action, found=False, context="")

        if plan.action == "fetch_metadata":

            return self._retrieve_metadata(plan)

        if plan.action == "fetch_exact_section":

            return self._retrieve_exact(plan)

        if plan.action in ("semantic_search", "multi_book_semantic_search"):

            return self._retrieve_semantic(plan)

        logger.warning(
            "Unrecognized SearchPlan.action '%s' -- treating as no retrieval.",
            plan.action
        )

        return RetrievalBundle(action=plan.action, found=False, context="")

    # -----------------------------------------------------

    def _retrieve_metadata(self, plan) -> RetrievalBundle:

        books = self.metadata_engine.apply(plan.filters)

        return RetrievalBundle(
            action=plan.action,
            found=bool(books),
            context=self._format_books(books),
            raw_results=books
        )

    # -----------------------------------------------------

    def _retrieve_exact(self, plan) -> RetrievalBundle:

        results = self.exact_retriever.retrieve(plan)

        context, found = self._format_exact(results)

        return RetrievalBundle(
            action=plan.action,
            found=found,
            context=context,
            raw_results=results
        )

    # -----------------------------------------------------

    def _retrieve_semantic(self, plan) -> RetrievalBundle:

        results = self.semantic_retriever.retrieve(plan)

        context, found = self._format_semantic(results)

        return RetrievalBundle(
            action=plan.action,
            found=found,
            context=context,
            raw_results=results
        )

    # -----------------------------------------------------
    # Formatting
    # -----------------------------------------------------

    @staticmethod
    def _format_books(books) -> str:

        if not books:

            return ""

        blocks = [
            f"- {b.get('title')} "
            f"(Series: {b.get('series')}, Level: {b.get('level')}, "
            f"Type: {b.get('book_type')})"
            for b in books
        ]

        return "Matching books:\n" + "\n".join(blocks)

    # -----------------------------------------------------

    @staticmethod
    def _format_exact(results) -> "tuple[str, bool]":

        blocks = []

        any_found = False

        for r in results:

            if not r.found:

                continue

            any_found = True

            location_bits = [
                f"Page {r.page}" if r.page else None,
                f"Chapter {r.chapter}" if r.chapter else None,
                f"Exercise {r.exercise}" if r.exercise else None,
                f"Activity {r.activity}" if r.activity else None,
                f"Line {r.line}" if r.line else None,
            ]

            location = ", ".join(b for b in location_bits if b)

            blocks.append(f"Source: {r.title} ({location})\n{r.content}")

        return "\n\n---\n\n".join(blocks), any_found

    # -----------------------------------------------------

    @staticmethod
    def _format_semantic(results) -> "tuple[str, bool]":

        blocks = []

        any_found = False

        for r in results:

            if not r.found:

                continue

            any_found = True

            page_note = f" (page {r.page})" if r.page is not None else ""

            blocks.append(
                f"[{r.title}{page_note}, relevance {r.score:.2f}]\n{r.content}"
            )

        return "\n\n---\n\n".join(blocks), any_found


# ---------------------------------------------------------
# Testing
# ---------------------------------------------------------

if __name__ == "__main__":

    from unittest.mock import MagicMock

    class FakeExactResult:
        def __init__(self, found, title=None, page=None, chapter=None,
                     exercise=None, activity=None, line=None, content=None):
            self.found, self.title, self.page = found, title, page
            self.chapter, self.exercise, self.activity, self.line = chapter, exercise, activity, line
            self.content = content

    class FakeSemanticResult:
        def __init__(self, found, title=None, page=None, score=0.0, content=None):
            self.found, self.title, self.page, self.score, self.content = found, title, page, score, content

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

    metadata_engine = MagicMock()
    exact_retriever = MagicMock()
    semantic_retriever = MagicMock()

    retriever = Retriever(metadata_engine, exact_retriever, semantic_retriever)

    # 1. no_search
    bundle = retriever.retrieve(FakePlan("no_search", needs_retrieval=False))
    assert bundle.found is False and bundle.context == ""
    metadata_engine.apply.assert_not_called()
    print("PASS: no_search skips everything")

    # 2. fetch_metadata
    metadata_engine.apply.return_value = [{"title": "Cosmopolite A1", "series": "Cosmopolite",
                                            "level": "A1", "book_type": "Student Book"}]
    bundle = retriever.retrieve(FakePlan("fetch_metadata", needs_retrieval=True, filters={"level": "A1"}))
    assert bundle.found and "Cosmopolite A1" in bundle.context
    assert bundle.raw_results == metadata_engine.apply.return_value
    print("PASS: fetch_metadata returns formatted context + raw books")

    # 3. fetch_exact_section
    exact_retriever.retrieve.return_value = [
        FakeExactResult(found=True, title="Cosmopolite A1", page=2, content="Bonjour tout le monde.")
    ]
    bundle = retriever.retrieve(FakePlan("fetch_exact_section", needs_retrieval=True, exact_location={"page": 2}))
    assert bundle.found and "Bonjour" in bundle.context
    print("PASS: fetch_exact_section dispatches to ExactRetriever")

    # 4. semantic_search
    semantic_retriever.retrieve.return_value = [
        FakeSemanticResult(found=True, title="Cosmopolite B2", page=45, score=0.91, content="Le subjonctif...")
    ]
    bundle = retriever.retrieve(FakePlan("semantic_search", needs_retrieval=True, search_text="explain subjunctive"))
    assert bundle.found and "0.91" in bundle.context
    print("PASS: semantic_search dispatches to SemanticRetriever")

    # 5. multi_book_semantic_search also routes to SemanticRetriever
    bundle = retriever.retrieve(FakePlan("multi_book_semantic_search", needs_retrieval=True,
                                          target_books=["Cosmopolite A1", "Tendances B1"]))
    assert semantic_retriever.retrieve.call_count == 2
    print("PASS: multi_book_semantic_search also dispatches to SemanticRetriever")

    # 6. unknown action -- shouldn't crash
    bundle = retriever.retrieve(FakePlan("something_unexpected", needs_retrieval=True))
    assert bundle.found is False and bundle.context == ""
    print("PASS: unknown action degrades gracefully")

    print("\nALL DISPATCHER TESTS PASSED")