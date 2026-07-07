from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List

from src.query.book_detector import BookDetector
from src.query.level_detector import LevelDetector
from src.query.book_type_detector import BookTypeDetector
from src.query.structure_detector import StructureDetector
from src.query.topic_detector import TopicDetector
from src.query.intent_detector import IntentDetector


# ---------------------------------------------------------
# Query Object
# ---------------------------------------------------------

@dataclass
class QueryAnalysis:

    original_query: str

    intent: str

    book: Optional[str]           # primary/best-matched book title
    books: List[str]              # all books referenced (for Comparison)

    level: Optional[str]

    book_type: Optional[str]

    topic: Optional[str]

    chapter: Optional[int]

    page: Optional[int]

    exercise: Optional[int]

    activity: Optional[int]

    line: Optional[int]

    metadata_filters: Dict[str, Any]

    def to_dict(self):

        return asdict(self)


# ---------------------------------------------------------
# Query Analyzer
# ---------------------------------------------------------

class QueryAnalyzer:

    """
    Main Query Analyzer.

    Combines all detectors into one structured query.
    """

    def __init__(self):

        self.book_detector = BookDetector()

        self.level_detector = LevelDetector()

        self.book_type_detector = BookTypeDetector()

        self.structure_detector = StructureDetector()

        self.topic_detector = TopicDetector()

        self.intent_detector = IntentDetector()

    # -----------------------------------------------------

    def analyze(self, query: str) -> QueryAnalysis:

        # ---------------------------
        # Book(s)
        #
        # book_detector now returns a full book dict (title, series,
        # level, book_type, ...), not a bare string. detect_all()
        # additionally returns every distinct series referenced --
        # needed for Comparison-type queries ("Compare Cosmopolite
        # and Tendances"), where detect() alone would only surface
        # one of the two.
        # ---------------------------

        # Detect an explicit book_type signal (e.g. "teacher guide")
        # BEFORE book detection, so BookDetector can use it to break
        # ties between same-level/series books of different types
        # (e.g. "Cosmopolite A2" alone matches both the guide and
        # the main book equally -- the explicit hint decides which).
        book_type_query_hint = self.book_type_detector.detect(query)

        level_query_hint = self.level_detector.detect(query)

        best_book = self.book_detector.detect(
            query,
            book_type_hint=book_type_query_hint,
            level_hint=level_query_hint
        )

        all_books = self.book_detector.detect_all(
            query,
            book_type_hint=book_type_query_hint,
            level_hint=level_query_hint
        )

        has_book = best_book is not None

        book_title = best_book["title"] if best_book else None

        book_titles = [b["title"] for b in all_books]

        # ---------------------------
        # Level
        #
        # Prefer whatever the query text explicitly states. If the
        # query names a specific book but no level keyword ("Complete
        # French All in One"), fall back to that book's own indexed
        # level rather than leaving it unset.
        # ---------------------------

        is_single_book_context = len(all_books) <= 1

        level = level_query_hint

        if level is None and best_book and is_single_book_context:

            level = best_book.get("level")

        # ---------------------------
        # Book Type
        #
        # Same fallback logic as level: trust explicit query text
        # first, then the matched book's own indexed type -- but
        # only when exactly one book is in play. In a Comparison
        # query (multiple books/series), the arbitrary "best" match
        # must not silently inject its level/type as a filter.
        # ---------------------------

        book_type = book_type_query_hint

        if book_type is None and best_book and is_single_book_context:

            book_type = best_book.get("book_type")

        # ---------------------------
        # Structure
        # ---------------------------

        structure = self.structure_detector.detect(query)

        # ---------------------------
        # Topic
        # ---------------------------

        topic = self.topic_detector.detect(query)

        # ---------------------------
        # Intent
        # ---------------------------

        intent = self.intent_detector.detect(

            query,

            structure=structure,

            has_book=has_book

        )

        # ---------------------------
        # Metadata Filter
        # ---------------------------

        metadata_filters = {}

        if len(all_books) > 1:

            # Comparison-style query: filter across every referenced
            # series rather than collapsing to just one.
            metadata_filters["series"] = [b["series"] for b in all_books]

        elif best_book:

            metadata_filters["series"] = best_book["series"]

        if level:

            metadata_filters["level"] = level

        if book_type:

            metadata_filters["book_type"] = book_type

        if topic != "General French":

            metadata_filters["category"] = topic

        # ---------------------------

        return QueryAnalysis(

            original_query=query,

            intent=intent,

            book=book_title,

            books=book_titles,

            level=level,

            book_type=book_type,

            topic=topic,

            chapter=structure.get("chapter"),

            page=structure.get("page"),

            exercise=structure.get("exercise"),

            activity=structure.get("activity"),

            line=structure.get("line"),

            metadata_filters=metadata_filters

        )


# ---------------------------------------------------------
# Testing
# ---------------------------------------------------------

if __name__ == "__main__":

    analyzer = QueryAnalyzer()

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
        "Teach me pronunciation"

    ]

    for query in queries:

        print("=" * 70)

        result = analyzer.analyze(query)

        for k, v in result.to_dict().items():

            print(f"{k:18}: {v}")