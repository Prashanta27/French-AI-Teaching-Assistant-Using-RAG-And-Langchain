from dataclasses import dataclass, field
from typing import List


@dataclass
class Book:

    book_id: str
    title: str
    aliases: List[str]
    filename: str
    filepath: str
    series: str
    level: str
    book_type: str
    category: str
    publisher: str
    total_pages: int

    language: str = "French"
    chunks: int = 0
    chapters: List[str] = field(default_factory=list)
    has_toc: bool = False
    is_indexed: bool = True

    def to_dict(self):

        return {

            "book_id": self.book_id,
            "title": self.title,
            "aliases": self.aliases,
            "filename": self.filename,
            "filepath": self.filepath,
            "series": self.series,
            "level": self.level,
            "book_type": self.book_type,
            "category": self.category,
            "publisher": self.publisher,
            "language": self.language,
            "total_pages": self.total_pages,
            "chunks": self.chunks,
            "chapters": self.chapters,
            "has_toc": self.has_toc,
            "is_indexed": self.is_indexed

        }
