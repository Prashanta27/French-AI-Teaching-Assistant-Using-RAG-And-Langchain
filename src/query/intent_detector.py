import re
from typing import Optional, List, Dict


# "Action" intents: these describe WHAT the user wants done with
# content, and always take priority over generic retrieval --
# even when a chapter/page/exercise number is also present.
# e.g. "Explain chapter 2 grammar" is Explanation, not RetrieveChapter.
ACTION_INTENTS: Dict[str, List[str]] = {

    "Greeting": [
        "hi",
        "hello",
        "hey",
        "good morning",
        "good evening",
        "how are you",
        "salut",
        "bonjour"
    ],

    "Recommendation": [
        "recommend",
        "suggest",
        "which book",
        "best book",
        "should i use",
        "what should i study",
        "any suggestion"
    ],

    "Comparison": [
        "compare",
        "comparison",
        "difference between",
        "versus",
        " vs ",
        "which is better",
        "better than"
    ],

    # Asking the AI to check/mark/grade something the user produced,
    # as opposed to asking for new material (that's Practice).
    "Correction": [
        "correct my",
        "correct this",
        "check my",
        "evaluate my",
        "evaluate",
        "review my",
        "give me feedback",
        "mark my"
    ],

    "Translation": [
        "translate",
        "traduire",
        "translation",
        "in english",
        "in french",
        "en anglais",
        "en français",
        "en francais"
    ],

    "Summary": [
        "summarize",
        "summarise",
        "summary",
        "overview",
        "brief me",
        "give me a brief",
        "tl;dr"
    ],

    # NOTE: bare "exercise" is deliberately excluded -- "Exercise 4
    # page 32" is a structural reference (handled by
    # StructureDetector), not a request to practice. Only phrases
    # that clearly ask for practice material are included here.
    "Practice": [
        "practice",
        "quiz",
        "test me",
        "give me an exercise",
        "give me a quiz",
        "practice exercise",
        "do an exercise",
        "drill",
        "worksheet",
        "solve",
        "answer"
    ],

    "Explanation": [
        "explain with examples",
        "explain simply",
        "explain",
        "what is",
        "what does",
        "how does",
        "define",
        "definition of",
        "meaning of",
        "clarify",
        "difference",
        "teach me",
        "teach",
        "learn",
        "study"
    ],

    "Navigation": [
        "next chapter",
        "previous chapter",
        "next page",
        "previous page",
        "go to chapter",
        "go to page",
        "continue from",
        "start from"
    ]

}

# Generic verbs that signal "the user wants something delivered/
# shown", but don't by themselves say WHAT granularity. The actual
# Book / Chapter / Page / Exercise / Line target is resolved from
# StructureDetector (and book detection) output in detect().
RETRIEVAL_TRIGGERS: List[str] = [
    "give me",
    "get me",
    "send me",
    "download",
    "show me the book",
    "i want the book",
    "share the pdf",
    "provide the book",
    "show",
    "display",
    "read",
    "open",
    "retrieve",
    "locate",
    "find",
    "generate",
    "create"
]

_RETRIEVAL_TRIGGER_TAG = "__RetrievalTrigger__"


