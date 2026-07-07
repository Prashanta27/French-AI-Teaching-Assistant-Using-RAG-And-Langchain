"""
ExactRetriever
==============

Deterministically fetches a specific chapter / page / exercise /
activity / line from a book's source PDF, given a SearchPlan whose
action is "fetch_exact_section".

Lookup strategy, fastest first:
  1. Precomputed chapter index (book["chapters"], if the ingestion
     pipeline has populated it) -- O(1). Supports both a single
     start_page and a start_page/end_page range.
  2. Direct page open (when `page` is given) -- O(1).
  3. Full-document heading scan (when only chapter/exercise/activity
     is given, with no page) -- O(pages). Deliberate fallback, not
     the primary strategy -- it exists so the system still works
     before per-book chapter indexing is built.

Not yet supported (deliberately out of scope here): detecting
Grammar/Vocabulary/Dialogue/Task/Section-style headings. That needs
StructureDetector/QueryAnalysis to grow matching fields first --
adding heading patterns for them in this file with nothing upstream
ever populating `exact_location` accordingly would just be dead code.
"""

import logging
import re
import threading
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
import fitz  # PyMuPDF


logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Result Object
# ---------------------------------------------------------

@dataclass
class ExactRetrievalResult:

    book_id: Optional[str]
    title: Optional[str]
    found: bool

    page: Optional[int] = None
    page_range: Optional[Tuple[int, int]] = None
    chapter: Optional[int] = None
    exercise: Optional[int] = None
    activity: Optional[int] = None
    line: Optional[int] = None

    content: Optional[str] = None

    # Character offsets of `content` within the page's extracted
    # text, and its pixel bounding box (x0, y0, x1, y1) on the page
    # when known -- both are for downstream citation/highlighting.
    # Not populated for multi-page page_range results (a bbox/offset
    # pair only makes sense for a single page).
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    bbox: Optional[Tuple[float, float, float, float]] = None

    # 1.0 for a deterministic exact match, 0.0 when not found. Kept
    # so a downstream merge step can rank this alongside
    # SemanticRetriever results (which will carry a real similarity
    # score) without special-casing "this came from ExactRetriever".
    score: float = 0.0

    warning: Optional[str] = None
    note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:

        return asdict(self)


# ---------------------------------------------------------
# Exact Retriever
# ---------------------------------------------------------

