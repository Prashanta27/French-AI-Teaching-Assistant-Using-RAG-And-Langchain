"""
SemanticRetriever
==================

Embedding-based content search for Explanation / Practice /
GeneralQuery style SearchPlans, and per-book comparison search for
Comparison-intent plans.

Design goals over the original RAGRetriever prototype:
  - Metadata filters (series/level/book_type/category, and specific
    target_books) are pushed down into the ChromaDB query itself
    (a `where` clause) instead of fetching a fixed 40 candidates and
    hoping they happen to match -- faster, and actually correct.
  - Comparison queries (SearchPlan.action == "multi_book_semantic_search")
    run one filtered query per book and keep results grouped by book,
    instead of interleaving everything into a single ranked list
    where "which book was this about" gets lost.
  - Uses `logging`, not `print`, and never lets a bad query take the
    whole pipeline down -- errors become a result entry with
    `found=False` + `warning`, matching ExactRetriever's convention.
  - Result shape (`score`, `found`, `book_id`, `title`, `page`,
    `content`) mirrors ExactRetrievalResult so a later merge step can
    rank both kinds of results together without special-casing either.
"""

import logging
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from src.retriever.metadata_filter import MetadataFilterEngine


logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Result Object
# ---------------------------------------------------------

@dataclass
class SemanticRetrievalResult:

    book_id: Optional[str]
    title: Optional[str]
    found: bool

    page: Optional[Any] = None

    content: Optional[str] = None

    score: float = 0.0

    rank: Optional[int] = None

    metadata: Optional[Dict[str, Any]] = None

    warning: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:

        return asdict(self)


# ---------------------------------------------------------
# Semantic Retriever
# ---------------------------------------------------------

