import re


class MetadataExtractor:
    """
    Extracts book metadata (title, aliases, publisher, series, level,
    book type, category) purely from a PDF filename.
    """

    # ----------------------------------------------------
    # Clean Title
    # ----------------------------------------------------

    def clean_title(self, filename):

        filename = filename.replace(".pdf", "")

        filename = filename.replace("_", " ")

        patterns = [

            r"(?i)main\s*book",
            r"(?i)student\s*book",
            r"(?i)teacher\s*guide",
            r"(?i)guide\s*pédagogique",
            r"(?i)guide",
            r"(?i)livre\s*du\s*professeur",
            r"(?i)livre\s*de\s*l.?élève",
            r"(?i)livre",
            r"(?i)cahier\s*d.?activités",
            r"(?i)cahier",
            r"(?i)exercise\s*book",
            r"(?i)notebook",
            r"(?i)corrigés",
            r"(?i)corriges",
            r"(?i)transcriptions",
            r"(?i)correction",
            r"\(.*?\)"

        ]

        for p in patterns:
            filename = re.sub(p, "", filename)

        filename = re.sub(r"\s+", " ", filename)

        return filename.strip()

    # ----------------------------------------------------
    # Aliases
    # ----------------------------------------------------

    def generate_aliases(self, title):

        aliases = set()

        title = title.strip()

        aliases.add(title.lower())

        aliases.add(title.lower().replace(" ", ""))

        aliases.add(title.lower().replace("-", " "))

        if "cosmopolite" in title.lower():

            aliases.add(title.lower().replace("cosmopolite", "cosmo"))

            aliases.add(title.lower().replace("cosmopolite", ""))

        if "tendances" in title.lower():

            aliases.add(title.lower().replace("tendances", "tendance"))

        aliases = [

            a.strip()

            for a in aliases

            if len(a.strip()) > 1

        ]

        return sorted(list(set(aliases)))

    # ----------------------------------------------------
    # Publisher
    # ----------------------------------------------------

    def detect_publisher(self, filename):

        filename = filename.lower()

        if "cosmopolite" in filename:
            return "Hachette"

        if "tendances" in filename:
            return "CLE International"

        if "oxford" in filename:
            return "Oxford"

        if "teach yourself" in filename:
            return "Teach Yourself"

        return "Unknown"

    # ----------------------------------------------------
    # Series
    # ----------------------------------------------------

    def detect_series(self, filename):

        filename = filename.lower()

        if "cosmopolite" in filename:
            return "Cosmopolite"

        if "tendances" in filename:
            return "Tendances"

        if "oxford" in filename:
            return "Oxford"

        return "General"

    # ----------------------------------------------------
    # Level
    # ----------------------------------------------------

    def detect_level(self, filename):

        filename = filename.lower()

        mapping = {

            "a1": "A1",
            "a2": "A2",
            "b1": "B1",
            "b2": "B2",
            "c1": "C1",
            "c2": "C2"

        }

        for key, value in mapping.items():

            if key in filename:
                return value

        # Cosmopolite number mapping

        if "cosmopolite 1" in filename:
            return "A1"

        if "cosmopolite 2" in filename:
            return "A2"

        if "cosmopolite 3" in filename:
            return "B1"

        if "cosmopolite 4" in filename:
            return "B2"

        if "cosmopolite 5" in filename:
            return "C1"

        return "Unknown"

    # ----------------------------------------------------
    # Book Type
    # ----------------------------------------------------

    def detect_book_type(self, filename):

        filename = filename.lower()

        if "guide" in filename or "professeur" in filename:

            return "Teacher Guide"

        if "corrig" in filename:

            return "Answer Key"

        if "cahier" in filename or "notebook" in filename:

            return "Workbook"

        if "transcription" in filename:

            return "Transcription"

        return "Student Book"

    # ----------------------------------------------------
    # Category
    # ----------------------------------------------------

    def detect_category(self, filename):

        filename = filename.lower()

        if "grammar" in filename:
            return "Grammar"

        if "vocabulary" in filename or "lexique" in filename:
            return "Vocabulary"

        if "conversation" in filename:
            return "Conversation"

        return "General French"
