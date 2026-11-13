
from pathlib import Path


def load_pdf(file_path: str):
    from langchain_community.document_loaders import PyPDFLoader

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    loader = PyPDFLoader(str(path))

    documents = loader.load()

    return documents

