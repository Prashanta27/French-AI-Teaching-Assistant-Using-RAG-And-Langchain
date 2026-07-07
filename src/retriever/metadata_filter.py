import json
from pathlib import Path
from typing import Any, Dict, List


class MetadataFilterEngine:
    """
    Applies a SearchPlan's `filters` dict against the book catalog
    (knowledge_index.json) to narrow the candidate set of books
    *before* ExactRetriever or SemanticRetriever ever run. Neither
    retriever should have to know how filters work, or read the
    catalog JSON themselves -- they just ask this engine for
    candidate book_ids / filepaths.
    """

    # Class-level cache keyed by resolved file path, so re-creating
    # the engine (e.g. on every Streamlit rerun) doesn't re-read and
    # re-parse the JSON every time.
    _CACHE: Dict[str, List[Dict]] = {}

    def __init__(
        self,
        knowledge_file: str = "data/knowledge_index.json"
    ):

        self.knowledge_file = Path(knowledge_file)

        self.books = self._load_books()

    # -------------------------------------------------

    def _load_books(self) -> List[Dict]:

        cache_key = str(self.knowledge_file.resolve())

        if cache_key in self._CACHE:

            return self._CACHE[cache_key]

        if not self.knowledge_file.exists():

            raise FileNotFoundError(
                f"{self.knowledge_file} not found."
            )

        with open(
            self.knowledge_file,
            "r",
            encoding="utf-8"
        ) as f:

            books = json.load(f)

        self._CACHE[cache_key] = books

        return books

    # -------------------------------------------------

    @classmethod
    def clear_cache(cls):
        """
        Call this after knowledge_index.json is rebuilt (e.g. after
        re-indexing new PDFs), otherwise the engine keeps serving the
        stale in-memory copy for the lifetime of the process.
        """

        cls._CACHE.clear()

    # -------------------------------------------------

    @staticmethod
    def _normalize(value: Any) -> str:

        # Case- and whitespace-insensitive comparison, so "A1" /
        # "a1", or "Teacher Guide" / "teacher   guide", are treated
        # as equal. Filter *values* here always come from our own
        # canonical detectors (LevelDetector, BookTypeDetector,
        # TopicDetector, ...), so this only guards against harmless
        # case/spacing drift -- it does not attempt fuzzy or partial
        # matching (see notes in `_matches`).
        return " ".join(str(value).lower().split())

    # -------------------------------------------------

    def _matches(self, book: Dict, key: str, value: Any) -> bool:

        book_value = book.get(key)

        if isinstance(value, list):

            # OR logic within a list-valued filter -- e.g.
            # {"series": ["Cosmopolite", "Tendances"]} from a
            # Comparison-intent SearchPlan should match either.
            return self._normalize(book_value) in {

                self._normalize(v) for v in value

            }

        # NOTE: intentionally exact (post-normalization) equality,
        # not substring ("in") matching. Filter values here are
        # canonical enums produced upstream by LevelDetector /
        # BookTypeDetector / TopicDetector -- not raw user text --
        # so partial matching isn't needed, and it would reintroduce
        # the exact collision problem BookTypeDetector already had
        # to fix (a bare "guide"/"b1"-style substring silently
        # matching things it shouldn't, e.g. "B1" matching a future
        # "B10", or "Guide" matching "Guide pédagogique" when only
        # "Teacher Guide" was intended).
        return self._normalize(book_value) == self._normalize(value)

    # -------------------------------------------------

    def apply(self, filters: Dict[str, Any]) -> List[Dict]:
        """
        AND across filter keys, OR within any single list-valued
        filter. An empty (or all-None) filters dict returns every
        book in the catalog -- this matches SearchPlan's convention
        that "no filters" means "search everything", not "search
        nothing".
        """

        candidates = self.books

        for key, value in filters.items():

            if value is None:

                continue

            candidates = [

                book
                for book in candidates
                if self._matches(book, key, value)

            ]

        return candidates

    # -------------------------------------------------

    def apply_plan(self, plan) -> List[Dict]:
        """
        Convenience wrapper: pull `.filters` straight off a
        SearchPlan object instead of the caller extracting it first.
        """

        return self.apply(plan.filters)

    # -------------------------------------------------

    def get_book_ids(self, filters: Dict[str, Any]) -> List[str]:

        return [book["book_id"] for book in self.apply(filters)]

    # -------------------------------------------------

    def get_filepaths(self, filters: Dict[str, Any]) -> List[str]:

        return [book["filepath"] for book in self.apply(filters)]

    # -------------------------------------------------

    def get_book_map(self, filters: Dict[str, Any]) -> Dict[str, Dict]:

        return {

            book["book_id"]: book
            for book in self.apply(filters)

        }

    # -------------------------------------------------

    def count(self, filters: Dict[str, Any]) -> int:

        return len(self.apply(filters))


# ---------------------------------------------------------
# Testing
# ---------------------------------------------------------

if __name__ == "__main__":

    engine = MetadataFilterEngine()

    test_cases = [

        {},
        {"series": "Cosmopolite"},
        {"series": "cosmopolite"},           # case-insensitivity
        {"book_type": "teacher   guide"},    # spacing-insensitivity
        {"series": "Cosmopolite", "level": "A1", "book_type": "Workbook"},
        {"series": ["Cosmopolite", "Tendances"]},
        {"level": "C1"},

    ]

    for filters in test_cases:

        print("=" * 60)
        print("Filters :", filters)
        print("Matches :", [b["title"] for b in engine.apply(filters)])

    print("=" * 60)
    print("get_book_ids  :", engine.get_book_ids({"series": "Tendances"}))
    print("get_filepaths :", engine.get_filepaths({"series": "Tendances"}))
    print("get_book_map  :", {
        k: v["title"] for k, v in engine.get_book_map({"series": "Tendances"}).items()
    })

    # cache check -- second instantiation should not re-read the file
    engine2 = MetadataFilterEngine()
    print("=" * 60)
    print("Same cached object? ", engine.books is engine2.books)