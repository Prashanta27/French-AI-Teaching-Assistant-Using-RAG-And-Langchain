import re
from typing import Optional


class BookTypeDetector:
    """
    Detects the requested book type from a user query.

    Supported Types
    ----------------
    • Student Book
    • Teacher Guide
    • Workbook
    • Answer Key
    • Transcription
    """

    BOOK_TYPE_ALIASES = {

        "Student Book": [

            "student book",
            "student",
            "main book",
            "course book",
            "textbook",
            "livre",
            "livre de l'élève",
            "livre de l eleve",
            "manuel"

        ],

        "Teacher Guide": [

            "teacher guide",
            "teacher's guide",
            "teacher book",
            "teacher manual",
            "professor book",
            # NOTE: bare "guide" / "teacher" / "professor" removed --
            # they collide with generic phrases like "guide me
            # through chapter 2" (a navigation request) or plain
            # mentions of a teacher/professor unrelated to book type.
            # Multi-word phrases below are specific enough to keep.
            "guide pédagogique",
            "guide pedagogique",
            "livre du professeur",
            "professeur"

        ],

        "Workbook": [

            "workbook",
            "exercise book",
            # NOTE: bare "exercise" removed -- StructureDetector /
            # IntentDetector already treat bare "exercise" as a
            # structural reference (e.g. "Exercise 4"), not a
            # book-type request.
            "practice book",
            # NOTE: bare "practice" removed -- IntentDetector uses
            # it for the Practice intent (e.g. "practice grammar"),
            # which is not a book-type request.
            "activity book",
            "activities",
            "cahier",
            "cahier d'activités",
            "cahier d activites",
            "notebook"

        ],

        "Answer Key": [

            "answer key",
            "answers",
            "solution",
            "solutions",
            "correction",
            "corrigé",
            "corrigés",
            "corrige",
            "corriges"

        ],

        "Transcription": [

            "transcription",
            "transcriptions",
            "audio script",
            "script"

        ]
    }

    # ------------------------------------------------------

    @staticmethod
    def _normalize(text: str) -> str:

        text = text.lower()

        text = re.sub(r"[^\w\s]", " ", text)

        text = re.sub(r"\s+", " ", text)

        return text.strip()

    # ------------------------------------------------------

    def detect(self, query: str) -> Optional[str]:

        query = self._normalize(query)

        best_match = None

        longest_match = -1

        for book_type, aliases in self.BOOK_TYPE_ALIASES.items():

            for alias in aliases:

                alias = self._normalize(alias)

                pattern = rf"\b{re.escape(alias)}\b"

                if re.search(pattern, query):

                    if len(alias) > longest_match:

                        longest_match = len(alias)

                        best_match = book_type

        return best_match


# ------------------------------------------------------------

if __name__ == "__main__":

    detector = BookTypeDetector()

    test_queries = [

        "Give me Cosmopolite Teacher Guide",
        "Open the Professor Book",
        "I need workbook",
        "Give me exercise book",
        "Show notebook",
        "Need corrigés",
        "Give answer key",
        "Open transcription",
        "Open audio script",
        "Student Book please",
        "Main Book",
        "Livre de l'élève",
        "Guide pédagogique",
        "Cahier",
        "Corrigés",

        # Collision regression checks
        "I want to practice grammar",
        "Exercise 4 page 32",
        "Give me an exercise on verbs",
        "Guide me through chapter 2",
        "Teach me the subjunctive"

    ]

    for query in test_queries:

        print("=" * 60)
        print("Query :", query)
        print("Detected :", detector.detect(query))