class SemanticRetriever:
    """
    Parameters
    ----------
    vector_store:
        Object exposing `.collection` (a ChromaDB collection) with
        `.query(...)` and `.count()`.
    embedding_manager:
        Object exposing `.generate_embedding(list[str]) -> list[vector]`.
    metadata_engine:
        MetadataFilterEngine -- used to resolve SearchPlan.filters /
        target_books (book titles) into concrete book_ids, so the
        `where` clause can filter on book_id directly rather than
        re-deriving series/level logic here.
    overfetch_multiplier / min_overfetch:
        ChromaDB's cosine "distance" ranking can put a few
        low-relevance hits ahead of a score_threshold cut, so we ask
        for more than top_k and trim after scoring, similar in spirit
        to the original prototype's fixed n_results=40 -- but scaled
        to top_k instead of a magic constant, and capped to the
        collection size so ChromaDB never errors on n_results
        exceeding what actually exists.
    """

    DEFAULT_SCORE_THRESHOLD = 0.0

    # Filter keys understood by SearchPlan/MetadataFilterEngine that
    # map directly onto chunk metadata field names in the vector
    # store. If your ingestion pipeline names these fields
    # differently, update this map rather than the query logic below.
    FILTERABLE_FIELDS = ("series", "level", "book_type", "category")

    def __init__(
        self,
        vector_store,
        embedding_manager,
        metadata_engine: MetadataFilterEngine,
        overfetch_multiplier: int = 5,
        min_overfetch: int = 20,
        reranker=None
    ):

        self.vector_store = vector_store

        self.embedding_manager = embedding_manager

        self.metadata_engine = metadata_engine

        self.overfetch_multiplier = overfetch_multiplier

        self.min_overfetch = min_overfetch

        self.reranker = reranker
        # Optional CrossEncoderReranker. When set, _query() overfetches
        # a larger candidate pool (already does, via
        # overfetch_multiplier) and lets the reranker pick the real
        # top_k from it instead of trusting bi-encoder distance alone.
        # None (default) preserves the original behavior exactly.

    # -----------------------------------------------------
    # Public API
    # -----------------------------------------------------

    def retrieve(
        self,
        plan,
        score_threshold: float = DEFAULT_SCORE_THRESHOLD
    ) -> List[SemanticRetrievalResult]:
        """
        plan: a SearchPlan (action in {"semantic_search",
        "multi_book_semantic_search"}).
        """

        if not plan.search_text or not plan.search_text.strip():

            logger.warning("SemanticRetriever.retrieve() got an empty search_text.")

            return [SemanticRetrievalResult(
                book_id=None,
                title=None,
                found=False,
                warning="No search text was provided."
            )]

        if plan.action == "multi_book_semantic_search":

            return self._retrieve_per_book(plan, score_threshold)

        return self._retrieve_single(plan, score_threshold)

    # -----------------------------------------------------
    # Single-query path (Explanation / Practice / GeneralQuery / ...)
    # -----------------------------------------------------

    def _retrieve_single(self, plan, score_threshold: float) -> List[SemanticRetrievalResult]:

        where = self._build_where_clause(plan.filters, plan.target_books)

        return self._query(
            query_text=plan.search_text,
            top_k=plan.top_k or 5,
            where=where,
            score_threshold=score_threshold
        )

    # -----------------------------------------------------
    # Comparison path -- one filtered query per book, kept grouped
    # -----------------------------------------------------

    def _retrieve_per_book(self, plan, score_threshold: float) -> List[SemanticRetrievalResult]:

        if len(plan.target_books) < 2:

            logger.warning(
                "multi_book_semantic_search called with < 2 target_books "
                "(%s) -- SearchPlanner should have degraded this to "
                "semantic_search already.", plan.target_books
            )

        results: List[SemanticRetrievalResult] = []

        # Non-book filters (level/category/...) still apply to every
        # per-book query; only the book identity itself is pinned
        # per iteration.
        shared_filters = {
            k: v for k, v in plan.filters.items() if k != "series"
        }

        for title in plan.target_books:

            book_ids = self._book_ids_for_titles([title])

            if not book_ids:

                logger.info("No catalog entry found for target book '%s'.", title)

                results.append(SemanticRetrievalResult(
                    book_id=None,
                    title=title,
                    found=False,
                    warning=f"'{title}' was not found in the catalog."
                ))

                continue

            where = self._build_where_clause(
                shared_filters, target_book_ids=book_ids
            )

            book_results = self._query(
                query_text=plan.search_text,
                top_k=plan.top_k or 3,
                where=where,
                score_threshold=score_threshold
            )

            if not book_results:

                results.append(SemanticRetrievalResult(
                    book_id=book_ids[0],
                    title=title,
                    found=False,
                    warning=f"No relevant content found in '{title}'."
                ))

            else:

                results.extend(book_results)

        return results

    # -----------------------------------------------------
    # Filter resolution
    # -----------------------------------------------------

    def _book_ids_for_titles(self, titles: List[str]) -> List[str]:

        titles_set = set(titles)

        catalog = self.metadata_engine.apply({})

        return [b["book_id"] for b in catalog if b["title"] in titles_set]

    # -----------------------------------------------------

    def _build_where_clause(
        self,
        filters: Dict[str, Any],
        target_books: Optional[List[str]] = None,
        target_book_ids: Optional[List[str]] = None
    ) -> Optional[Dict]:
        """
        Translate SearchPlan.filters (+ optionally target_books) into
        a ChromaDB `where` clause. Assumes the ingestion pipeline
        writes series/level/book_type/category/book_id onto each
        chunk's metadata -- if it doesn't, this silently filters out
        everything, so that field mapping is worth double-checking
        against your actual chunking code.
        """

        conditions = []

        for key in self.FILTERABLE_FIELDS:

            value = filters.get(key)

            if value is None:

                continue

            if isinstance(value, list):

                conditions.append({key: {"$in": value}})

            else:

                conditions.append({key: value})

        book_ids = target_book_ids

        if book_ids is None and target_books:

            book_ids = self._book_ids_for_titles(target_books)

        if book_ids:

            conditions.append({"book_id": {"$in": book_ids}})

        if not conditions:

            return None

        if len(conditions) == 1:

            return conditions[0]

        return {"$and": conditions}

    # -----------------------------------------------------
    # Core ChromaDB query + scoring
    # -----------------------------------------------------

    def _collection_size(self) -> int:

        try:

            return self.vector_store.collection.count()

        except Exception:

            logger.exception("Could not read vector store collection size.")

            return 0

    # -----------------------------------------------------

    def _query(
        self,
        query_text: str,
        top_k: int,
        where: Optional[Dict],
        score_threshold: float
    ) -> List[SemanticRetrievalResult]:

        try:

            query_embedding = self.embedding_manager.generate_embedding(
                [query_text]
            )[0]

        except Exception:

            logger.exception("Embedding generation failed for query '%s'.", query_text)

            return [SemanticRetrievalResult(
                book_id=None,
                title=None,
                found=False,
                warning="Failed to generate an embedding for the query."
            )]

        collection_size = self._collection_size()

        if collection_size == 0:

            logger.warning("Vector store collection is empty.")

            return [SemanticRetrievalResult(
                book_id=None,
                title=None,
                found=False,
                warning="The vector store has no indexed content yet."
            )]

        n_results = min(
            max(top_k * self.overfetch_multiplier, self.min_overfetch),
            collection_size
        )

        query_kwargs = dict(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )

        if where:

            query_kwargs["where"] = where

        logger.debug(
            "Querying vector store: n_results=%d where=%s", n_results, where
        )

        try:

            raw = self.vector_store.collection.query(**query_kwargs)

        except Exception:

            logger.exception("Vector store query failed.")

            return [SemanticRetrievalResult(
                book_id=None,
                title=None,
                found=False,
                warning="The vector store query failed."
            )]

        return self._parse_results(raw, top_k, score_threshold, query_text)

    # -----------------------------------------------------

    def _parse_results(
        self,
        raw: Dict,
        top_k: int,
        score_threshold: float,
        query_text: str
    ) -> List[SemanticRetrievalResult]:

        documents = raw.get("documents") or [[]]

        if not documents or not documents[0]:

            logger.info("No documents returned by the vector store for this query.")

            return []

        metadatas = raw["metadatas"][0]

        distances = raw["distances"][0]

        ids = raw["ids"][0]

        # Collect every above-threshold candidate from the overfetched
        # pool first -- do NOT truncate to top_k yet. If a reranker is
        # configured, it needs the full pool to have anything
        # meaningful to re-rank; truncating here would just hand it
        # the bi-encoder's top_k and defeat the point.
        candidates = []

        for doc_id, document, metadata, distance in zip(
            ids, documents[0], metadatas, distances
        ):

            # ChromaDB's default space is cosine distance; similarity
            # is its complement. If your collection uses a different
            # distance metric (e.g. L2), this conversion no longer
            # holds and should be adjusted here.
            similarity_score = 1 - distance

            if similarity_score < score_threshold:

                continue

            candidates.append(SemanticRetrievalResult(
                book_id=metadata.get("book_id"),
                title=metadata.get("title") or metadata.get("source"),
                found=True,
                page=metadata.get("page") or metadata.get("page_label"),
                content=document,
                score=similarity_score,
                metadata=metadata
            ))

        if self.reranker is not None and candidates:

            results = self.reranker.rerank(query_text, candidates, top_k)

        else:

            candidates.sort(key=lambda c: c.score, reverse=True)

            results = candidates[:top_k]

        for i, result in enumerate(results, start=1):

            result.rank = i

        logger.info(
            "Retrieved %d/%d candidates above score_threshold=%.2f%s.",
            len(results), len(ids), score_threshold,
            " (reranked)" if self.reranker is not None else ""
        )

        return results


