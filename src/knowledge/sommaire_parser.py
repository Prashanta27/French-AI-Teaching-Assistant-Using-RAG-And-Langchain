"""
SommaireParser
==============

Parses a book's table of contents ("Sommaire" / "Table des matières"
/ "Contents") page into a chapter/unit -> page-range index, so
ExactRetriever can jump straight to a chapter's actual content
instead of:
  (a) scanning every page of the book for a heading match, or
  (b) accidentally matching the TOC page itself, since it also
      contains the heading text (e.g. "Unité 1 ... p. 10").

Output format matches Book.chapters / knowledge_index.json exactly:
    [{"number": 1, "start_page": 10, "end_page": 21}, ...]
"""

import re
from typing import Dict, List, Optional

import fitz


# Keywords covering the same "chapter family" as StructureDetector/
# ExactRetriever, so whatever heading style a book uses, the TOC
# parser recognizes it too.
_KEYWORDS = r'(?:chapitre|chapter|unit[eé]?|dossier|le[cç]on|lesson|module)'

# A TOC line typically looks like one of:
#   "Unité 1 ... p. 10"
#   "Unité 1................10"
#   "Chapitre 2   22"
#   "Dossier 3 p24"
# i.e. keyword, chapter number, a run of non-digit filler
# (dots/spaces/"p."), then the page number at the end of the line.
_TOC_LINE_PATTERN = re.compile(
    rf'^\s*{_KEYWORDS}\s*(\d+)\D{{1,40}}?(\d{{1,4}})\s*$',
    re.IGNORECASE | re.MULTILINE
)

# A page is only treated as "the Sommaire" if it has at least this
# many TOC-shaped lines -- a single stray match elsewhere (e.g. a
# cross-reference like "see Unité 3, page 34" in body text) shouldn't
# be mistaken for the actual table of contents.
_MIN_MATCHES_FOR_TOC_PAGE = 4

# Only look at the front of the book -- a real table of contents is
# always near the start, and scanning the whole document defeats the
# purpose of avoiding a full scan.
_MAX_PAGES_TO_SCAN = 12


