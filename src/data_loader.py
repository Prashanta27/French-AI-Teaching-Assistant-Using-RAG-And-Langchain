from langchain_community.document_loaders import PyPDFLoader
from pathlib import Path


### Read all the PDF's inside the directory

def process_all_pdfs(pdf_directory):
    """Process all PDF files in a directory"""

    all_documents = []

    pdf_dir = Path(pdf_directory)

    pdf_files = list(pdf_dir.glob("**/*.pdf"))

    print(f"Found {len(pdf_files)} PDF files to process")

    for pdf_file in pdf_files:

        print(f"\nProcessing: {pdf_file.name}")

        try:
            loader = PyPDFLoader(str(pdf_file))

            documents = loader.load()

            for doc in documents:

                doc.metadata["source_file"] = pdf_file.name
                doc.metadata["file_type"] = "pdf"

            all_documents.extend(documents)

            print(f"✔ Loaded {len(documents)} pages")

        except Exception as e:

            print(f"❌ Error: {e}")

    print(f"\nTotal Documents Loaded: {len(all_documents)}")

    return all_documents

def process_pdf(pdf_path):

    loader = PyPDFLoader(pdf_path)

    documents = loader.load()

    print(f"Loaded {len(documents)} pages from {pdf_path}")

    return documents


if __name__ == "__main__":

    documents = process_all_pdfs("data/pdf")

    print(documents)