"""
Regression tests for SommaireParser -- covers rejecting non-TOC pages
(e.g. numbered legal/copyright clauses) that coincidentally match the
"keyword N ... page" pattern, and correctly parsing a real TOC.
"""

from src.knowledge.sommaire_parser import SommaireParser


def test_real_toc_is_parsed_correctly(catalog):

    import json

    with open(catalog) as f:
        books = json.load(f)

    book = next(b for b in books if b["title"] == "Tendances A1")

    parser = SommaireParser()

    chapters = parser.parse(book["filepath"])

    numbers = [c["number"] for c in chapters]

    assert numbers == [0, 1, 2, 3, 4]

    chapter_1 = next(c for c in chapters if c["number"] == 1)

    assert chapter_1["start_page"] == 10


def test_non_consecutive_numbers_are_rejected_as_false_positive(catalog):

    import json

    with open(catalog) as f:
        books = json.load(f)

    book = next(b for b in books if b["title"] == "Tendances B1")

    parser = SommaireParser()

    chapters = parser.parse(book["filepath"])

    # "Clause 1, 3, 5, 7, 9" has gaps -- must not be treated as a
    # real table of contents.
    assert chapters == []