class ExactRetriever:
    """
    Deterministic content lookup for RetrieveChapter / RetrievePage /
    RetrieveExercise / RetrieveLine style SearchPlans.

    Parameters
    ----------
    metadata_engine:
        A MetadataFilterEngine instance -- used to resolve
        SearchPlan.filters/target_books into concrete book records
        (book_id, filepath, ...), so this class never touches
        knowledge_index.json directly.
    default_page_offset:
        Fallback added to a user-facing page number before mapping
        it to a PDF page index, used only when the book record itself
        has no "page_offset". Real textbooks often have unnumbered
        front matter (cover, table of contents), so "page 1" as
        printed may not be PDF page index 0 -- prefer setting
        book["page_offset"] per book once real offsets are known;
        this constructor value is just a global default.
    """

    # {n} is substituted with the target number before compiling.
    # SEP allows the separators real textbooks actually use between
    # a keyword and its number: "Exercise 4", "Exercise: 4",
    # "Exercise-4", "Exercise #4".
    _SEP = r'[\s:\-#]*'

    CHAPTER_HEADING_PATTERNS = [
        rf'chapter{_SEP}{{n}}\b',
        rf'chapitre{_SEP}{{n}}\b',
        rf'unit{_SEP}{{n}}\b',
        rf'lesson{_SEP}{{n}}\b',
        rf'module{_SEP}{{n}}\b',
        rf'dossier{_SEP}{{n}}\b',
        rf'le[cç]on{_SEP}{{n}}\b'
    ]

    EXERCISE_HEADING_PATTERNS = [
        rf'exercise{_SEP}{{n}}\b',
        rf'exercice{_SEP}{{n}}\b',
        rf'ex\.?{_SEP}{{n}}\b',
        rf'exercice\s*n[°o]\s*{{n}}\b'
    ]

    ACTIVITY_HEADING_PATTERNS = [
        rf'activity{_SEP}{{n}}\b',
        rf'activit[ée]{_SEP}{{n}}\b',
        rf'activit[ée]\s*n[°o]\s*{{n}}\b'
    ]

    # "Family" patterns (no specific number) used only to find the
    # *next* heading of the same kind, to bound a heading block --
    # e.g. so "Exercise 4" content stops before "Exercise 5" starts
    # instead of running to the end of the page.
    CHAPTER_FAMILY_PATTERN = (
        rf'(?:chapter|chapitre|unit|lesson|module|dossier|le[cç]on)'
        rf'{_SEP}\d+'
    )

    EXERCISE_FAMILY_PATTERN = (
        rf'(?:exercise|exercice|ex\.?)'
        rf'(?:{_SEP}\d+|\s*n[°o]\s*\d+)'
    )

    ACTIVITY_FAMILY_PATTERN = (
        rf'(?:activity|activit[ée])'
        rf'(?:{_SEP}\d+|\s*n[°o]\s*\d+)'
    )

    def __init__(self, metadata_engine, default_page_offset: int = 0):

        self.metadata_engine = metadata_engine

        self.default_page_offset = default_page_offset

        # filepath -> fitz.Document. Opening a PDF is expensive
        # enough (especially large scanned textbooks) that reopening
        # it on every single query would be a real bottleneck under
        # concurrent use.
        self._doc_cache: Dict[str, fitz.Document] = {}

        # PyMuPDF Document objects are not safe for unsynchronized
        # concurrent access from multiple threads. A single coarse
        # lock is simpler and safer than per-document locks, at the
        # cost of serializing access across *different* books too --
        # an acceptable trade-off until this becomes a measured
        # bottleneck, at which point a per-filepath lock dict is the
        # natural next step.
        self._lock = threading.Lock()

    # -----------------------------------------------------
    # Public API
    # -----------------------------------------------------

    def retrieve(self, plan) -> List[ExactRetrievalResult]:
        """
        plan: a SearchPlan (action == "fetch_exact_section").

        Returns one result per candidate book. Normally that's a
        single book, but a loose filter (e.g. only `level`, no
        specific title) can legitimately match several -- every
        candidate gets its own result rather than silently guessing
        which one the user meant.
        """

        if not plan.exact_location:

            logger.warning(
                "ExactRetriever.retrieve() called with an empty "
                "exact_location -- nothing to look up."
            )

            return [ExactRetrievalResult(
                book_id=None,
                title=None,
                found=False,
                warning=(
                    "No page/chapter/exercise/activity/line was "
                    "provided -- nothing to look up."
                )
            )]

        books = self._candidate_books(plan)

        if not books:

            logger.info(
                "No candidate books matched filters=%s target_books=%s",
                plan.filters, plan.target_books
            )

            return [ExactRetrievalResult(
                book_id=None,
                title=None,
                found=False,
                warning=(
                    "No book matched the given filters -- cannot "
                    "look up an exact location without knowing which "
                    "book to open."
                )
            )]

        with self._lock:

            return [
                self._locate_in_book(book, plan.exact_location)
                for book in books
            ]

    # -----------------------------------------------------

    def close_all(self):
        """
        Close every cached PDF. Call this after re-indexing (new
        knowledge_index.json / replaced PDFs) so stale file handles
        and pages aren't served from the cache.
        """

        with self._lock:

            for doc in self._doc_cache.values():

                doc.close()

            self._doc_cache.clear()

    # -----------------------------------------------------
    # Book resolution
    # -----------------------------------------------------

    def _candidate_books(self, plan) -> List[Dict]:

        matches = self.metadata_engine.apply(plan.filters)

        if plan.target_books:

            titles = set(plan.target_books)

            return [b for b in matches if b["title"] in titles]

        return matches

    # -----------------------------------------------------

    def _get_document(self, filepath: str) -> fitz.Document:

        doc = self._doc_cache.get(filepath)

        if doc is not None:

            return doc

        doc = fitz.open(filepath)

        self._doc_cache[filepath] = doc

        return doc

    # -----------------------------------------------------
    # Per-book dispatch
    # -----------------------------------------------------

    def _locate_in_book(
        self,
        book: Dict,
        location: Dict[str, int]
    ) -> ExactRetrievalResult:

        book_id = book.get("book_id")

        title = book.get("title")

        filepath = book.get("filepath")

        if not filepath:

            logger.error("Book %s (%s) has no filepath.", book_id, title)

            return ExactRetrievalResult(
                book_id=book_id,
                title=title,
                found=False,
                warning="This book has no filepath on record."
            )

        page_offset = book.get("page_offset", self.default_page_offset)

        # Fast path: a precomputed chapter index, if the ingestion
        # pipeline has populated book["chapters"] as
        # [{"number": 2, "start_page": 5, "end_page": 7}, ...].
        # `end_page` is optional -- a single-page chapter only needs
        # start_page.
        if "page" not in location and "chapter" in location:

            precomputed = self._lookup_precomputed_chapter(
                book, location["chapter"]
            )

            if precomputed is not None:

                start_page, end_page = precomputed

                if end_page and end_page != start_page:

                    try:

                        doc = self._get_document(filepath)

                        result = self._locate_page_range(
                            doc, start_page, end_page, page_offset
                        )

                        result.chapter = location["chapter"]

                    except Exception:

                        logger.exception(
                            "Failed to open PDF at '%s'.", filepath
                        )

                        result = ExactRetrievalResult(
                            book_id=book_id,
                            title=title,
                            found=False,
                            warning=f"Could not open PDF at '{filepath}'."
                        )

                    result.book_id = book_id

                    result.title = title

                    return result

                location = {**location, "page": start_page}

        try:

            doc = self._get_document(filepath)

        except Exception:

            logger.exception("Failed to open PDF at '%s'.", filepath)

            return ExactRetrievalResult(
                book_id=book_id,
                title=title,
                found=False,
                warning=f"Could not open PDF at '{filepath}'."
            )

        if "page" in location:

            result = self._locate_by_page(doc, location, page_offset)

        else:

            result = self._locate_by_heading(doc, location)

        result.book_id = book_id

        result.title = title

        return result

    # -----------------------------------------------------

    @staticmethod
    def _lookup_precomputed_chapter(
        book: Dict,
        chapter_number: int
    ) -> Optional[Tuple[int, Optional[int]]]:

        for entry in book.get("chapters") or []:

            if entry.get("number") == chapter_number:

                return entry.get("start_page"), entry.get("end_page")

        return None

    # -----------------------------------------------------
    # Multi-page chapter range
    # -----------------------------------------------------

    def _locate_page_range(
        self,
        doc: fitz.Document,
        start_page: int,
        end_page: int,
        page_offset: int
    ) -> ExactRetrievalResult:

        start_index = start_page - 1 + page_offset

        end_index = end_page - 1 + page_offset

        if start_index < 0 or end_index >= len(doc) or start_index > end_index:

            return ExactRetrievalResult(
                book_id=None,
                title=None,
                found=False,
                page_range=(start_page, end_page),
                warning=(
                    f"Page range {start_page}-{end_page} is out of "
                    f"bounds (book has {len(doc)} pages)."
                )
            )

        parts = [
            doc[i].get_text().strip()
            for i in range(start_index, end_index + 1)
        ]

        return ExactRetrievalResult(
            book_id=None,
            title=None,
            found=True,
            page=start_page,
            page_range=(start_page, end_page),
            content="\n\n---\n\n".join(parts),
            score=1.0,
            note=(
                "Multi-page result from a precomputed chapter range -- "
                "no single bbox/char-offset applies across pages."
            )
        )

    # -----------------------------------------------------
    # Page-based lookup
    # -----------------------------------------------------

    def _locate_by_page(
        self,
        doc: fitz.Document,
        location: Dict[str, int],
        page_offset: int
    ) -> ExactRetrievalResult:

        page_number = location["page"]

        index = page_number - 1 + page_offset

        if index < 0 or index >= len(doc):

            return ExactRetrievalResult(
                book_id=None,
                title=None,
                found=False,
                page=page_number,
                warning=(
                    f"Page {page_number} is out of range "
                    f"(book has {len(doc)} pages)."
                )
            )

        page = doc[index]

        text = page.get_text()

        if "exercise" in location:

            return self._extract_heading_block(
                page, text, location["exercise"],
                self.EXERCISE_HEADING_PATTERNS, self.EXERCISE_FAMILY_PATTERN,
                page_number, field="exercise"
            )

        if "activity" in location:

            return self._extract_heading_block(
                page, text, location["activity"],
                self.ACTIVITY_HEADING_PATTERNS, self.ACTIVITY_FAMILY_PATTERN,
                page_number, field="activity"
            )

        if "line" in location:

            return self._extract_line(page, location["line"], page_number)

        return ExactRetrievalResult(
            book_id=None,
            title=None,
            found=True,
            page=page_number,
            content=text.strip(),
            start_char=0,
            end_char=len(text.strip()),
            score=1.0
        )

    # -----------------------------------------------------
    # Line extraction -- structured (dict) mode instead of naive
    # "\n".split(), which can fragment or merge lines depending on
    # how the PDF encodes text runs.
    # -----------------------------------------------------

    def _extract_line(
        self,
        page: fitz.Page,
        line_number: int,
        page_number: int
    ) -> ExactRetrievalResult:

        lines = []

        for block in page.get_text("dict").get("blocks", []):

            for line in block.get("lines", []):

                text = "".join(
                    span.get("text", "") for span in line.get("spans", [])
                ).strip()

                if not text:

                    continue

                bbox = line.get("bbox")

                lines.append((text, bbox))

        index = line_number - 1

        if index < 0 or index >= len(lines):

            return ExactRetrievalResult(
                book_id=None,
                title=None,
                found=False,
                page=page_number,
                line=line_number,
                warning=(
                    f"Line {line_number} is out of range on page "
                    f"{page_number} ({len(lines)} lines found)."
                )
            )

        text, bbox = lines[index]

        return ExactRetrievalResult(
            book_id=None,
            title=None,
            found=True,
            page=page_number,
            line=line_number,
            content=text,
            bbox=tuple(bbox) if bbox else None,
            score=1.0
        )

    # -----------------------------------------------------
    # Bounded heading-block extraction (page already known)
    # -----------------------------------------------------

    def _extract_heading_block(
        self,
        page: fitz.Page,
        text: str,
        number: int,
        patterns: List[str],
        family_pattern: str,
        page_number: int,
        field: str
    ) -> ExactRetrievalResult:

        match = self._first_match(text, patterns, number)

        if not match:

            return ExactRetrievalResult(
                book_id=None,
                title=None,
                found=False,
                page=page_number,
                **{field: number},
                warning=f"Could not find {field} {number} on page {page_number}."
            )

        start = match.start()

        end = self._next_family_boundary(text, family_pattern, after=match.end())

        content = text[start:end].strip()

        bbox = self._bbox_for(page, match.group())

        return ExactRetrievalResult(
            book_id=None,
            title=None,
            found=True,
            page=page_number,
            content=content,
            start_char=start,
            end_char=start + len(content),
            bbox=bbox,
            score=1.0,
            **{field: number}
        )

    # -----------------------------------------------------

    @staticmethod
    def _first_match(text: str, patterns: List[str], number: int):

        # Anchored to the start of a line (allowing leading
        # whitespace) -- real headings sit on their own line. Without
        # this anchor, a stray "...exercise 4..." occurring mid-
        # sentence in body text (e.g. referencing exercise 4 while
        # describing exercise 5) would be matched instead of the
        # actual heading.
        for pattern in patterns:

            compiled = re.compile(
                r'^\s*' + pattern.format(n=number),
                re.IGNORECASE | re.MULTILINE
            )

            match = compiled.search(text)

            if match:

                return match

        return None

    # -----------------------------------------------------

    @staticmethod
    def _next_family_boundary(text: str, family_pattern: str, after: int) -> int:
        """
        Find where the *next* heading of the same family starts,
        after `after`, so a heading block stops there instead of
        running to the end of the page/document. Anchored to line
        start for the same reason as `_first_match`.
        """

        compiled = re.compile(
            r'^\s*' + family_pattern,
            re.IGNORECASE | re.MULTILINE
        )

        match = compiled.search(text, pos=after)

        return match.start() if match else len(text)

    # -----------------------------------------------------

    @staticmethod
    def _bbox_for(
        page: fitz.Page,
        heading_text: str
    ) -> Optional[Tuple[float, float, float, float]]:

        try:

            rects = page.search_for(heading_text)

        except Exception:

            return None

        if not rects:

            return None

        r = rects[0]

        return (r.x0, r.y0, r.x1, r.y1)

    # -----------------------------------------------------
    # Heading-scan lookup (no page given)
    # -----------------------------------------------------

    def _locate_by_heading(
        self,
        doc: fitz.Document,
        location: Dict[str, int]
    ) -> ExactRetrievalResult:

        if "exercise" in location:

            patterns, family, number, field = (
                self.EXERCISE_HEADING_PATTERNS, self.EXERCISE_FAMILY_PATTERN,
                location["exercise"], "exercise"
            )

        elif "activity" in location:

            patterns, family, number, field = (
                self.ACTIVITY_HEADING_PATTERNS, self.ACTIVITY_FAMILY_PATTERN,
                location["activity"], "activity"
            )

        elif "chapter" in location:

            patterns, family, number, field = (
                self.CHAPTER_HEADING_PATTERNS, self.CHAPTER_FAMILY_PATTERN,
                location["chapter"], "chapter"
            )

        else:

            return ExactRetrievalResult(
                book_id=None,
                title=None,
                found=False,
                warning=(
                    "No page/chapter/exercise/activity/line given -- "
                    "nothing to look up."
                )
            )

        logger.debug(
            "Scanning %d pages for %s %s (no precomputed index/page given).",
            len(doc), field, number
        )

        for page_index in range(len(doc)):

            page = doc[page_index]

            text = page.get_text()

            match = self._first_match(text, patterns, number)

            if match:

                start = match.start()

                end = self._next_family_boundary(text, family, after=match.end())

                content = text[start:end].strip()

                bbox = self._bbox_for(page, match.group())

                return ExactRetrievalResult(
                    book_id=None,
                    title=None,
                    found=True,
                    page=page_index + 1,
                    content=content,
                    start_char=start,
                    end_char=start + len(content),
                    bbox=bbox,
                    score=1.0,
                    note=(
                        "Located via a full-document heading scan -- "
                        "consider precomputing book['chapters'] during "
                        "ingestion for O(1) lookups instead."
                    ),
                    **{field: number}
                )

        return ExactRetrievalResult(
            book_id=None,
            title=None,
            found=False,
            **{field: number},
            warning=f"Could not find {field} {number} anywhere in the book."
        )


