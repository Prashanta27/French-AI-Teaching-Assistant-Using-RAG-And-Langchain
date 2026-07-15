"""
LLMGenerator
============

The RAG pipeline's entry point: takes a raw user question, runs it
through query understanding + retrieval, builds a prompt, and calls
the configured LLM provider for the final answer.

Pipeline:

    question
      -> QueryAnalyzer.analyze()   (intent/book/level/structure/...)
      -> SearchPlanner.plan()      (what to retrieve, and how)
      -> Retriever.retrieve()      (dispatches to Exact/Semantic/
                                     Metadata based on plan.action)
      -> PromptBuilder.build()
      -> get_llm(...).generate() / .generate_stream()
         (OpenAI by default, see llm_factory.py)
"""

import logging
from typing import Generator, Optional

from src.query.query_analyzer import QueryAnalyzer
from planner.search_planner import SearchPlanner
from src.retriever.metadata_filter import MetadataFilterEngine
from src.retriever.exact_retriever import ExactRetriever
from src.retriever.semantic_retriever import SemanticRetriever
from src.retriever.reranker import CrossEncoderReranker
from src.retriever.retriever import Retriever
from src.vector_store import VectorStore
from src.prompt_builder import PromptBuilder
from src.LLM.llm_factory import get_llm
from src.embedding.embedding_factory import get_embedding


logger = logging.getLogger(__name__)


class LLMGenerator:

    def __init__(
        self,
        model: Optional[str] = None,
        llm_provider: Optional[str] = None,
        embedding_provider: Optional[str] = None,
        knowledge_file: str = "data/knowledge_index.json",
    ):
        """
        Args:
            model: Model name passed through to the chosen LLM client
                (e.g. "gpt-4o-mini"). None uses that client's own default.
            llm_provider: Which LLM backend to use ("openai", ...).
                None falls back to config.LLM_PROVIDER, then "openai".
            embedding_provider: Which embedding backend to use
                ("openai", "sentence_transformer", ...). None falls
                back to config.EMBEDDING_PROVIDER, then "openai".
            knowledge_file: Path to the catalog JSON used for metadata
                filtering.
        """
        print("Loading Query Understanding pipeline...")

        self.query_analyzer = QueryAnalyzer()

        self.search_planner = SearchPlanner()

        print("Loading Metadata Filter Engine...")

        metadata_engine = MetadataFilterEngine(knowledge_file=knowledge_file)

        print("Loading Vector Store...")

        vector_store = VectorStore()

        print("Loading Embedding Model...")

        embedding_manager = get_embedding(embedding_provider)

        print("Loading LLM Client...")

        llm_kwargs = {"model": model} if model else {}
        self.llm = get_llm(llm_provider, **llm_kwargs)

        print("Initializing Retrievers...")

        # The reranker's model only loads on first actual use (lazy),
        # so constructing it here doesn't slow down startup or
        # require network access until a semantic search actually runs.
        reranker = CrossEncoderReranker()

        self.retriever = Retriever(
            metadata_engine=metadata_engine,
            exact_retriever=ExactRetriever(metadata_engine),
            semantic_retriever=SemanticRetriever(
                vector_store, embedding_manager, metadata_engine,
                reranker=reranker
            )
        )

    # -----------------------------------------------------
    # Shared: question -> prompt (used by both generate and generate_stream)
    # -----------------------------------------------------

    def _build_prompt(self, question: str) -> str:

        analysis = self.query_analyzer.analyze(question)

        plan = self.search_planner.plan(analysis)

        logger.info(
            "intent=%s action=%s llm_task=%s needs_retrieval=%s",
            analysis.intent, plan.action, plan.llm_task, plan.needs_retrieval
        )

        bundle = self.retriever.retrieve(plan)

        return PromptBuilder.build(
            context=bundle.context,
            question=question,
            llm_task=plan.llm_task
        )

    # -----------------------------------------------------
    # Public API -- non-streaming
    # -----------------------------------------------------

    def generate(self, question: str) -> str:
        """Run the full pipeline and return the complete answer at once.

        Args:
            question: The user's raw question.

        Returns:
            The full generated answer, or a friendly error message if
            the LLM call fails.
        """
        prompt = self._build_prompt(question)

        try:
            return self.llm.generate(prompt)
        except Exception:
            logger.exception("LLM call failed.")
            return "The language model request failed. Please try again."

    # -----------------------------------------------------
    # Public API -- streaming
    # -----------------------------------------------------

    def generate_stream(self, question: str) -> Generator[str, None, None]:
        """Run the full pipeline and yield the answer chunk by chunk.

        Retrieval and prompt-building happen synchronously first (they
        are fast compared to the LLM call and the retriever needs a
        finished plan before it can run); only the final LLM call is
        streamed token-by-token to the caller.

        Args:
            question: The user's raw question.

        Yields:
            Successive text chunks of the answer. On failure, yields a
            single friendly error message chunk instead of raising.
        """
        try:
            prompt = self._build_prompt(question)
        except Exception:
            logger.exception("Failed while building the prompt (retrieval stage).")
            yield "Something went wrong while looking up relevant material. Please try again."
            return

        try:
            for chunk in self.llm.generate_stream(prompt):
                yield chunk
        except Exception:
            logger.exception("Streaming LLM call failed.")
            yield "The language model request failed. Please try again."


