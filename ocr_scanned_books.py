"""
Batch-OCRs every "no text" (scanned) PDF found in knowledge_index.json,
so ExactRetriever and the ingestion pipeline (SemanticRetriever) can
both read real text from them -- no other code changes needed.

Originals are backed up to data/pdf_originals_backup/ before being
replaced, in case OCR quality needs a second look or a different
language/setting later.

Usage:
    uv run python ocr_scanned_books.py
"""

import json
import shutil
import tempfile
from pathlib import Path

import fitz
import ocrmypdf


BACKUP_DIR = Path("data/pdf_originals_backup")

SAMPLE_PAGES = 5


def has_extractable_text(filepath: str) -> bool:

    try:

        doc = fitz.open(filepath)

    except Exception:

        return False

    total_pages = len(doc)

    if total_pages == 0:

        doc.close()

        return False

    step = max(1, total_pages // SAMPLE_PAGES)

    indices = list(range(0, total_pages, step))[:SAMPLE_PAGES]

    found_text = any(
        len(doc[i].get_text().strip()) > 20
        for i in indices
    )

    doc.close()

    return found_text


def ocr_book(filepath: str, language: str = "fra") -> bool:

    path = Path(filepath)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    backup_path = BACKUP_DIR / path.name

    if not backup_path.exists():

        shutil.copy2(path, backup_path)

        print(f"    Backed up original -> {backup_path}")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:

        tmp_path = Path(tmp.name)

    try:

        ocrmypdf.ocr(
            str(path),
            str(tmp_path),
            language=language,
            deskew=True,
            force_ocr=True,
            progress_bar=False
        )

        # Atomic-ish replace only after OCR succeeded, so a failed run
        # never leaves the original PDF corrupted/half-written.
        shutil.move(str(tmp_path), str(path))

        return True

    except Exception as e:

        print(f"    OCR FAILED for '{path}': {e}")

        if tmp_path.exists():

            tmp_path.unlink()

        return False


def main():

    knowledge_file = Path("data/knowledge_index.json")

    if not knowledge_file.exists():

        print(f"{knowledge_file} not found.")

        return

    with open(knowledge_file, "r", encoding="utf-8") as f:

        books = json.load(f)

    scanned = [
        b for b in books
        if not has_extractable_text(b.get("filepath"))
    ]

    if not scanned:

        print("No scanned (text-less) books found -- nothing to do.")

        return

    print(f"Found {len(scanned)} book(s) needing OCR:\n")

    for b in scanned:

        print(f"  - {b['title']}  ({b['filepath']})")

    print()

    succeeded = []

    failed = []

    for b in scanned:

        print(f"OCR-ing '{b['title']}' ({b['filepath']}) ...")

        if ocr_book(b["filepath"]):

            succeeded.append(b["title"])

            print("    Done.")

        else:

            failed.append(b["title"])

    print("\n" + "=" * 70)
    print(f"Succeeded: {len(succeeded)}")
    print(f"Failed:    {len(failed)}")

    if failed:

        print("\nFailed books (originals untouched, backups available):")

        for title in failed:

            print(f"  - {title}")

    print("=" * 70)
    print("\nNext steps:")
    print("  1. uv run ingest.py     # re-rebuilds knowledge_index.json")
    print("     (harmless -- book_id stays stable) and re-chunks/")
    print("     re-embeds ONLY the files that changed (these OCR'd")
    print("     ones), replacing their old empty-text chunks.")
    print("  2. uv run python scan_pdf_text_coverage.py   # confirm 0 left")


if __name__ == "__main__":

    main()