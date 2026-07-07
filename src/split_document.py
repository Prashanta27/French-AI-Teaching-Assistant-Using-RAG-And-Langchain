import json
import os
from pathlib import Path
from typing import Dict, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter


# ---------------------------------------------------------
# Catalog lookup (single source of truth)
# ---------------------------------------------------------

class CatalogMetadataResolver:
    """
    Resolves a PDF's chunk metadata (book_id, title, series, level,
    book_type, category) from knowledge_index.json, instead of
    re-deriving it from the filename a second/third time.

    knowledge_index.json is already built by KnowledgeIndexBuilder
    (which itself runs the same series/level/book_type/category
    detection once, carefully). Re-deriving it again here risks the
    chunk metadata silently drifting out of sync with the catalog --
    e.g. MetadataFilterEngine says a book is "Cosmopolite A1", but
    its chunks in the vector store are tagged "General"/"Unknown"
    because a weaker/duplicated heuristic missed the same case.
    """

    def __init__(self, knowledge_file: str = "data/knowledge_index.json"):

        self.knowledge_file = Path(knowledge_file)

        self._by_filename: Dict[str, Dict] = self._load()

    # -------------------------------------------------

    def _load(self) -> Dict[str, Dict]:

        if not self.knowledge_file.exists():

            raise FileNotFoundError(
                f"{self.knowledge_file} not found. Run the knowledge "
                f"index builder before ingesting -- chunk metadata is "
                f"sourced from it."
            )

        with open(self.knowledge_file, "r", encoding="utf-8") as f:

            books = json.load(f)

        return {book["filename"]: book for book in books}

    # -------------------------------------------------

    def resolve(self, source_path: str) -> Dict[str, str]:
        """
        source_path: the `source` metadata LangChain's PDF loader
        attaches to each page (a full or relative filepath).
        """

        filename = os.path.basename(source_path)

        book = self._by_filename.get(filename)

        if book is None:

            # Fail loudly rather than silently tagging with guessed
            # defaults -- a chunk with wrong/missing metadata is
            # worse than one that visibly errors during ingestion,
            # since the former only surfaces as "why didn't this
            # book show up in search results" much later.
            raise ValueError(
                f"No knowledge_index.json entry found for '{filename}'. "
                f"Re-run the knowledge index builder so this PDF is "
                f"catalogued before ingesting its chunks."
            )

        return {
            "book_id": book["book_id"],
            "title": book["title"],
            "series": book["series"],
            "level": book["level"],
            "book_type": book["book_type"],
            "category": book["category"]
        }


# ---------------------------------------------------------
# Splitting
# ---------------------------------------------------------

def split_documents(
    documents,
    chunk_size: int = 400,
    chunk_overlap: int = 100,
    resolver: Optional[CatalogMetadataResolver] = None
):
    """
    Split documents into smaller chunks for better RAG performance,
    tagging each chunk with catalog metadata (book_id/series/level/
    book_type/category) resolved from knowledge_index.json.
    """

    resolver = resolver or CatalogMetadataResolver()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )

    split_docs = text_splitter.split_documents(documents)

    for doc in split_docs:

        catalog_metadata = resolver.resolve(doc.metadata["source"])

        doc.metadata.update(catalog_metadata)

    print(f"Split {len(documents)} documents into {len(split_docs)} chunks")

    if split_docs:

        print("\nExample Chunk:")
        print(f"Content: {split_docs[0].page_content[:200]}...")
        print(f"Metadata: {split_docs[0].metadata}")

    return split_docs


# ---------------------------------------------------------
# Testing
# ---------------------------------------------------------

