print("before vector store import")

from src.vector_store import VectorStore

print("before embedding import")

from src.embedding import EmbeddingManager

print("all imports successful")

from src.vector_store import VectorStore
from src.embedding import EmbeddingManager
from typing import List, Dict, Any



class RAGRetriever:
    """Handles query based retrival from the vector store"""

    def __init__(self, vector_store: VectorStore, embedding_manager: EmbeddingManager):
        """
        Initialize The Retriever

        Args:
            vector_store: Vector Store containing document embeddings
            embedding_manager: Manager for generating query embedding
        
        """
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager
    

    def retrieve(self, query: str, top_k: int = 2, score_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """
        Retrieve Relevant documents for a query

        Args:
            query: The search query
            top_k: Number of top results to return
            score_threshold: Minimum Similarity Score Threshold

        Return:
              List of dictionaries containing retrieved documents and metadata
        """
        print(f"Retrieving documents for query: '{query}'")
        print(f"Top k: {top_k}, score threshold: {score_threshold}")

        # Generate query embedding
        query_embedding = self.embedding_manager.generate_embedding([query])[0]

        # search in vector store

        try:
            results = self.vector_store.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=top_k
            )

            # process results
            retrieved_docs = []

            if results['documents'] and results['documents'][0]:
                documents = results['documents'][0]
                metadatas = results['metadatas'][0]
                distances = results['distances'][0]
                ids = results['ids'][0]

                for i, (doc_id, document, metadata, distance) in enumerate(zip(ids, documents, metadatas, distances)):
                    # convert distance to similaity store (ChromaDB uses cosine distance)
                    similarity_score = 1 - distance

                    if similarity_score >= score_threshold:
                        retrieved_docs.append(
                            {
                                'id': doc_id,
                                'content': document,
                                'metadata': metadata,
                                'similarity_score': similarity_score,
                                'distance': distance,
                                'rank': i + 1
                            }
                        )
                print(f"Retrieved {len(retrieved_docs)} documents (after filtering)")
            else:
                print("No documents found")
            return retrieved_docs
        except Exception as e:
            print(f"Error during Retrieval: {e}")
            return[]

if __name__ == "__main__":

    vector_store = VectorStore()

    embedding_manager = EmbeddingManager()

    rag_retriever = RAGRetriever(vector_store,embedding_manager)

    query = input("Enter Your question:")

    result = rag_retriever.retrieve(query)

    for doc in result:

        print(doc['content'][:200])

        print(doc['similarity_score'])

        print()

