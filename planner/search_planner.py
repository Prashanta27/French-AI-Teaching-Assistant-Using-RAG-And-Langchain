from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List

from src.query.query_analyzer import QueryAnalysis


# ---------------------------------------------------------
# Search Plan Object
# ---------------------------------------------------------

@dataclass
class SearchPlan:

    action: str
    # One of:
    #   "no_search"                 -- pure LLM response, no retrieval
    #   "fetch_metadata"            -- catalog lookup (no chunk search)
    #   "fetch_exact_section"       -- deterministic chapter/page/
    #                                  exercise/activity/line lookup
    #   "semantic_search"           -- embedding search within filters
    #   "multi_book_semantic_search" -- semantic search run once per
    #                                   referenced book (Comparison)

    filters: Dict[str, Any]

    search_text: str

    top_k: int

    target_books: List[str]
    # Empty list means "no specific book identified -- search across
    # the whole catalog", NOT "search zero books". See `notes`, which
    # spells this out whenever target_books is empty and a search is
    # actually happening.

    exact_location: Dict[str, int]

    needs_retrieval: bool
    # False only for actions that skip the knowledge base entirely
    # ("no_search"). True for everything else -- the Retriever can
    # branch on this directly instead of inspecting `action` itself.

    llm_task: str
    # What the LLM should actually do with whatever content comes
    # back (or with no content, for no_search actions). Drives the
    # downstream prompt builder so it doesn't need to re-derive this
    # from `action`/intent itself.

    notes: str = ""

    def to_dict(self):

        return asdict(self)


# ---------------------------------------------------------
# Search Planner
# ---------------------------------------------------------