if __name__ == "__main__":

    class FakeDoc:

        def __init__(self, page_content, metadata):

            self.page_content = page_content
            self.metadata = metadata

    # Simulate what a PDF loader would hand off: one Document per
    # page, each with a "source" (and typically "page") key already
    # set -- split_documents() only adds the catalog fields on top.
    fake_documents = [
        FakeDoc(
            "Bonjour, comment ça va? " * 30,
            {"source": "data/pdf/Cosmopolite A1 Main Book.pdf", "page": 0}
        ),
        FakeDoc(
            "Le subjonctif exprime le doute. " * 30,
            {"source": "data/pdf/Cosmopolite A1 Main Book.pdf", "page": 5}
        ),
    ]

    resolver = CatalogMetadataResolver(knowledge_file="data/knowledge_index.json")

    chunks = split_documents(fake_documents, resolver=resolver)

    print("\n--- All chunk metadata ---")

    for c in chunks:

        print(c.metadata)

    print("\n--- Unmatched filename should raise, not silently tag ---")

    try:

        split_documents(
            [FakeDoc("text", {"source": "data/pdf/Unknown_Book.pdf", "page": 0})],
            resolver=resolver
        )

    except ValueError as e:

        print(f"Raised as expected: {e}")
















# import os
# import re
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# ### Text splitting get into chunks

# def split_documents(documents, chunk_size = 400, chunk_overlap = 100):
#     """Split documents into smaller chunks for better RAG Performance"""
#     text_splitter = RecursiveCharacterTextSplitter(
#         chunk_size = chunk_size,
#         chunk_overlap = chunk_overlap,
#         length_function = len,
#         separators = ["\n\n", "\n", " ", ""]
#     )
#     split_docs = text_splitter.split_documents(documents)
#     for doc in split_docs:

#         auto_metadata = extract_metadata(doc.metadata["source"])

#         doc.metadata.update(auto_metadata)
#     print(f"Split {len(documents)} documents into {len(split_docs)} chunks")

#     # Show Example Of a chunk

#     if split_docs:
#         print(f"\nExample Chunk:")
#         print(f"Content: {split_docs[0].page_content[:200]}...")
#         print(f"Metadata: {split_docs[0].metadata}")
#     return split_docs

# def extract_metadata(filename: str):
#     """
#     Automatically extract metadata from PDF filename.
#     """

#     filename = os.path.basename(filename).lower()

#     metadata = {}

#     # -----------------------
#     # Level
#     # -----------------------

#     if "a1" in filename:
#         metadata["level"] = "A1"

#     elif "a2" in filename:
#         metadata["level"] = "A2"

#     elif "b1" in filename:
#         metadata["level"] = "B1"

#     elif "b2" in filename:
#         metadata["level"] = "B2"

#     elif "c1" in filename:
#         metadata["level"] = "C1"
    
#     elif "self-study" in filename:
#         metadata["level"] = "A1"

#     elif "complete french self" in filename:
#         metadata["level"] = "A1"

#     elif "c2" in filename:
#         metadata["level"] = "C2"

#     else:
#         metadata["level"] = "Unknown"

#     # -----------------------
#     # Book Type
#     # -----------------------

#     if "guide" in filename or "professeur" in filename:
#         metadata["book_type"] = "Teacher Guide"

#     elif "corrig" in filename:
#         metadata["book_type"] = "Answer Key"

#     elif "cahier" in filename or "notebook" in filename:
#         metadata["book_type"] = "Workbook"

#     elif "transcription" in filename:
#         metadata["book_type"] = "Transcription"

#     else:
#         metadata["book_type"] = "Student Book"

#     # -----------------------
#     # Publisher / Series
#     # -----------------------

#     if "cosmopolite" in filename:
#         metadata["series"] = "Cosmopolite"

#     elif "tendances" in filename:
#         metadata["series"] = "Tendances"

#     elif "teach yourself" in filename:
#         metadata["series"] = "Teach Yourself"

#     elif "oxford" in filename:
#         metadata["series"] = "Oxford"

#     else:
#         metadata["series"] = "General"

#     # -----------------------
#     # Category
#     # -----------------------

#     if "grammar" in filename:
#         metadata["category"] = "Grammar"

#     elif "vocabulary" in filename or "lexique" in filename:
#         metadata["category"] = "Vocabulary"

#     elif "conversation" in filename:
#         metadata["category"] = "Conversation"

#     else:
#         metadata["category"] = "General French"

#     return metadata

