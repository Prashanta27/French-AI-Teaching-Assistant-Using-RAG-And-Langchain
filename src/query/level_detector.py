import re
from typing import Optional


class LevelDetector:
    """
    Detects the CEFR language level (A1, A2, B1, B2, C1, C2)
    from a user's query.
    """

    LEVEL_ALIASES = {

        "A1": [
            "a1",
            "beginner",
            "basic",
            "starter",
            "novice",
            "entry level",
            "elementary 1",
            "débutant",
            "debutant"
        ],

        "A2": [
            "a2",
            "elementary",
            "false beginner",
            "pre intermediate"
        ],

        "B1": [
            "b1",
            "intermediate",
            "lower intermediate"
        ],

        "B2": [
            "b2",
            "upper intermediate"
        ],

        "C1": [
            "c1",
            "advanced"
        ],

        "C2": [
            "c2",
            "master",
            "proficient",
            "expert",
            "fluent"
        ]

    }

    # ---------------------------------------------

    @staticmethod
    def _normalize(text: str) -> str:

        text = text.lower()

        text = re.sub(r"[^\w\s]", " ", text)

        text = re.sub(r"\s+", " ", text)

        return text.strip()

    # ---------------------------------------------

    def detect(self, query: str) -> Optional[str]:

        query = self._normalize(query)

        best_level = None

        best_length = -1

        for level, aliases in self.LEVEL_ALIASES.items():

            for alias in aliases:

                alias = self._normalize(alias)

                pattern = rf"\b{re.escape(alias)}\b"

                if re.search(pattern, query):

                    # longest alias wins
                    if len(alias) > best_length:

                        best_length = len(alias)

                        best_level = level

        return best_level


# ------------------------------------------------------

if __name__ == "__main__":

    detector = LevelDetector()

    test_queries = [

        "Recommend beginner book",

        "Give me A1 grammar",

        "Teach elementary French",

        "Need A2 workbook",

        "Intermediate French book",

        "Teach B1 vocabulary",

        "Upper Intermediate Conversation",

        "Advanced grammar",

        "C2 French",

        "Master level French",

        "I want a fluent level French course",

        "Give me Cosmopolite A2",

        "Recommend beginner Cosmopolite"

    ]

    for q in test_queries:

        print("=" * 60)

        print("Query :", q)

        print("Detected Level :", detector.detect(q))