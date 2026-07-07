import os

from src.file_tracker import (
    calculate_file_hash,
    load_tracker,
    save_tracker
)

from src.knowledge.knowledge_index_builder import KnowledgeIndexBuilder
from src.data_loader import process_pdf
from src.split_document import split_documents, CatalogMetadataResolver
from src.embedding import EmbeddingManager
from src.vector_store import VectorStore


def ingest():

    pdf_folder = "data/pdf"

    # Keep knowledge_index.json in sync with data/pdf before doing
    # anything else -- CatalogMetadataResolver (used by
    # split_documents) looks up each chunk's series/level/book_type/
    # category/book_id from this catalog, so a new PDF that isn't in
    # it yet would otherwise fail ingestion with a confusing error.
    # Safe to call on every run: book_id is stable across rebuilds
    # (existing files keep their id; only genuinely new files get a
    # new one).
    print("Updating knowledge index...\n")

    KnowledgeIndexBuilder(pdf_folder=pdf_folder).build()

    tracker = load_tracker()

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

    resolver = CatalogMetadataResolver(
        knowledge_file="data/knowledge_index.json"
    )

    chunks = split_documents(new_documents, resolver=resolver)

    print("\nGenerating embeddings...")

    embedding_manager = EmbeddingManager()

    texts = [doc.page_content for doc in chunks]

    embeddings = embedding_manager.generate_embedding(texts)

    print("\nUpdating Vector Database...")

    vector_store = VectorStore()

    # Remove any chunks already stored for these files before adding
    # the new ones -- otherwise a reprocessed file (changed content,
    # or just a fixed ingestion pipeline) leaves stale chunks behind
    # alongside the new ones instead of replacing them.
    processed_paths = {
        os.path.join(pdf_folder, filename)
        for filename in updated_tracker
        if filename not in tracker or tracker[filename] != updated_tracker[filename]
    }

    for path in processed_paths:

        vector_store.delete_by_source(path)

    vector_store.add_documents(chunks, embeddings)

    save_tracker(updated_tracker)

    print("\nIngestion Completed Successfully.")


if __name__ == "__main__":

    ingest()


# import os

# from src.file_tracker import (
#     calculate_file_hash,
#     load_tracker,
#     save_tracker
# )

# from src.data_loader import process_pdf
# from src.split_document import split_documents
# from src.embedding import EmbeddingManager
# from src.vector_store import VectorStore


# def ingest():

#     tracker = load_tracker()

#     pdf_folder = "data/pdf"

#     new_documents = []

#     updated_tracker = tracker.copy()

#     print("\nChecking PDFs...\n")

#     for filename in os.listdir(pdf_folder):

#         if not filename.endswith(".pdf"):
#             continue

#         path = os.path.join(pdf_folder, filename)

#         file_hash = calculate_file_hash(path)

#         if tracker.get(filename) == file_hash:

#             print(f"✓ {filename} already indexed.")

#             continue

#         print(f"+ New PDF detected: {filename}")

#         docs = process_pdf(path)

#         new_documents.extend(docs)

#         updated_tracker[filename] = file_hash

#     if len(new_documents) == 0:

#         print("\nNo new PDFs found.")

#         return

#     print("\nSplitting documents...")

#     chunks = split_documents(new_documents)

#     print("\nGenerating embeddings...")

#     embedding_manager = EmbeddingManager()

#     texts = [doc.page_content for doc in chunks]

#     embeddings = embedding_manager.generate_embedding(texts)

#     print("\nUpdating Vector Database...")

#     vector_store = VectorStore()

#     vector_store.add_documents(chunks, embeddings)

#     save_tracker(updated_tracker)

#     print("\nIngestion Completed Successfully.")


# if __name__ == "__main__":

#     ingest()