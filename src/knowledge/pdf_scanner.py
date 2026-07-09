import json
from pathlib import Path
from typing import Dict, List, Optional

import fitz  # PyMuPDF

from src.knowledge.metadata_extractor import MetadataExtractor
from src.knowledge.models import Book
from src.knowledge.sommaire_parser import SommaireParser


class PDFScanner:
    """
    Scans a PDF folder and builds Book records.

    book_id stability
    ------------------
    book_id is NOT recomputed as "position in the sorted file list"
    on every run -- that shifts every existing book's id whenever a
    new file happens to sort earlier alphabetically, silently
    breaking any reference to the old id (e.g. book_id already
    written onto vector store chunks by the ingestion pipeline).

    Instead, scan() accepts the *previous* knowledge_index.json (if
    any) and reuses each already-known file's existing book_id.
    Only files that are genuinely new get a fresh id, allocated after
    the highest id currently in use.
    """

    def __init__(self, pdf_folder: str = "data/pdf"):

        self.pdf_folder = pdf_folder

        self.extractor = MetadataExtractor()

        self.sommaire_parser = SommaireParser()

    # ----------------------------------------------------
    # Existing catalog loading (for id stability)
    # ----------------------------------------------------

    @staticmethod
    def _load_existing_ids(
        existing_catalog: Optional[List[Dict]]
    ) -> Dict[str, str]:
        """
        filename -> book_id, from whatever catalog was already on
        disk before this scan.
        """

        if not existing_catalog:

            return {}

        return {
            entry["filename"]: entry["book_id"]
            for entry in existing_catalog
            if "filename" in entry and "book_id" in entry
        }

    # ----------------------------------------------------

    @staticmethod
    def _next_id_counter(existing_ids: Dict[str, str]) -> int:

        highest = 0

        for book_id in existing_ids.values():

            # book_ids are "book_NNN" -- fall back gracefully if a
            # differently-formatted id ever shows up.
            digits = "".join(ch for ch in book_id if ch.isdigit())

            if digits:

                highest = max(highest, int(digits))

        return highest + 1

    # ----------------------------------------------------
    # Total Pages
    # ----------------------------------------------------

    def get_total_pages(self, pdf_path) -> int:

        try:

            pdf = fitz.open(pdf_path)

            pages = len(pdf)

            pdf.close()

            return pages

        except Exception:

            return 0

    # ----------------------------------------------------
    # Scan
    # ----------------------------------------------------

    def scan(
        self,
        existing_catalog: Optional[List[Dict]] = None
    ) -> List[Book]:

        existing_ids = self._load_existing_ids(existing_catalog)

        next_id = self._next_id_counter(existing_ids)

        books = []

        pdfs = sorted(Path(self.pdf_folder).glob("*.pdf"))

        for pdf in pdfs:

            filename = pdf.name

            if filename in existing_ids:

                book_id = existing_ids[filename]

            else:

                book_id = f"book_{next_id:03d}"

                next_id += 1

            title = self.extractor.clean_title(filename)

            filepath_str = str(pdf).replace("\\", "/")

            # Auto-detect a chapter/unit -> page-range index from the
            # book's own table of contents, if one can be confidently
            # found in the first few pages. Falls back to [] (the old
            # default) when no TOC is detected -- ExactRetriever's
            # full-document heading scan still works in that case,
            # just slower and without this page-range precision.
            chapters = self.sommaire_parser.parse(filepath_str)

            book = Book(

                book_id=book_id,

                title=title,

                aliases=self.extractor.generate_aliases(title),

                filename=filename,

                filepath=filepath_str,

                series=self.extractor.detect_series(filename),

                level=self.extractor.detect_level(filename),

                book_type=self.extractor.detect_book_type(filename),

                category=self.extractor.detect_category(filename),

                publisher=self.extractor.detect_publisher(filename),

                total_pages=self.get_total_pages(pdf),

                chapters=chapters

            )

            books.append(book)

        return books


# ---------------------------------------------------------
# Testing
# ---------------------------------------------------------

if __name__ == "__main__":

    import os

    os.makedirs("data/pdf", exist_ok=True)

    def touch(name):
        open(f"data/pdf/{name}", "w").close()

    touch("Cosmopolite A1 Main Book.pdf")
    touch("Tendances B1 Main Book.pdf")

    scanner = PDFScanner("data/pdf")

    first_pass = [b.to_dict() for b in scanner.scan(existing_catalog=None)]

    print("BEFORE (2 files):")
    for b in first_pass:
        print(" ", b["book_id"], b["filename"])

    # Simulate a new file sorting alphabetically before the others
    touch("Alphabet_First_Book.pdf")

    second_pass = [
        b.to_dict()
        for b in scanner.scan(existing_catalog=first_pass)
    ]

    print("\nAFTER adding one new PDF, reusing existing catalog:")
    for b in second_pass:
        print(" ", b["book_id"], b["filename"])

    for name in ["Cosmopolite A1 Main Book.pdf", "Tendances B1 Main Book.pdf",
                 "Alphabet_First_Book.pdf"]:
        os.remove(f"data/pdf/{name}")