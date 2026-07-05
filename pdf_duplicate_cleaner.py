import os
import hashlib
from pathlib import Path

from pypdf import PdfReader

PDF_FOLDER = "data/pdf"


def extract_text(pdf_path):
    """Extract text from a PDF."""

    try:
        reader = PdfReader(pdf_path)

        text = ""

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text

        return text, len(reader.pages)

    except Exception as e:
        print(f"❌ Error reading {pdf_path}: {e}")
        return "", 0


def normalize_text(text):
    """Normalize text before hashing."""

    text = text.lower()
    text = " ".join(text.split())

    return text


def generate_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main():

    print("=" * 60)
    print("PDF DUPLICATE DETECTOR")
    print("=" * 60)

    hashes = {}

    duplicate_files = []

    pdf_files = sorted(Path(PDF_FOLDER).glob("*.pdf"))

    print(f"\nFound {len(pdf_files)} PDF files.\n")

    for pdf in pdf_files:

        print(f"Scanning: {pdf.name}")

        text, pages = extract_text(pdf)

        normalized = normalize_text(text)

        text_hash = generate_hash(normalized)

        if text_hash in hashes:

            original = hashes[text_hash]

            duplicate_files.append((original, pdf))

            print("   ⚠ DUPLICATE FOUND!")

        else:

            hashes[text_hash] = pdf

    print("\n")
    print("=" * 60)

    if len(duplicate_files) == 0:

        print("✅ No duplicate PDFs found.")
        return

    print(f"Found {len(duplicate_files)} duplicate PDFs.\n")

    for i, (original, duplicate) in enumerate(duplicate_files, start=1):

        print(f"{i}.")
        print(f"KEEP   : {original.name}")
        print(f"DELETE : {duplicate.name}")
        print()

    choice = input("Delete duplicate PDFs? (y/n): ").strip().lower()

    if choice == "y":

        for _, duplicate in duplicate_files:

            os.remove(duplicate)

            print(f"Deleted: {duplicate.name}")

        print("\n✅ Duplicate cleanup completed.")

    else:

        print("\nNothing deleted.")


if __name__ == "__main__":
    main()