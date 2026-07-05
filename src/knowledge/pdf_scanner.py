from pathlib import Path

import fitz  # PyMuPDF

from src.knowledge.metadata_extractor import MetadataExtractor
from src.knowledge.models import Book


class PDFScanner:

    def __init__(self, pdf_folder="data/pdf"):

        self.pdf_folder = pdf_folder

        self.extractor = MetadataExtractor()

    # ----------------------------------------------------
    # Book ID
    # ----------------------------------------------------

    def generate_book_id(self, index):

        return f"book_{index:03d}"

    # ----------------------------------------------------
    # Total Pages
    # ----------------------------------------------------

    def get_total_pages(self, pdf_path):

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

    def scan(self):

        books = []

        pdfs = sorted(Path(self.pdf_folder).glob("*.pdf"))

        for i, pdf in enumerate(pdfs, start=1):

            filename = pdf.name

            title = self.extractor.clean_title(filename)

            book = Book(

                book_id=self.generate_book_id(i),

                title=title,

                aliases=self.extractor.generate_aliases(title),

                filename=filename,

                filepath=str(pdf).replace("\\", "/"),

                series=self.extractor.detect_series(filename),

                level=self.extractor.detect_level(filename),

                book_type=self.extractor.detect_book_type(filename),

                category=self.extractor.detect_category(filename),

                publisher=self.extractor.detect_publisher(filename),

                total_pages=self.get_total_pages(pdf)

            )

            books.append(book)

        return books
