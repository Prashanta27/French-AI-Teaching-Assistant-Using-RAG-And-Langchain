"""
LLMGenerator
============

The RAG pipeline's entry point: takes a raw user question, runs it
through query understanding + retrieval, builds a prompt, and calls
Ollama for the final answer.

Pipeline:

    question
      -> QueryAnalyzer.analyze()   (intent/book/level/structure/...)
      -> SearchPlanner.plan()      (what to retrieve, and how)
      -> Retriever.retrieve()      (dispatches to Exact/Semantic/
                                     Metadata based on plan.action)
      -> PromptBuilder.build()
      -> Ollama /api/chat
"""

import logging

import requests

from src.query.query_analyzer import QueryAnalyzer
from planner.search_planner import SearchPlanner
from src.retriever.metadata_filter import MetadataFilterEngine
from src.retriever.exact_retriever import ExactRetriever
from src.retriever.semantic_retriever import SemanticRetriever
from src.retriever.retriever import Retriever
from src.vector_store import VectorStore
from src.embedding import EmbeddingManager
from src.prompt_builder import PromptBuilder


logger = logging.getLogger(__name__)


class LLMGenerator:

    def __init__(
        self,
        model: str = "llama3.2",
        host: str = "http://localhost:11434",
        knowledge_file: str = "data/knowledge_index.json"
    ):

        self.model = model

        self.host = host

        print("Loading Query Understanding pipeline...")

        self.query_analyzer = QueryAnalyzer()

        self.search_planner = SearchPlanner()

        print("Loading Metadata Filter Engine...")

        metadata_engine = MetadataFilterEngine(knowledge_file=knowledge_file)

        print("Loading Vector Store...")

        vector_store = VectorStore()

        print("Loading Embedding Model...")

        embedding_manager = EmbeddingManager()

        print("Initializing Retrievers...")

        self.retriever = Retriever(
            metadata_engine=metadata_engine,
            exact_retriever=ExactRetriever(metadata_engine),
            semantic_retriever=SemanticRetriever(
                vector_store, embedding_manager, metadata_engine
            )
        )

    # -----------------------------------------------------
    # Public API
    # -----------------------------------------------------

    def generate(self, question: str) -> str:

        analysis = self.query_analyzer.analyze(question)

        plan = self.search_planner.plan(analysis)

        logger.info(
            "intent=%s action=%s llm_task=%s needs_retrieval=%s",
            analysis.intent, plan.action, plan.llm_task, plan.needs_retrieval
        )

        bundle = self.retriever.retrieve(plan)

        prompt = PromptBuilder.build(
            context=bundle.context,
            question=question,
            llm_task=plan.llm_task
        )

        return self._call_ollama(prompt)

    # -----------------------------------------------------
    # Ollama call
    # -----------------------------------------------------

    def _call_ollama(self, prompt: str) -> str:

        try:

            response = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False
                },
                timeout=300
            )

            response.raise_for_status()

        except requests.exceptions.ConnectionError:

            logger.exception("Could not connect to Ollama at %s.", self.host)

            return (
                f"I couldn't reach the language model at {self.host}. "
                f"Is Ollama running?"
            )

        except requests.exceptions.RequestException:

            logger.exception("Ollama request failed.")

            return "The language model request failed. Please try again."

        try:

            return response.json()["message"]["content"]

        except (KeyError, ValueError):

            logger.exception("Unexpected Ollama response shape: %s", response.text[:500])

            return "Received an unexpected response from the language model."


# ---------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------

if __name__ == "__main__":  # CLI mode -- python -m src.ollama_client

    logging.basicConfig(level=logging.INFO)

    generator = LLMGenerator(model="llama3.2")

    while True:

        question = input("\nAsk French Question (q to quit): ")

        if question.lower() == "q":

            break

        answer = generator.generate(question)

        print("\n")
        print("=" * 80)
        print(answer)
        print("=" * 80)
        print()