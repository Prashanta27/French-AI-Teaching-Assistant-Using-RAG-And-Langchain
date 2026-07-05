import re
from typing import Optional, Dict


class StructureDetector:
    """
    Detect structural references from a user query:
    chapter / unit / lesson / module / dossier / leçon,
    plus page, exercise, activity, and line numbers.
    """

    ROMAN_MAP = {
        "I": 1,
        "II": 2,
        "III": 3,
        "IV": 4,
        "V": 5,
        "VI": 6,
        "VII": 7,
        "VIII": 8,
        "IX": 9,
        "X": 10
    }

    # All of these keywords map to the same "chapter" concept
    CHAPTER_PATTERNS = [
        r'chapter\s*(\d+)',
        r'chapitre\s*(\d+)',
        r'unit\s*(\d+)',
        r'lesson\s*(\d+)',
        r'module\s*(\d+)',
        r'dossier\s*(\d+)',
        r'leçon\s*(\d+)',
        r'lecon\s*(\d+)',
        r'chapter\s*([ivx]+)',
        r'chapitre\s*([ivx]+)'
    ]

    PAGE_PATTERNS = [
        r'page\s*(\d+)',
        r'pg\.?\s*(\d+)',
        r'p\.\s*(\d+)'
    ]

    EXERCISE_PATTERNS = [
        r'exercise\s*(\d+)',
        r'exercice\s*(\d+)',
        r'ex\.\s*(\d+)',
        r'ex\s*(\d+)'
    ]

    ACTIVITY_PATTERNS = [
        r'activity\s*(\d+)',
        r'activité\s*(\d+)',
        r'activite\s*(\d+)',
        r'act\.\s*(\d+)'
    ]

    LINE_PATTERNS = [
        r'line\s*(\d+)',
        r'ligne\s*(\d+)'
    ]

    # -----------------------------------------------------

    @staticmethod
    def _normalize(text: str):

        text = text.lower()

        text = re.sub(r'[-_:]', ' ', text)

        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    # -----------------------------------------------------

    def _match_number(self, query: str, patterns):

        for pattern in patterns:

            match = re.search(pattern, query)

            if not match:
                continue

            value = match.group(1)

            if value.isdigit():
                return int(value)

            # Roman numeral fallback (only chapter patterns use these)
            value = value.upper()

            if value in self.ROMAN_MAP:
                return self.ROMAN_MAP[value]

        return None

    # -----------------------------------------------------

    def detect_chapter(self, query: str) -> Optional[int]:

        return self._match_number(query, self.CHAPTER_PATTERNS)

    def detect_page(self, query: str) -> Optional[int]:

        return self._match_number(query, self.PAGE_PATTERNS)

    def detect_exercise(self, query: str) -> Optional[int]:

        return self._match_number(query, self.EXERCISE_PATTERNS)

    def detect_activity(self, query: str) -> Optional[int]:

        return self._match_number(query, self.ACTIVITY_PATTERNS)

    def detect_line(self, query: str) -> Optional[int]:

        return self._match_number(query, self.LINE_PATTERNS)

    # -----------------------------------------------------

    def detect(self, query: str) -> Dict[str, Optional[int]]:

        query = self._normalize(query)

        return {

            "chapter": self.detect_chapter(query),
            "page": self.detect_page(query),
            "exercise": self.detect_exercise(query),
            "activity": self.detect_activity(query),
            "line": self.detect_line(query)

        }


# -------------------------------------------------------

if __name__ == "__main__":

    detector = StructureDetector()

    test_queries = [

        "Give me chapter 2",
        "Chapter 10",
        "chapter-II",
        "Chapter IV",
        "Teach Unit 5",
        "lesson 8",
        "module 3",
        "Dossier 7",
        "Leçon 9",
        "Chapitre 6",
        "Cosmopolite chapter III",
        "Show me page 45",
        "Exercise 3 please",
        "Activity 2 from unit 4",
        "Read line 10 on page 12",
        "Nothing here"

    ]

    for q in test_queries:

        print("=" * 60)
        print(q)
        print(detector.detect(q))