class SommaireParser:

    def parse(self, filepath: str) -> List[Dict[str, int]]:
        """
        Returns [{"number": N, "start_page": P, "end_page": Q}, ...]
        sorted by chapter number, or [] if no table of contents could
        be confidently identified.
        """

        try:

            doc = fitz.open(filepath)

        except Exception:

            return []

        try:

            entries = self._find_toc_entries(doc)

        finally:

            doc.close()

        return entries

    # -----------------------------------------------------

    def _find_toc_entries(self, doc: fitz.Document) -> List[Dict[str, int]]:

        total_pages = len(doc)

        pages_to_scan = min(_MAX_PAGES_TO_SCAN, total_pages)

        candidates: List[List[re.Match]] = []

        for i in range(pages_to_scan):

            text = doc[i].get_text()

            text = self._rejoin_split_toc_lines(text)

            matches = list(_TOC_LINE_PATTERN.finditer(text))

            if len(matches) >= _MIN_MATCHES_FOR_TOC_PAGE:

                candidates.append(matches)

        # Try the most promising candidate (most matches) first, but
        # fall through to others if it turns out not to be a real TOC
        # (see _looks_like_a_real_toc) -- a page with more incidental
        # numbered-line matches isn't necessarily the actual table of
        # contents.
        candidates.sort(key=len, reverse=True)

        for matches in candidates:

            entries = self._build_entries(matches, total_pages)

            if entries:

                return entries

        return []

    # -----------------------------------------------------

    @staticmethod
    def _rejoin_split_toc_lines(text: str) -> str:
        """
        OCR sometimes splits one logical TOC line into two -- e.g.
        "Unite 2..." on one line and "p. 22" on the next. If a line
        has the keyword+number+filler but no trailing page number,
        and the next line is JUST a bare page number, join them into
        a single line before pattern matching.
        """

        lines = text.split("\n")

        joined = []

        i = 0

        keyword_no_number_at_end = re.compile(
            rf'^\s*{_KEYWORDS}\s*\d+\D+$',
            re.IGNORECASE
        )

        bare_page_number = re.compile(r'^\s*(?:p\.?\s*)?\d{1,4}\s*$', re.IGNORECASE)

        while i < len(lines):

            line = lines[i]

            if (
                i + 1 < len(lines)
                and keyword_no_number_at_end.match(line)
                and bare_page_number.match(lines[i + 1])
            ):

                joined.append(line.rstrip() + " " + lines[i + 1].strip())

                i += 2

            else:

                joined.append(line)

                i += 1

        return "\n".join(joined)

    # -----------------------------------------------------

    def _build_entries(
        self,
        matches: List[re.Match],
        total_pages: int
    ) -> List[Dict[str, int]]:

        # Deduplicate by chapter number, keeping the first occurrence
        # (a TOC shouldn't repeat a chapter, but be defensive).
        by_number: Dict[int, int] = {}

        for m in matches:

            number = int(m.group(1))

            start_page = int(m.group(2))

            if number not in by_number:

                by_number[number] = start_page

        ordered = sorted(by_number.items())

        if not self._looks_like_a_real_toc(ordered):

            return []

        entries = []

        for idx, (number, start_page) in enumerate(ordered):

            if idx + 1 < len(ordered):

                next_start = ordered[idx + 1][1]

                end_page = max(start_page, next_start - 1)

            else:

                end_page = total_pages

            entries.append({
                "number": number,
                "start_page": start_page,
                "end_page": end_page
            })

        return entries

    # -----------------------------------------------------

    @staticmethod
    def _looks_like_a_real_toc(ordered: List[tuple]) -> bool:
        """
        Sanity check against false positives -- e.g. numbered legal/
        copyright clauses, footnotes, or other incidental "word N ...
        number" text elsewhere on a page can coincidentally match the
        TOC line pattern. A genuine table of contents lists
        consecutive chapter/unit numbers (0,1,2,3,... or 1,2,3,...)
        with no gaps; matches with gaps (e.g. 1,3,5,7,9) or with page
        numbers that don't strictly increase are almost certainly not
        a real TOC.
        """

        if len(ordered) < _MIN_MATCHES_FOR_TOC_PAGE:

            return False

        numbers = [n for n, _ in ordered]

        # Require fully consecutive chapter numbers -- no gaps at all.
        # A real TOC never skips a unit; a coincidental match on
        # unrelated numbered text very often does.
        for i in range(1, len(numbers)):

            if numbers[i] - numbers[i - 1] != 1:

                return False

        # Page numbers must strictly increase alongside chapter
        # numbers -- chapter 2 starting before chapter 1 (or at the
        # same page) is not a real TOC either.
        pages = [p for _, p in ordered]

        for i in range(1, len(pages)):

            if pages[i] <= pages[i - 1]:

                return False

        return True


# ---------------------------------------------------------
# Testing
# ---------------------------------------------------------

if __name__ == "__main__":

    import os

    os.makedirs("data/pdf", exist_ok=True)

    doc = fitz.open()

    sommaire = doc.new_page()

    sommaire.insert_text((72, 72),
        "Sommaire\n\n"
        "Unite 0 ... p. 4\n"
        "Unite 1 ... p. 10\n"
        "Unite 2 ... p. 22\n"
        "Unite 3 ... p. 34\n"
    )

    for i in range(9):

        p = doc.new_page()

        p.insert_text((72, 72), f"Page {i + 2} filler content, nothing structural here.")

    unite1_page = doc.new_page()

    unite1_page.insert_text((72, 72), "Unite 1 - Lecon 1 - Dire son nom\n\n1. Apprenez le vocabulaire.")

    doc.save("data/pdf/toc_test.pdf")

    doc.close()

    parser = SommaireParser()

    entries = parser.parse("data/pdf/toc_test.pdf")

    print("Parsed chapter entries:")

    for e in entries:

        print(" ", e)