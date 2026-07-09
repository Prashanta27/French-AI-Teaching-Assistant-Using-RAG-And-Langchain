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

    # 5. Check the ACTUAL book that was targeted (not just the first
    # catalog match, which may be a completely different book) --
    # specifically the requested page, if any, plus a few pages
    # around it.
    target_titles = set(plan.target_books) if plan.target_books else set()

    targeted = [b for b in all_books if b.get("title") in target_titles] or matches

    if targeted:

        book = targeted[0]

        print(f"\n--- Raw text check on the ACTUALLY TARGETED book: {book['title']!r} ---")
        print(f"    filepath: {book['filepath']}")

        import fitz

        try:

            doc = fitz.open(book["filepath"])

            print(f"    total pages in PDF: {len(doc)}")

            requested_page = analysis.page

            if requested_page:

                idx = requested_page - 1

                if 0 <= idx < len(doc):

                    text = doc[idx].get_text().strip()

                    preview = text[:400] if text else "<<EMPTY -- no text on this page>>"

                    print(f"\n    Requested page {requested_page} (PDF index {idx}) full-ish text:")
                    print(f"    {preview}")

                else:

                    print(f"\n    Requested page {requested_page} is OUT OF RANGE "
                          f"(PDF only has {len(doc)} pages).")

            else:

                for i in range(min(3, len(doc))):

                    text = doc[i].get_text().strip()

                    preview = text[:150].replace("\n", " ") if text else "<<EMPTY>>"

                    print(f"    Page {i+1}: {preview}")

            doc.close()

        except Exception as e:

            print(f"    Could not open '{book['filepath']}': {e}")


if __name__ == "__main__":

    main()