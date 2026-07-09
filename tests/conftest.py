"""
Shared fixtures for the benchmark suite.

Builds a small, self-contained synthetic PDF catalog (not the real
data/pdf catalog, which changes over time) covering every regression
case found during development:
  - same level, different book_type (tie-breaking)
  - a bare-numbered-series book (no "A1"-style alias)
  - a book with a real, parseable Sommaire/TOC
  - a book with a fake/non-consecutive numbered page (TOC false
    positive it should NOT be fooled by)
  - "Unite"/"Unité" heading style
  - bare-numbered ("1.", "2.", "3.") exercise style

Running against this fixed, known catalog means the suite gives the
same pass/fail answer every time, regardless of what's currently in
the real data/pdf folder.
"""

import json
from pathlib import Path

import fitz
import pytest

from src.query.query_analyzer import QueryAnalyzer
from planner.search_planner import SearchPlanner
from src.retriever.metadata_filter import MetadataFilterEngine
from src.retriever.exact_retriever import ExactRetriever
from src.retriever.retriever import Retriever


@pytest.fixture(scope="session")
def fixture_dir(tmp_path_factory):

    base = tmp_path_factory.mktemp("benchmark_fixtures")

    (base / "pdf").mkdir()

    return base


@pytest.fixture(scope="session")
def catalog(fixture_dir):

    pdf_dir = fixture_dir / "pdf"

    entries = []

    # ---- 1. Cosmopolite A1 (bare-numbered series book: "Cosmopolite
    # 1", no "A1"-style alias -- exercises how false the true false-
    # alarm alias-stripping bug region if it ever regresses).
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Cosmopolite 1 workbook cover page.")
    p2 = doc.new_page()
    p2.insert_text((72, 72),
        "1. Voici la reponse.\n"
        "2. Conjuguez le verbe aller.\n"
        "3. Completez avec a, au ou en.\n"
        "4. Choisissez la bonne reponse.\n"
    )
    path = pdf_dir / "Cosmopolite 1 Notebook (cahier).pdf"
    doc.save(str(path))
    doc.close()
    entries.append({
        "book_id": "book_001", "title": "Cosmopolite 1",
        "aliases": ["cosmopolite 1", "cosmopolite1", "cosmo 1"],
        "filename": path.name, "filepath": str(path).replace("\\", "/"),
        "series": "Cosmopolite", "level": "A1", "book_type": "Workbook",
        "category": "General French", "chapters": []
    })

    # ---- 2 & 3. Cosmopolite A2, two books tied at the same level --
    # Teacher Guide vs Student Book (the tie-breaking regression).
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Teacher's guide notes for Cosmopolite A2.")
    path_guide = pdf_dir / "Cosmopolite A2 guide.pdf"
    doc.save(str(path_guide))
    doc.close()
    entries.append({
        "book_id": "book_002", "title": "Cosmopolite A2 guide",
        "aliases": ["cosmopolite a2 guide"],
        "filename": path_guide.name, "filepath": str(path_guide).replace("\\", "/"),
        "series": "Cosmopolite", "level": "A2", "book_type": "Teacher Guide",
        "category": "General French", "chapters": []
    })

    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((72, 72), "Student content page 1.")
    for i in range(23):
        p = doc.new_page()
        if i == 22:  # page 24 (1-indexed)
            p.insert_text((72, 72),
                "1. Warm-up.\n2. Grammar practice.\n"
                "3. Complete the sentences with a, au, or en.\n"
            )
        else:
            p.insert_text((72, 72), f"Filler page {i+2}.")
    path_main = pdf_dir / "Cosmopolite A2 main book.pdf"
    doc.save(str(path_main))
    doc.close()
    entries.append({
        "book_id": "book_003", "title": "Cosmopolite A2 main book",
        "aliases": ["cosmopolite a2 main book"],
        "filename": path_main.name, "filepath": str(path_main).replace("\\", "/"),
        "series": "Cosmopolite", "level": "A2", "book_type": "Student Book",
        "category": "General French", "chapters": []
    })

    # ---- 4. Tendances A1 with a real, parseable Sommaire (0-4) and
    # a "Unite"/accent heading style content page.
    doc = fitz.open()
    sommaire = doc.new_page()
    sommaire.insert_text((72, 72),
        "Sommaire\n\n"
        "Unite 0 ... p. 4\nUnite 1 ... p. 10\nUnite 2 ... p. 22\n"
        "Unite 3 ... p. 34\nUnite 4 ... p. 46\n"
    )
    for i in range(50):
        p = doc.new_page()
        if i + 2 == 10:
            p.insert_text((72, 72), "Unite 1 - Lecon 1 - Dire son nom\n\n1. Apprenez le vocabulaire.")
        else:
            p.insert_text((72, 72), f"Filler page {i+2}.")
    path_toc = pdf_dir / "Tendances A1.pdf"
    doc.save(str(path_toc))
    doc.close()
    from src.knowledge.sommaire_parser import SommaireParser
    chapters = SommaireParser().parse(str(path_toc))
    entries.append({
        "book_id": "book_004", "title": "Tendances A1",
        "aliases": ["tendances a1", "tendance a1"],
        "filename": path_toc.name, "filepath": str(path_toc).replace("\\", "/"),
        "series": "Tendances", "level": "A1", "book_type": "Student Book",
        "category": "General French", "chapters": chapters
    })

    # ---- 5. A book with a FAKE/non-consecutive numbered page (must
    # NOT be mistaken for a TOC -- the false-positive regression).
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((72, 72),
        "Copyright Notice\n\n"
        "Clause 1 ... p. 2\nClause 3 ... p. 4\n"
        "Clause 5 ... p. 6\nClause 7 ... p. 8\nClause 9 ... p. 12\n"
    )
    for i in range(20):
        doc.new_page().insert_text((72, 72), f"filler {i}")
    path_fake = pdf_dir / "Tendances B1.pdf"
    doc.save(str(path_fake))
    doc.close()
    chapters_fake = SommaireParser().parse(str(path_fake))
    entries.append({
        "book_id": "book_005", "title": "Tendances B1",
        "aliases": ["tendances b1", "tendance b1"],
        "filename": path_fake.name, "filepath": str(path_fake).replace("\\", "/"),
        "series": "Tendances", "level": "B1", "book_type": "Student Book",
        "category": "General French", "chapters": chapters_fake
    })

    catalog_path = fixture_dir / "knowledge_index.json"

    with open(catalog_path, "w", encoding="utf-8") as f:

        json.dump(entries, f, ensure_ascii=False)

    return catalog_path


@pytest.fixture(scope="session")
def query_analyzer(catalog):

    return QueryAnalyzer(knowledge_file=str(catalog))


@pytest.fixture(scope="session")
def search_planner():

    return SearchPlanner()


@pytest.fixture(scope="session")
def metadata_engine(catalog):

    return MetadataFilterEngine(knowledge_file=str(catalog))


@pytest.fixture(scope="session")
def exact_retriever(metadata_engine):

    return ExactRetriever(metadata_engine)


@pytest.fixture(scope="session")
def retriever(metadata_engine, exact_retriever):

    # No real vector store/embedding model in the benchmark suite --
    # semantic_search-action tests are out of scope here (they'd need
    # a real embedding model and are covered separately, not as a
    # fast, dependency-free regression suite).
    return Retriever(
        metadata_engine=metadata_engine,
        exact_retriever=exact_retriever,
        semantic_retriever=None
    )
