import os
import uuid
from src.data_loader import process_all_pdfs
from src.split_document import split_documents
from src.embedding import EmbeddingManager
import chromadb
import numpy as np
from typing import List, Any


class VectorStore:
    """Manages document embeddings in a chromaDB vector Store"""

    def __init__(self, collection_name: str = "pdf_documents", persist_directory: str = "data/vector_store"):
        """
        Initialize the vectore store

        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory to persist the vector store
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
        self._initialize_store() 
    def _initialize_store(self):
        """Initialize ChromaDB client and collections"""
        try:
            # Create persistant chromaDB Client
            os.makedirs(self.persist_directory, exist_ok=True)
            self.client = chromadb.PersistentClient(path = self.persist_directory)

            # Get or create collection 
            self.collection = self.client.get_or_create_collection(
                name = self.collection_name,
                metadata={"description": "PDF Documents Embedding For RAG"}
            ) 
            print(f"Vector store initialized. Collection:{self.collection_name}")
            print(f"Existing documens in collections: {self.collection.count()}")

        except Exception as e:
            print(f"Error initializing vector store: {e}")
            raise

    def add_documents(self, documents: List[Any], embeddings: np.ndarray):
        """
        Add documents and their embeddings to the vector store.

        Args:
        documents: List of LangChain Documents
        embeddings: Corresponding embeddings for the documents
        """

        if len(documents) != len(embeddings):
            raise ValueError("Number of documents must match number of embeddings")

        total_documents = len(documents)
        print(f"Adding {total_documents} documents to the vector store")

        # ChromaDB max batch size
        batch_size = 5000
 
        try:
            for batch_start in range(0, total_documents, batch_size):
                batch_end = min(batch_start + batch_size, total_documents)

                print(
                    f"\nProcessing Batch: {batch_start + 1} - {batch_end} "
                    f"of {total_documents}"
                )

                ids = []
                metadatas = []
                documents_text = []
                embeddings_list = []

                # Prepare current batch
                for i in range(batch_start, batch_end):
                    doc = documents[i]
                    embedding = embeddings[i]

                    # Unique ID
                    doc_id = f"doc_{uuid.uuid4().hex[:8]}_{i}"
                    ids.append(doc_id)

                    # Metadata
                    metadata = dict(doc.metadata)
                    metadata["doc_index"] = i
                    metadata["content_length"] = len(doc.page_content)

                    metadatas.append(metadata)

                    # Document
                    documents_text.append(doc.page_content)

                    # Embedding
                    embeddings_list.append(embedding.tolist())

                # Insert current batch
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings_list,
                    metadatas=metadatas,
                    documents=documents_text,
                )

                print(
                    f"✓ Batch inserted successfully "
                    f"({batch_end}/{total_documents})"
                )

            print("\n===================================")
            print("All documents inserted successfully!")
            print(f"Total documents in collection: {self.collection.count()}")
            print("===================================\n")
        except Exception as e:
            print(f"Error adding documents to vector store: {e}")
            raise

    def clear_collection(self):
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "PDF Documents Embedding For RAG"},
            )
            print("Collection cleared successfully")
        except Exception as e:
            print(e)
            raise



### Convert the txt to embeddings

if __name__ == "__main__":

    documents = process_all_pdfs("data/pdf")

    chunks = split_documents(documents)

    texts = [doc.page_content for doc in chunks]

    embedding_manager = EmbeddingManager()

    embeddings = embedding_manager.generate_embedding(texts)

    vector_store = VectorStore()

    vector_store.add_documents(chunks, embeddings)



