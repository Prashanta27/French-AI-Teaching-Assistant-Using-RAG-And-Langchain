from src.data_loader import process_all_pdfs
from src.split_document import split_documents
from src.embedding import EmbeddingManager
from src.vector_store import VectorStore


def ingest():

    print("\nStep 1: Loading PDFs...")
    documents = process_all_pdfs("data/pdf")

    print("\nStep 2: Splitting documents...")
    chunks = split_documents(documents)

    print("\nStep 3: Generating embeddings...")
    embedding_manager = EmbeddingManager()

    texts = [doc.page_content for doc in chunks]

    embeddings = embedding_manager.generate_embedding(texts)

    print("\nStep 4: Storing embeddings...")
    vector_store = VectorStore()

    vector_store.add_documents(chunks, embeddings)

    print("\nIngestion completed successfully!")

    vector_store = VectorStore()

    vector_store.clear_collection()

    vector_store.add_documents(

        chunks,
        embeddings
)

if __name__ == "__main__":
    ingest()