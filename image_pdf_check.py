"""
Scans every PDF in knowledge_index.json and reports which ones have
no extractable text (scanned/image-only PDFs) -- these will silently
fail both ExactRetriever (heading scan finds nothing) and ingestion
(no usable text to chunk/embed for SemanticRetriever either).

Usage:
    uv run python scan_pdf_text_coverage.py
"""

import json
from pathlib import Path

import fitz  # PyMuPDF


def has_extractable_text(filepath: str, sample_pages: int = 5) -> tuple:
    """
    Returns (has_text, pages_checked, pages_with_text).
    Checks up to `sample_pages` pages spread across the document,
    not just the first few (some PDFs have a blank/image cover but
    real text starting a few pages in, or vice versa).
    """

    try:

        doc = fitz.open(filepath)

    except Exception as e:

        return None, 0, 0

    total_pages = len(doc)

    if total_pages == 0:

        doc.close()

        return False, 0, 0

    # Sample pages spread across the document
    step = max(1, total_pages // sample_pages)

    indices = list(range(0, total_pages, step))[:sample_pages]

    pages_with_text = 0

    for i in indices:

        text = doc[i].get_text().strip()

        if len(text) > 20:  # a handful of stray characters doesn't count

            pages_with_text += 1

    doc.close()

    return pages_with_text > 0, len(indices), pages_with_text


def main():

    knowledge_file = Path("data/knowledge_index.json")

    if not knowledge_file.exists():

        print(f"{knowledge_file} not found.")

        return

    with open(knowledge_file, "r", encoding="utf-8") as f:

        books = json.load(f)

    print(f"Checking {len(books)} books for extractable text...\n")

    ok = []

    scanned = []

    errored = []

    for book in books:

        filepath = book.get("filepath")

        has_text, checked, with_text = has_extractable_text(filepath)

        title = book.get("title")

        if has_text is None:

            errored.append((title, filepath))

            print(f"  ERROR    {title!r} -- could not open '{filepath}'")

        elif has_text:

            ok.append((title, filepath))

            print(f"  OK       {title!r} -- text found on {with_text}/{checked} sampled pages")

        else:

            scanned.append((title, filepath))

            print(f"  NO TEXT  {title!r} -- 0/{checked} sampled pages have text (likely scanned)")

    print("\n" + "=" * 70)
    print(f"OK (has text):        {len(ok)}")
    print(f"NO TEXT (scanned):    {len(scanned)}")
    print(f"ERRORED (bad path):   {len(errored)}")
    print("=" * 70)

    if scanned:

        print("\nBooks needing OCR before they'll work with ExactRetriever/SemanticRetriever:")

        for title, filepath in scanned:

            print(f"  - {title}  ({filepath})")


if __name__ == "__main__":

    main()