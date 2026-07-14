from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai")


# ==========================================
# Embedding Configuration
# ==========================================

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


# ==========================================
# LLM Configuration
# ==========================================

LLM_MODEL = "llama3.2"

OLLAMA_HOST = "http://localhost:11434"


# ==========================================
# Vector Store Configuration
# ==========================================

COLLECTION_NAME = "pdf_documents"

VECTOR_STORE_DIR = "data/vector_store"


# ==========================================
# Data Configuration
# ==========================================

PDF_DIRECTORY = "data/pdf"


# ==========================================
# Chunking Configuration
# ==========================================

CHUNK_SIZE = 400

CHUNK_OVERLAP = 100


# ==========================================
# Retrieval Configuration
# ==========================================

TOP_K = 2

SCORE_THRESHOLD = 0.0