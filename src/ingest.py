import os

from src.file_tracker import (
    calculate_file_hash,
    load_tracker,
    save_tracker
)

from src.data_loader import process_pdf
from src.split_document import split_documents
from src.embedding import EmbeddingManager
from src.vector_store import VectorStore


def ingest():

    tracker = load_tracker()

    pdf_folder = "data/pdf"

    new_documents = []

    updated_tracker = tracker.copy()

    print("\nChecking PDFs...\n")

    for filename in os.listdir(pdf_folder):

        if not filename.endswith(".pdf"):
            continue

        path = os.path.join(pdf_folder, filename)

        file_hash = calculate_file_hash(path)

        if tracker.get(filename) == file_hash:

            print(f"✓ {filename} already indexed.")

            continue

        print(f"+ New PDF detected: {filename}")

        docs = process_pdf(path)

        new_documents.extend(docs)

        updated_tracker[filename] = file_hash

    if len(new_documents) == 0:

        print("\nNo new PDFs found.")

        return

    print("\nSplitting documents...")

    chunks = split_documents(new_documents)

    print("\nGenerating embeddings...")

    embedding_manager = EmbeddingManager()

    texts = [doc.page_content for doc in chunks]

    embeddings = embedding_manager.generate_embedding(texts)

    print("\nUpdating Vector Database...")

    vector_store = VectorStore()

    vector_store.add_documents(chunks, embeddings)

    save_tracker(updated_tracker)

    print("\nIngestion Completed Successfully.")


if __name__ == "__main__":

    ingest()