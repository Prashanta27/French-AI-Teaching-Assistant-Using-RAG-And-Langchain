"""
Regression tests for BookDetector tie-breaking.

Covers: "Cosmopolite A2" (with no explicit book_type keyword) must
resolve to the Student Book, not whichever tied match happens to be
first in the catalog (e.g. the Teacher Guide) -- and an explicit
"teacher guide" request must still correctly resolve to the guide.
"""


def test_bare_query_prefers_student_book(query_analyzer):

    result = query_analyzer.analyze("Exercise 3 of page 24 Cosmopolite A2")

    assert result.book == "Cosmopolite A2 main book"
    assert result.book_type == "Student Book"
    assert result.level == "A2"


def test_explicit_teacher_guide_request_resolves_correctly(query_analyzer):

    result = query_analyzer.analyze("Cosmopolite A2 teacher guide")

    assert result.book == "Cosmopolite A2 guide"
    assert result.book_type == "Teacher Guide"


def test_numbered_series_book_matches_cefr_level_phrasing(query_analyzer):
    """
    "Cosmopolite 1" and "Cosmopolite A1" refer to the same book (CEFR
    A1) but use different numbering conventions. The bare-series
    fallback should still resolve this correctly via the level filter,
    not silently return no book.
    """

    result = query_analyzer.analyze("Give me Cosmopolite A1 chapter 2")

    assert result.book == "Cosmopolite 1"
    assert result.level == "A1"


def test_generic_recommendation_query_does_not_pin_a_random_book(query_analyzer):
    """
    Regression test for the dangerous short-alias bug: a generic
    query with no book name mentioned at all must not accidentally
    match some unrelated book via a coincidental substring in a
    stripped-down alias fragment.
    """

    result = query_analyzer.analyze("Which books are available for A1 learners?")

    assert result.book is None
    assert result.level == "A1"
