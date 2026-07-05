import re
from typing import Optional, List


TOPIC_MAP = {

    "Grammar": [
        "grammar",
        "grammaire",
        "conjugation",
        "conjugaison",
        "tense",
        "present tense",
        "past tense",
        "future tense",
        "verb",
        "verbs",
        "verbe",
        "imperative",
        "indicative",
        "conditional",
        "subjunctive",
        "subjonctif",
        "passive voice",
        "direct speech",
        "indirect speech",
        "pronoun",
        "pronom",
        "determiner",
        "adjective",
        "adverb",
        "preposition",
        # NOTE: "article" is ambiguous (grammatical article vs. a
        # written article). Kept here as the grammar sense since
        # that's the dominant meaning in a language-course context.
        # If real usage shows "article" meaning reading material more
        # often, move it to Reading or disambiguate with context.
        "article"
    ],

    "Vocabulary": [
        "vocabulary",
        "vocabulaire",
        "lexique",
        "words",
        "new words",
        "flashcards",
        "food vocabulary",
        "travel vocabulary",
        "airport words",
        "restaurant vocabulary",
        "family words",
        "clothing vocabulary"
    ],

    "Conversation": [
        "conversation",
        "dialogue",
        "speaking",
        "speaking practice",
        "speaking task",
        "oral",
        "oral activity",
        "discussion",
        "roleplay",
        "pair work",
        "interview",
        "introduce yourself"
    ],

    "Listening": [
        "listening",
        "listening activity",
        "listening task",
        "audio",
        "podcast",
        "écoute",
        "ecoute",
        "compréhension orale",
        "comprehension orale"
    ],

    "Pronunciation": [
        "pronunciation",
        "prononciation",
        "pronounce",
        "accent",
        "phonetics",
        "phonétique",
        "phonetique",
        "ipa",
        "sound"
    ],

    "Writing": [
        "writing",
        "writing task",
        "write an email",
        "write a letter",
        "essay",
        # NOTE: "paragraph" also fits Reading (a passage to read).
        # Grouped under Writing here since it appears alongside
        # "essay"/"composition" as a production task. Revisit with
        # surrounding context if this misfires in practice.
        "paragraph",
        "composition",
        "écriture",
        "ecriture",
        "redaction",
        "rédaction"
    ],

    "Reading": [
        "reading",
        "reading passage",
        "reading exercise",
        "lecture",
        "text",
        "comprehension",
        "comprehension écrite",
        "comprehension ecrite",
        "text comprehension"
    ],

    "Culture": [
        "culture",
        "civilisation",
        "history",
        "histoire",
        "tradition",
        "french history",
        "french food",
        "french tradition",
        "french culture",
        "french customs",
        "customs"
    ],

    "Exam Prep": [
        "exam",
        "test",
        "delf",
        "dalf",
        "tcf",
        "tef",
        "certification",
        "exam preparation",
        "mock test",
        "practice test"
    ]

}


class TopicDetector:
    """
    Detect the subject-matter topic of a user query
    (Grammar, Vocabulary, Conversation, etc.), independent
    of book/level/chapter/page references.
    """

    def __init__(self):

        # Flatten and sort by keyword length (longest first) so more
        # specific phrases (e.g. "present tense") win over shorter
        # generic ones (e.g. "tense"), and multi-word phrases
        # (e.g. "food vocabulary") win over single words.

        pairs = []

        for topic, keywords in TOPIC_MAP.items():

            for keyword in keywords:

                pairs.append((keyword, topic))

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

        return text.strip()

    def detect(self, query: str) -> Optional[str]:

        query = self._normalize(query)

        for keyword, topic in self.pairs:

            if re.search(rf'\b{re.escape(keyword)}\b', query):

                return topic

        return "General French"

    def detect_all(self, query: str) -> List[str]:

        query = self._normalize(query)

        found = []

        for keyword, topic in self.pairs:

            if re.search(rf'\b{re.escape(keyword)}\b', query):

                if topic not in found:
                    found.append(topic)

        return found if found else ["General French"]


# -------------------------------------------------------

if __name__ == "__main__":

    detector = TopicDetector()

    test_queries = [

        # Grammar
        "Explain present tense",
        "Past tense",
        "Future tense",
        "Imperative",
        "Indicative",
        "Conditional",
        "Passive voice",
        "Direct speech",
        "Indirect speech",

        # Vocabulary
        "Food vocabulary",
        "Travel vocabulary",
        "Airport words",
        "Restaurant vocabulary",
        "Family words",
        "Clothing vocabulary",

        # Conversation
        "Dialogue",
        "Speaking practice",
        "Speaking task",
        "Oral activity",
        "Pair work",
        "Interview",
        "Introduce yourself",

        # Reading
        "Reading passage",
        "Reading exercise",
        "Text",
        "Comprehension",

        # Listening
        "Audio",
        "Podcast",
        "Listening activity",
        "Listening task",

        # Writing
        "Write an email",
        "Write a letter",
        "Essay",
        "Paragraph",
        "Composition",
        "Writing task",

        # Culture
        "French history",
        "French food",
        "French tradition",
        "French culture",
        "French customs",

        # Exam
        "DELF",
        "DALF",
        "TCF",
        "TEF",
        "Exam preparation",
        "Mock test",
        "Practice test",

        # Pronunciation
        "IPA",
        "phonetics",
        "phonétique",
        "sound",
        "pronounce",
        "pronunciation"

    ]

    for q in test_queries:

        print(q, "->", detector.detect(q))