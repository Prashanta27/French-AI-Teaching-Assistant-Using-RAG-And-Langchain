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

    def detect(self, query: str) -> Optional[Dict]:
        """
        Best single match -- used when the query refers to one book.
        """

        query = self._normalize(query)

        best_match = None

        best_score = -1

        for book in self.books:

            for candidate in self._candidates(book):

                candidate = self._normalize(candidate)

                if candidate and candidate in query:

                    score = len(candidate)

                    if score > best_score:

                        best_score = score

                        best_match = book

        return best_match

    # -------------------------------------------------

    def detect_all(self, query: str) -> List[Dict]:
        """
        All distinct books/series referenced in the query -- used
        for Comparison-type intents where more than one book or
        series may be mentioned (e.g. "Compare Cosmopolite and
        Tendances"). Returns at most one representative book per
        distinct series matched, picking the most specific match
        available for that series.
        """

        query = self._normalize(query)

        best_per_series: Dict[str, Tuple[int, Dict]] = {}

        for book in self.books:

            series = book.get("series", "")

            for candidate in self._candidates(book):

                candidate = self._normalize(candidate)

                if candidate and candidate in query:

                    score = len(candidate)

                    current = best_per_series.get(series)

                    if current is None or score > current[0]:

                        best_per_series[series] = (score, book)

        results = [book for _, book in best_per_series.values()]

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