class IntentDetector:
    """
    Detect the user's underlying intent.

    Two layers:
      1. Action intents (Explain/Summarize/Translate/Practice/...)
         detected purely from keywords -- these always win.
      2. Retrieval intents (RetrieveBook/Chapter/Page/Exercise/Line)
         resolved from StructureDetector output (and book presence)
         when no action intent applies, whether or not a generic
         retrieval verb ("give me", "show", ...) was used.
    """

    DEFAULT_INTENT = "GeneralQuery"

    # Finest-grained first: if multiple structure fields are present
    # (e.g. both chapter and page), the most specific one wins.
    _STRUCTURE_PRIORITY = ["line", "exercise", "page", "chapter"]

    def __init__(self):

        pairs = []

        for intent, phrases in ACTION_INTENTS.items():

            for phrase in phrases:

                pairs.append((phrase, intent))

        for phrase in RETRIEVAL_TRIGGERS:

            pairs.append((phrase, _RETRIEVAL_TRIGGER_TAG))

        # Longest phrase first, so specific multi-word phrases
        # (e.g. "give me an exercise") win over shorter generic
        # triggers (e.g. "give me").
        self.pairs = sorted(

            pairs,

            key=lambda p: len(p[0]),

            reverse=True

        )

    @staticmethod
    def _normalize(text: str):

        text = text.lower()

        text = re.sub(r'[-_:]', ' ', text)

        text = re.sub(r'\s+', ' ', text)

        return f" {text.strip()} "

    def _matches(self, phrase: str, query: str) -> bool:

        if " " in phrase.strip():

            return phrase in query

        return re.search(rf'\b{re.escape(phrase)}\b', query) is not None

    def _match_action_or_trigger(self, query: str) -> Optional[str]:

        for phrase, label in self.pairs:

            if self._matches(phrase, query):

                return label

        return None

    def _resolve_retrieval(
        self,
        structure: Optional[dict],
        has_book: bool
    ) -> Optional[str]:

        structure = structure or {}

        for field in self._STRUCTURE_PRIORITY:

            if structure.get(field) is not None:

                return f"Retrieve{field.capitalize()}"

        if has_book:

            return "RetrieveBook"

        return None

    def detect(
        self,
        query: str,
        structure: Optional[dict] = None,
        has_book: bool = False
    ) -> str:
        """
        query: the raw user query.
        structure: optional dict from StructureDetector, e.g.
            {"chapter": 2, "page": None, "exercise": None, "line": None}
        has_book: whether a book was already identified in the query
            (from BookDetector), used only when no chapter/page/
            exercise/line is present.
        """

        normalized = self._normalize(query)

        matched = self._match_action_or_trigger(normalized)

        if matched is not None and matched != _RETRIEVAL_TRIGGER_TAG:

            # A real action intent (Explain/Summarize/Translate/...)
            # always takes priority, even if structure is present.
            return matched

        # Either a generic retrieval trigger matched, or nothing
        # matched at all -- in both cases, let structure/book
        # presence decide the granularity. This is what makes
        # "Cosmopolite A1 chapter 2" resolve to RetrieveChapter
        # even though it contains no verb at all.
        resolved = self._resolve_retrieval(structure, has_book)

        if resolved is not None:

            return resolved

        if matched == _RETRIEVAL_TRIGGER_TAG:

            # A retrieval verb was used but nothing specific was
            # identified to retrieve -- default to whole-book intent.
            return "RetrieveBook"

        return self.DEFAULT_INTENT

    def detect_all(self, query: str) -> List[str]:
        """
        Keyword-only view (no structure/book fallback) -- useful for
        debugging or when multiple action intents are mixed together.
        """

        query = self._normalize(query)

        found = []

        for phrase, label in self.pairs:

            if self._matches(phrase, query):

                intent = "Retrieval" if label == _RETRIEVAL_TRIGGER_TAG else label

                if intent not in found:
                    found.append(intent)

        return found if found else [self.DEFAULT_INTENT]


# -------------------------------------------------------

if __name__ == "__main__":

    from structure_detector import StructureDetector

    intent_detector = IntentDetector()
    structure_detector = StructureDetector()

    # (query, has_book) -- has_book simulates BookDetector output
    test_cases = [
        ("Cosmopolite A1 chapter 2", True),
        ("Give me Cosmopolite chapter 2 page 34", True),
        ("Explain chapter 2 grammar", True),
        ("Summarize chapter 2", False),
        ("Translate page 33", False),
        ("Exercise 4 page 32", False),
        ("I want to practice grammar", False),
        ("Give me an exercise on verbs", False),
        ("Teach me the subjunctive", False),
        ("Show me chapter 3", True),
        ("Continue from chapter 5", True),
        ("Correct my essay", False),
        ("Check my answers", False),
        ("Give me the Cosmopolite A1 book", True),
        ("Download the teacher guide", True),
        ("Recommend a beginner book", False),
        ("Compare Cosmopolite and Tendances", False),
        ("Hello, how are you?", False),
        ("asdkjasd random text", False),
    ]

    for query, has_book in test_cases:

        structure = structure_detector.detect(query)

        intent = intent_detector.detect(
            query,
            structure=structure,
            has_book=has_book
        )

        print(f"{query!r:45} -> {intent}")