# ---------------------------------------------------------
# Testing
# ---------------------------------------------------------

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    from src.retriever.metadata_filter import MetadataFilterEngine

    class FakePlan:
        def __init__(self, filters, target_books, exact_location):
            self.filters = filters
            self.target_books = target_books
            self.exact_location = exact_location

    engine = MetadataFilterEngine()
    retriever = ExactRetriever(engine)

    test_plans = [

        ("direct page", FakePlan({"series": "Cosmopolite"}, ["Cosmopolite A1"], {"page": 2})),
        ("page + line (dict-mode)", FakePlan({"series": "Cosmopolite"}, ["Cosmopolite A1"], {"page": 1, "line": 2})),
        ("chapter via precomputed single page", FakePlan({"series": "Cosmopolite"}, ["Cosmopolite A1"], {"chapter": 2})),
        ("chapter via precomputed RANGE", FakePlan({"series": "Cosmopolite"}, ["Cosmopolite A1"], {"chapter": 3})),
        ("exercise via heading scan, n\u00b0 notation", FakePlan({"series": "Cosmopolite"}, ["Cosmopolite A1"], {"exercise": 4})),
        ("exercise 5 via 'Exercise: 5' separator", FakePlan({"series": "Cosmopolite"}, ["Cosmopolite A1"], {"page": 4, "exercise": 5})),
        ("exercise 4 boundary should NOT include exercise 5", FakePlan({"series": "Cosmopolite"}, ["Cosmopolite A1"], {"page": 4, "exercise": 4})),
        ("out of range page", FakePlan({"series": "Cosmopolite"}, ["Cosmopolite A1"], {"page": 99})),
        ("nonexistent chapter", FakePlan({"series": "Cosmopolite"}, ["Cosmopolite A1"], {"chapter": 9})),

    ]

    for label, plan in test_plans:

        print("=" * 70)
        print(label, "|", plan.exact_location)

        for result in retriever.retrieve(plan):

            for k, v in result.to_dict().items():

                if v is not None:

                    print(f"  {k:12}: {v}")

    # cache check
    print("=" * 70)
    print("Cached documents:", list(retriever._doc_cache.keys()))