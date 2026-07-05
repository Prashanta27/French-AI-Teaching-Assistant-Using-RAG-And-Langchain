import json

from src.knowledge.pdf_scanner import PDFScanner


class KnowledgeIndexBuilder:

    def __init__(
        self,
        pdf_folder="data/pdf",
        output_file="data/knowledge_index.json"
    ):

        self.pdf_folder = pdf_folder
        self.output_file = output_file

    def build(self):

        scanner = PDFScanner(self.pdf_folder)

        books = scanner.scan()

        json_data = [
            book.to_dict()
            for book in books
        ]

        with open(
            self.output_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                json_data,
                f,
                indent=4,
                ensure_ascii=False
            )

        print("=" * 60)
        print(f"Indexed {len(json_data)} books")
        print(f"Saved -> {self.output_file}")
        print("=" * 60)


if __name__ == "__main__":

    builder = KnowledgeIndexBuilder()
    builder.build()
