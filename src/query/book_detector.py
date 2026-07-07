import json
import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple


class BookDetector:
    """
    Detects which book(s) the user is referring to using
    knowledge_index.json.
    """

    def __init__(
        self,
        knowledge_file: str = "data/knowledge_index.json"
    ):

        self.knowledge_file = Path(knowledge_file)
        self.books = self._load_books()

    # -------------------------------------------------

    def _load_books(self) -> List[Dict]:

        if not self.knowledge_file.exists():
            raise FileNotFoundError(
                f"{self.knowledge_file} not found."
            )

        with open(
            self.knowledge_file,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    # -------------------------------------------------

    @staticmethod
    def _normalize(text: str) -> str:

        text = text.lower()

        text = text.replace("_", " ")

        text = re.sub(r"[^\w\s]", " ", text)

        text = re.sub(r"\s+", " ", text)

        return text.strip()

    # -------------------------------------------------

    def _candidates(self, book: Dict):
        """
        All strings that can identify this book in a query, from
        most specific to least: aliases/title/filename (exact book,
        including level) down to the bare series name (any book in
        that series). Bare series is included so that a query like
        "Show me Cosmopolite" or "Compare Cosmopolite and Tendances"
        -- which never spells out a level -- still matches something.
        """

        aliases = book.get("aliases", [])

        title = book.get("title", "")

        filename = book.get("filename", "")

        series = book.get("series", "")

        return aliases + [title, filename, series]

    # -------------------------------------------------

    def detect(
        self,
        query: str,
        book_type_hint: Optional[str] = None,
        level_hint: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Best single match -- used when the query refers to one book.

        book_type_hint / level_hint: the already-detected book_type/
        level for this query (from BookTypeDetector/LevelDetector),
        if any. Callers should run those BEFORE this and pass their
        results here.

        Tie-breaking: when multiple books tie on match score (e.g.
        "Cosmopolite A2" matches "Cosmopolite A1", "Cosmopolite A2
        guide", AND "Cosmopolite A2 main book" all equally via the
        bare-series candidate alone, since none of their specific
        aliases matched verbatim), narrow down in this order:
          1. level_hint, if given -- "A2" in the query should never
             resolve to an A1 book just because both tied on the
             bare series name.
          2. book_type_hint, if given -- e.g. "teacher guide" should
             resolve to the Teacher Guide, not the Student Book.
          3. Prefer the Student Book -- a bare level/series mention
             with no explicit type keyword almost always means the
             student's own book, not the Teacher Guide/Answer Key.
          4. Otherwise, first match found (stable, but arbitrary).
        """

        query = self._normalize(query)

        best_score = -1

        tied_matches = []

        for book in self.books:

            for candidate in self._candidates(book):

                candidate = self._normalize(candidate)

                if candidate and candidate in query:

                    score = len(candidate)

                    if score > best_score:

                        best_score = score

                        tied_matches = [book]

                    elif score == best_score:

                        tied_matches.append(book)

        if not tied_matches:

            return None

        return self._break_tie(tied_matches, book_type_hint, level_hint)

    # -------------------------------------------------

    @staticmethod
    def _break_tie(
        candidates: List[Dict],
        book_type_hint: Optional[str],
        level_hint: Optional[str]
    ) -> Dict:
        """
        Shared tie-breaking logic used by both detect() and
        detect_all(): level_hint > book_type_hint > Student Book
        default > first match. See detect()'s docstring for why.
        """

        if len(candidates) == 1:

            return candidates[0]

        if level_hint:

            by_level = [b for b in candidates if b.get("level") == level_hint]

            if by_level:

                candidates = by_level

        if len(candidates) > 1 and book_type_hint:

            by_type = [b for b in candidates if b.get("book_type") == book_type_hint]

            if by_type:

                candidates = by_type

        if len(candidates) > 1:

            student_books = [
                b for b in candidates
                if b.get("book_type") == "Student Book"
            ]

            if student_books:

                candidates = student_books

        return candidates[0]

    # -------------------------------------------------

    def detect_all(
        self,
        query: str,
        book_type_hint: Optional[str] = None,
        level_hint: Optional[str] = None
    ) -> List[Dict]:
        """
        All distinct books/series referenced in the query -- used
        for Comparison-type intents where more than one book or
        series may be mentioned (e.g. "Compare Cosmopolite and
        Tendances"). Returns at most one representative book per
        distinct series matched, using the same tie-breaking as
        detect() (level_hint > book_type_hint > Student Book default)
        when a series has multiple equally-specific matches.
        """

        query = self._normalize(query)

        tied_by_series: Dict[str, Tuple[int, List[Dict]]] = {}

        for book in self.books:

            series = book.get("series", "")

            for candidate in self._candidates(book):

                candidate = self._normalize(candidate)

                if candidate and candidate in query:

                    score = len(candidate)

                    current_score, current_list = tied_by_series.get(series, (-1, []))

                    if score > current_score:

                        tied_by_series[series] = (score, [book])

                    elif score == current_score:

                        current_list.append(book)

                        tied_by_series[series] = (current_score, current_list)

        results = [
            self._break_tie(books, book_type_hint, level_hint)
            for _, books in tied_by_series.values()
        ]

        results.sort(key=lambda b: len(b.get("series", "")), reverse=True)

        return results


# ---------------------------------------------------------

if __name__ == "__main__":

    detector = BookDetector()

    test_queries = [

        "Give me Cosmopolite A1 book",
        "I need cosmo a1",
        "Teach from book 1",
        "Open Tendances B1",
        "Complete French All in One",
        "Recommend Cosmopolite B2",
        "Show me Cosmopolite",
        "Compare Cosmopolite and Tendances"

    ]

    for q in test_queries:

        result = detector.detect(q)

        all_results = detector.detect_all(q)

        print("=" * 60)
        print("Query :", q)
        print("detect()     :", result["title"] if result else None)
        print("detect_all() :", [b["title"] for b in all_results])