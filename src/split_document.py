import os
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
### Text splitting get into chunks

def split_documents(documents, chunk_size = 400, chunk_overlap = 100):
    """Split documents into smaller chunks for better RAG Performance"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = chunk_size,
        chunk_overlap = chunk_overlap,
        length_function = len,
        separators = ["\n\n", "\n", " ", ""]
    )
    split_docs = text_splitter.split_documents(documents)
    for doc in split_docs:

        auto_metadata = extract_metadata(doc.metadata["source"])

        doc.metadata.update(auto_metadata)
    print(f"Split {len(documents)} documents into {len(split_docs)} chunks")

    # Show Example Of a chunk

    if split_docs:
        print(f"\nExample Chunk:")
        print(f"Content: {split_docs[0].page_content[:200]}...")
        print(f"Metadata: {split_docs[0].metadata}")
    return split_docs

def extract_metadata(filename: str):
    """
    Automatically extract metadata from PDF filename.
    """

    filename = os.path.basename(filename).lower()

    metadata = {}

    # -----------------------
    # Level
    # -----------------------

    if "a1" in filename:
        metadata["level"] = "A1"

    elif "a2" in filename:
        metadata["level"] = "A2"

    elif "b1" in filename:
        metadata["level"] = "B1"

    elif "b2" in filename:
        metadata["level"] = "B2"

    elif "c1" in filename:
        metadata["level"] = "C1"
    
    elif "self-study" in filename:
        metadata["level"] = "A1"

    elif "complete french self" in filename:
        metadata["level"] = "A1"

    elif "c2" in filename:
        metadata["level"] = "C2"

    else:
        metadata["level"] = "Unknown"

    # -----------------------
    # Book Type
    # -----------------------

    if "guide" in filename or "professeur" in filename:
        metadata["book_type"] = "Teacher Guide"

    elif "corrig" in filename:
        metadata["book_type"] = "Answer Key"

    elif "cahier" in filename or "notebook" in filename:
        metadata["book_type"] = "Workbook"

    elif "transcription" in filename:
        metadata["book_type"] = "Transcription"

    else:
        metadata["book_type"] = "Student Book"

    # -----------------------
    # Publisher / Series
    # -----------------------

    if "cosmopolite" in filename:
        metadata["series"] = "Cosmopolite"

    elif "tendances" in filename:
        metadata["series"] = "Tendances"

    elif "teach yourself" in filename:
        metadata["series"] = "Teach Yourself"

    elif "oxford" in filename:
        metadata["series"] = "Oxford"

    else:
        metadata["series"] = "General"

    # -----------------------
    # Category
    # -----------------------

    if "grammar" in filename:
        metadata["category"] = "Grammar"

    elif "vocabulary" in filename or "lexique" in filename:
        metadata["category"] = "Vocabulary"

    elif "conversation" in filename:
        metadata["category"] = "Conversation"

    else:
        metadata["category"] = "General French"

    return metadata

