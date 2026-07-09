"""
Regression tests for ExactRetriever's heading/exercise pattern
matching -- covers the bare-numbered exercise format ("3." with no
"Exercise"/"Exercice" word) and "Unite"/"Unité" chapter headings
found in real books this session.
"""


class FakePlan:

    def __init__(self, filters, target_books, exact_location):

        self.filters = filters
        self.target_books = target_books
        self.exact_location = exact_location


def test_bare_numbered_exercise_is_found(exact_retriever):
    """
    Many workbooks number exercises as bare "1.", "2.", "3." with no
    "Exercise"/"Exercice" word at all.
    """

    plan = FakePlan(
        {"series": "Cosmopolite"}, ["Cosmopolite 1"], {"page": 2, "exercise": 3}
    )

    results = exact_retriever.retrieve(plan)

    assert len(results) == 1
    assert results[0].found is True
    assert "Completez avec" in results[0].content
    # must not leak into the next exercise's content
    assert "Choisissez" not in results[0].content


def test_unite_heading_is_found_via_scan(exact_retriever):
    """
    "Unité"/"Unite" (French) must match, not just the English "unit".
    """

    plan = FakePlan(
        {"series": "Tendances"}, ["Tendances A1"], {"chapter": 1}
    )

    results = exact_retriever.retrieve(plan)

    assert len(results) == 1
    assert results[0].found is True


def test_chapter_lookup_uses_precomputed_toc_not_full_scan(exact_retriever):
    """
    When a valid TOC was parsed at indexing time, chapter lookup
    should land on the real content page (10), not the Sommaire page
    (1) where the heading text also happens to appear.
    """

    plan = FakePlan(
        {"series": "Tendances"}, ["Tendances A1"], {"chapter": 1}
    )

    results = exact_retriever.retrieve(plan)

    assert results[0].page == 10
    assert "note" not in results[0].warning if results[0].warning else True
