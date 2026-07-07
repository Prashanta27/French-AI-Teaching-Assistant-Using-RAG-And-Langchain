"""
Diagnostic script -- run this to see EXACTLY where the pipeline
fails for a given query, instead of just seeing the final
"no info found" answer.

Usage:
    uv run python debug_query.py "give me cosmopolite chapter 2 line 4"
"""

import sys
import json

from src.query.query_analyzer import QueryAnalyzer
from planner.search_planner import SearchPlanner
from src.retriever.metadata_filter import MetadataFilterEngine
from src.retriever.exact_retriever import ExactRetriever


def main():

    question = sys.argv[1] if len(sys.argv) > 1 else "give me cosmopolite chapter 2 line 4"

    print("=" * 70)
    print("QUESTION:", question)
    print("=" * 70)

    analyzer = QueryAnalyzer()
    planner = SearchPlanner()
    metadata_engine = MetadataFilterEngine()
    exact_retriever = ExactRetriever(metadata_engine)

    # 1. What did QueryAnalyzer detect?
    analysis = analyzer.analyze(question)

    print("\n--- QueryAnalysis ---")
    for k, v in analysis.to_dict().items():
        print(f"  {k}: {v}")

    # 2. Is "Cosmopolite" actually in the catalog at all?
    print("\n--- Catalog check: any book with series containing 'cosmopolite'? ---")

    all_books = metadata_engine.apply({})

    print(f"Total books in catalog: {len(all_books)}")

    matches = [b for b in all_books if "cosmopolite" in b.get("series", "").lower()]

    if not matches:
        print("!! NO book in knowledge_index.json has series='Cosmopolite' (or similar).")
        print("   Sample of what IS in the catalog:")
        for b in all_books[:5]:
            print(f"   - title={b.get('title')!r} series={b.get('series')!r} filename={b.get('filename')!r}")
    else:
        print(f"Found {len(matches)} matching book(s):")
        for b in matches:
            print(f"  - title={b.get('title')!r} filepath={b.get('filepath')!r} "
                  f"level={b.get('level')!r} chapters={b.get('chapters')!r}")

    # 3. What did SearchPlanner decide?
    plan = planner.plan(analysis)

    print("\n--- SearchPlan ---")
    for k, v in plan.to_dict().items():
        print(f"  {k}: {v}")

    # 4. What did ExactRetriever actually do, in detail?
    print("\n--- ExactRetriever.retrieve() raw results ---")

    results = exact_retriever.retrieve(plan)

    for r in results:
        print(json.dumps(r.to_dict(), indent=2, default=str, ensure_ascii=False))

    # 5. If a book matched, check whether PyMuPDF can even read text from it
    # (scanned/image-only PDFs return empty text -- a very common reason
    # heading-scan finds nothing).
    if matches:

        print("\n--- Raw text check on the first matching PDF (first 3 pages) ---")

        import fitz

        filepath = matches[0]["filepath"]

        try:
            doc = fitz.open(filepath)
            for i in range(min(3, len(doc))):
                text = doc[i].get_text().strip()
                preview = text[:150].replace("\n", " ") if text else "<<EMPTY -- likely a scanned/image PDF with no text layer>>"
                print(f"  Page {i+1}: {preview}")
            doc.close()
        except Exception as e:
            print(f"  Could not open '{filepath}': {e}")


if __name__ == "__main__":

    main()