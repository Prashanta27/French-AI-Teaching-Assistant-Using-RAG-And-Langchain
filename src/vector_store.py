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
        Add documents and their embeddings to the vector store

        Args:
            documents: List of langchain documents
            embeddings: Coresponding embedding for the documents
        """ 
        if len(documents) != len(embeddings):
            raise ValueError("Number of documents must match number of embeddings")
        print(f"Adding {len(documents)} documents to the vector store")

        # Prepare data for chromadb

        ids = []
        metadatas = []
        documents_text = []
        embeddings_list = []

        for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
            # Generate Unique id
            doc_id = f"doc_{uuid.uuid4().hex[:8]}_{i}"
            ids.append(doc_id)

            # Prepare Metadata
            metadata = dict(doc.metadata)
            metadata["doc_index"] = i
            metadata['content_length'] = len(doc.page_content)
            metadatas.append(metadata)

            # Document content
            documents_text.append(doc.page_content)

            # Embedding
            embeddings_list.append(embedding.tolist())

        # Add to collections
        try:
            self.collection.add(
                ids = ids,
                embeddings = embeddings_list,
                metadatas = metadatas,
                documents = documents_text
            )
            print(f"Successfully added {len(documents)} Documents to vector store")
            print(f"Total documents in collection: {self.collection.count()}")
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