# ---------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------

if __name__ == "__main__":  # CLI mode -- python -m src.LLM.llm_generator

    logging.basicConfig(level=logging.INFO)

    generator = LLMGenerator()

    while True:

        question = input("\nAsk French Question (q to quit): ")

        if question.lower() == "q":

            break

        print("\n")
        print("=" * 80)
        for chunk in generator.generate_stream(question):
            print(chunk, end="", flush=True)
        print()
        print("=" * 80)
        print()


















# """
# LLMGenerator
# ============

# The RAG pipeline's entry point: takes a raw user question, runs it
# through query understanding + retrieval, builds a prompt, and calls
# the configured LLM provider for the final answer.

# Pipeline:

#     question
#       -> QueryAnalyzer.analyze()   (intent/book/level/structure/...)
#       -> SearchPlanner.plan()      (what to retrieve, and how)
#       -> Retriever.retrieve()      (dispatches to Exact/Semantic/
#                                      Metadata based on plan.action)
#       -> PromptBuilder.build()
#       -> get_llm(...).generate()   (OpenAI by default, see llm_factory.py)
# """

# import logging
# from typing import Optional

# from src.query.query_analyzer import QueryAnalyzer
# from planner.search_planner import SearchPlanner
# from src.retriever.metadata_filter import MetadataFilterEngine
# from src.retriever.exact_retriever import ExactRetriever
# from src.retriever.semantic_retriever import SemanticRetriever
# from src.retriever.reranker import CrossEncoderReranker
# from src.retriever.retriever import Retriever
# from src.vector_store import VectorStore
# from src.prompt_builder import PromptBuilder
# from src.LLM.llm_factory import get_llm
# from src.embedding.embedding_factory import get_embedding


# logger = logging.getLogger(__name__)


# class LLMGenerator:

#     def __init__(
#         self,
#         model: Optional[str] = None,
#         llm_provider: Optional[str] = None,
#         embedding_provider: Optional[str] = None,
#         knowledge_file: str = "data/knowledge_index.json",
#     ):
#         """
#         Args:
#             model: Model name passed through to the chosen LLM client
#                 (e.g. "gpt-4o-mini"). None uses that client's own default.
#             llm_provider: Which LLM backend to use ("openai", ...).
#                 None falls back to config.LLM_PROVIDER, then "openai".
#             embedding_provider: Which embedding backend to use
#                 ("openai", "sentence_transformer", ...). None falls
#                 back to config.EMBEDDING_PROVIDER, then "openai".
#             knowledge_file: Path to the catalog JSON used for metadata
#                 filtering.
#         """
#         print("Loading Query Understanding pipeline...")

#         self.query_analyzer = QueryAnalyzer()

#         self.search_planner = SearchPlanner()

#         print("Loading Metadata Filter Engine...")

#         metadata_engine = MetadataFilterEngine(knowledge_file=knowledge_file)

#         print("Loading Vector Store...")

#         vector_store = VectorStore()

#         print("Loading Embedding Model...")

#         embedding_manager = get_embedding(embedding_provider)

#         print("Loading LLM Client...")

#         llm_kwargs = {"model": model} if model else {}
#         self.llm = get_llm(llm_provider, **llm_kwargs)

#         print("Initializing Retrievers...")

#         # The reranker's model only loads on first actual use (lazy),
#         # so constructing it here doesn't slow down startup or
#         # require network access until a semantic search actually runs.
#         reranker = CrossEncoderReranker()

#         self.retriever = Retriever(
#             metadata_engine=metadata_engine,
#             exact_retriever=ExactRetriever(metadata_engine),
#             semantic_retriever=SemanticRetriever(
#                 vector_store, embedding_manager, metadata_engine,
#                 reranker=reranker
#             )
#         )

#     # -----------------------------------------------------
#     # Public API
#     # -----------------------------------------------------

#     def generate(self, question: str) -> str:

#         analysis = self.query_analyzer.analyze(question)

#         plan = self.search_planner.plan(analysis)

#         logger.info(
#             "intent=%s action=%s llm_task=%s needs_retrieval=%s",
#             analysis.intent, plan.action, plan.llm_task, plan.needs_retrieval
#         )

#         bundle = self.retriever.retrieve(plan)

#         prompt = PromptBuilder.build(
#             context=bundle.context,
#             question=question,
#             llm_task=plan.llm_task
#         )

#         try:
#             return self.llm.generate(prompt)
#         except Exception:
#             logger.exception("LLM call failed.")
#             return "The language model request failed. Please try again."


# # ---------------------------------------------------------
# # CLI entry point
# # ---------------------------------------------------------

# if __name__ == "__main__":  # CLI mode -- python -m src.LLM.ollama_client

#     logging.basicConfig(level=logging.INFO)

#     generator = LLMGenerator()

#     while True:

#         question = input("\nAsk French Question (q to quit): ")

#         if question.lower() == "q":

#             break

#         answer = generator.generate(question)

#         print("\n")
#         print("=" * 80)
#         print(answer)
#         print("=" * 80)
#         print()