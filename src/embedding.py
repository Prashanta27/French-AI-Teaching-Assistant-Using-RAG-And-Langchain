import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np
from typing import List
from sklearn.metrics.pairwise import cosine_similarity


class EmbeddingManager:
    """Handles Document Embedding Generation Using SentenceTransformer"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding manager

        Args:
            model_name: HuggingFace model name for sentence embedding        
        """
        self.model_name = model_name
        self.model = None
        self._load_model()
    def _load_model(self):
        """Load the SentenceTransformer model"""

        try:
            print(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            print(f"Model Loaded Successfully. Embedding dimension: {self.model.get_embedding_dimension()}")
        except Exception as e:
            print(f"Error Loading Model {self.model_name}: {e}")
            raise
    
    def generate_embedding(self, texts: List[str]) -> np.ndarray:
        """
        Generate Embedding for a list of texts

        Args:
            texts: List of text string to embed

        Returns:
            numpy array of embeddings with shape (len(texts), embedding_dim)
        """
        if not self.model:
            raise ValueError("Model Not Loaded")
        print(f"Generating Embeddings For {len(texts)} texts....")
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            convert_to_numpy=True, 
            show_progress_bar = True)
        print(f"Generate Embedding With Shape: {embeddings.shape}")
        return embeddings
    
    #def get_embedding_dimension(self) -> int:
       ## if not self.model:
        #    raise ValueError("Model Not Loading")
        #return self.model.get_embedding_dimension()

## INitialize the embedding manager


if __name__ == "__main__":

    model = EmbeddingManager()

    emb = model.generate_embedding(

        ["Hello", "Bonjour"]

    )

    print(emb.shape)