# ---------------------------------------------------------
# Testing (stubbed vector store + embedding manager -- no real
# ChromaDB/embedding model dependency needed to validate the logic)
# ---------------------------------------------------------

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    class FakeCollection:

        def __init__(self, records):

            self.records = records

        def count(self):

            return len(self.records)

        def query(self, query_embeddings, n_results, include, where=None):

            def matches(meta):

                if not where:

                    return True

                if "$and" in where:

                    return all(matches_single(meta, c) for c in where["$and"])

                return matches_single(meta, where)

            def matches_single(meta, cond):

                (key, val), = cond.items()

                if isinstance(val, dict) and "$in" in val:

                    return meta.get(key) in val["$in"]

                return meta.get(key) == val

            filtered = [r for r in self.records if matches(r["metadata"])]

            filtered = filtered[:n_results]

            return {
                "ids": [[r["id"] for r in filtered]],
                "documents": [[r["document"] for r in filtered]],
                "metadatas": [[r["metadata"] for r in filtered]],
                "distances": [[r["distance"] for r in filtered]]
            }

    class FakeVectorStore:

        def __init__(self, records):

            self.collection = FakeCollection(records)

    class FakeEmbeddingManager:

        def generate_embedding(self, texts):

            import numpy as np

            return [np.array([0.1, 0.2, 0.3]) for _ in texts]

    fake_records = [
        {"id": "c1", "document": "Le subjonctif est utilisé pour exprimer un doute.",
         "distance": 0.1,
         "metadata": {"book_id": "book_003", "title": "Cosmopolite B2", "series": "Cosmopolite",
                      "level": "B2", "book_type": "Student Book", "category": "Grammar", "page": 45}},
        {"id": "c2", "document": "Present tense conjugation of -er verbs.",
         "distance": 0.2,
         "metadata": {"book_id": "book_001", "title": "Cosmopolite A1", "series": "Cosmopolite",
                      "level": "A1", "book_type": "Student Book", "category": "Grammar", "page": 12}},
        {"id": "c3", "document": "Vocabulaire: les fruits et légumes.",
         "distance": 0.5,
         "metadata": {"book_id": "book_004", "title": "Tendances B1", "series": "Tendances",
                      "level": "B1", "book_type": "Student Book", "category": "Vocabulary", "page": 30}},
        {"id": "c4", "document": "Un exercice de compréhension orale.",
         "distance": 0.6,
         "metadata": {"book_id": "book_005", "title": "Tendances B1 Teacher Guide", "series": "Tendances",
                      "level": "B1", "book_type": "Teacher Guide", "category": "General French", "page": 5}},
    ]

    vector_store = FakeVectorStore(fake_records)
    embedding_manager = FakeEmbeddingManager()
    metadata_engine = MetadataFilterEngine()

    retriever = SemanticRetriever(vector_store, embedding_manager, metadata_engine)

    class FakePlan:
        def __init__(self, action, filters, target_books, search_text, top_k=5):
            self.action = action
            self.filters = filters
            self.target_books = target_books
            self.search_text = search_text
            self.top_k = top_k

    test_plans = [

        ("plain semantic search, no filters",
         FakePlan("semantic_search", {}, [], "explain the subjunctive")),

        ("semantic search filtered by category=Grammar",
         FakePlan("semantic_search", {"category": "Grammar"}, [], "verb tenses")),

        ("semantic search filtered by series+level (should exclude Tendances)",
         FakePlan("semantic_search", {"series": "Cosmopolite", "level": "A1"}, [], "verb conjugation")),

        ("comparison across two series",
         FakePlan("multi_book_semantic_search", {"series": ["Cosmopolite", "Tendances"]},
                   ["Cosmopolite A1", "Tendances B1"], "vocabulary practice", top_k=2)),

        ("empty search_text",
         FakePlan("semantic_search", {}, [], "")),

    ]

    for label, plan in test_plans:

        print("=" * 70)
        print(label)

        for result in retriever.retrieve(plan):

            for k, v in result.to_dict().items():

                if v is not None:

                    print(f"  {k:10}: {v}")