class SearchPlanner:
    """
    Turns a QueryAnalysis (intent + book/level/type/topic/structure)
    into a concrete retrieval plan the Retriever can execute directly,
    without needing to re-interpret intent itself.
    """

    # Default action per intent. "fetch_exact_section" here means
    # "prefer an exact chapter/page/exercise/activity/line lookup if
    # one was given" -- if none was given, plan() falls back to
    # "semantic_search" so the request still returns something.
    INTENT_ACTION_MAP = {

        "RetrieveBook": "fetch_metadata",
        "RetrieveChapter": "fetch_exact_section",
        "RetrievePage": "fetch_exact_section",
        "RetrieveExercise": "fetch_exact_section",
        "RetrieveLine": "fetch_exact_section",

        "Explanation": "semantic_search",
        "Practice": "semantic_search",
        "Summary": "fetch_exact_section",
        "Translation": "fetch_exact_section",

        "Comparison": "multi_book_semantic_search",
        "Recommendation": "fetch_metadata",

        "Navigation": "fetch_exact_section",

        "Correction": "no_search",
        "Greeting": "no_search",

        "GeneralQuery": "semantic_search"

    }

    TOP_K_BY_ACTION = {

        "no_search": 0,
        "fetch_metadata": 5,
        "fetch_exact_section": 1,
        "semantic_search": 5,
        "multi_book_semantic_search": 3

    }

    # What the LLM should do with the retrieved (or absent) content.
    # Kept separate from `action` (a retrieval instruction) so the
    # prompt builder never has to re-derive intent from it.
    INTENT_LLM_TASK_MAP = {

        "RetrieveBook": "Present Book Info",
        "RetrieveChapter": "Present Chapter Content",
        "RetrievePage": "Present Page Content",
        "RetrieveExercise": "Present Exercise",
        "RetrieveLine": "Present Line",

        "Explanation": "Explain",
        "Summary": "Summarize",
        "Translation": "Translate",
        "Practice": "Generate Exercise",
        "Comparison": "Compare",
        "Recommendation": "Recommend",
        "Navigation": "Navigate",
        "Correction": "Correct",
        "Greeting": "Greet",

        "GeneralQuery": "Answer"

    }

    DEFAULT_LLM_TASK = "Answer"

    # -----------------------------------------------------

    def _exact_location(self, analysis: QueryAnalysis) -> Dict[str, int]:

        location = {

            "chapter": analysis.chapter,
            "page": analysis.page,
            "exercise": analysis.exercise,
            "activity": analysis.activity,
            "line": analysis.line

        }

        return {k: v for k, v in location.items() if v is not None}

    # -----------------------------------------------------

    def _build_search_text(self, analysis: QueryAnalysis) -> str:

        # Lead with the detected topic (if any) so the embedding
        # search is anchored on subject matter, not just the raw
        # phrasing -- then include the original query for the
        # specifics the topic label alone would lose. Plain
        # space-joining (no punctuation) tends to embed slightly
        # better than a "Topic: query" string.
        if analysis.topic and analysis.topic != "General French":

            return f"{analysis.topic} {analysis.original_query}"

        return analysis.original_query

    # -----------------------------------------------------

    def _target_books(self, analysis: QueryAnalysis, action: str) -> List[str]:

        if action == "multi_book_semantic_search":

            return list(analysis.books)

        if analysis.book:

            return [analysis.book]

        return []

    # -----------------------------------------------------

    def plan(self, analysis: QueryAnalysis) -> SearchPlan:

        action = self.INTENT_ACTION_MAP.get(analysis.intent, "semantic_search")

        exact_location = self._exact_location(analysis)

        notes = ""

        # "fetch_exact_section" only makes sense if we actually have
        # a chapter/page/exercise/activity/line to anchor on. Without
        # one (e.g. "Summarize the book" with no chapter given), fall
        # back to a semantic search over whatever filters we do have
        # so the request still returns useful content.
        if action == "fetch_exact_section" and not exact_location:

            action = "semantic_search"

            notes = (
                "No exact chapter/page/exercise/activity/line was "
                "found in the query -- falling back to semantic "
                "search within the detected filters."
            )

        # Comparison needs at least two distinct books/series to be
        # meaningful. If detection only found one, there is nothing
        # to compare -- degrade gracefully to a normal semantic
        # search rather than running a pointless "comparison".
        if action == "multi_book_semantic_search" and len(analysis.books) < 2:

            action = "semantic_search"

            notes = (
                "Comparison intent detected, but fewer than two "
                "books/series were identified -- falling back to a "
                "single semantic search."
            )

        target_books = self._target_books(analysis, action)

        if not target_books and action in ("semantic_search", "fetch_metadata"):

            notes = (notes + " " if notes else "") + (
                "target_books is empty, meaning no specific book was "
                "identified -- search across the full catalog, not "
                "zero books."
            )

        llm_task = self.INTENT_LLM_TASK_MAP.get(analysis.intent, self.DEFAULT_LLM_TASK)

        return SearchPlan(

            action=action,

            # Copied so the Retriever can freely mutate its own copy
            # without side-effecting the QueryAnalysis this plan was
            # built from.
            filters=dict(analysis.metadata_filters),

            search_text=self._build_search_text(analysis),

            top_k=self.TOP_K_BY_ACTION.get(action, 5),

            target_books=target_books,

            exact_location=exact_location,

            needs_retrieval=(action != "no_search"),

            llm_task=llm_task,

            notes=notes.strip()

        )


# ---------------------------------------------------------
# Testing
# ---------------------------------------------------------

if __name__ == "__main__":

    from src.query.query_analyzer import QueryAnalyzer

    analyzer = QueryAnalyzer()
    planner = SearchPlanner()

    queries = [

        "Give me Cosmopolite A1 chapter 2",
        "Explain chapter 3 grammar",
        "Translate page 45",
        "Give me page 50 line 8",
        "Recommend a beginner book",
        "Show me Tendances B1 workbook",
        "Exercise 4 page 32",
        "Summarize chapter 5",
        "Compare Cosmopolite and Tendances",
        "Teach me pronunciation",
        "Correct my essay",
        "Hello, how are you?",
        "Summarize the book"

    ]

    for query in queries:

        print("=" * 70)

        analysis = analyzer.analyze(query)

        plan = planner.plan(analysis)

        print("Query:", query)
        print("Intent:", analysis.intent)

        for k, v in plan.to_dict().items():

            print(f"  {k:15}: {v}")