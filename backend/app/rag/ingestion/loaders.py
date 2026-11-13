import csv
from pathlib import Path

from app.rag.ingestion.pdf_loader import load_pdf
from langchain_core.documents import Document

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".markdown", ".csv"}


def load_document(file_path: Path) -> list[Document]:
    extension = file_path.suffix.lower()
    if extension == ".pdf":
        return load_pdf(str(file_path))
    if extension == ".docx":
        return _load_docx(file_path)
    if extension in {".txt", ".md", ".markdown"}:
        return _load_text(file_path)
    if extension == ".csv":
        return _load_csv(file_path)
    raise ValueError(f"Unsupported document type: {extension or 'unknown'}")


def _load_docx(file_path: Path) -> list[Document]:
    try:
        from docx import Document as DocxDocument
    except ImportError as exc:
        raise RuntimeError("DOCX support requires the python-docx package") from exc

    document = DocxDocument(str(file_path))
    text = "\n".join(
        paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()
    )
    return [Document(page_content=text, metadata={"source": file_path.name})]


def _load_text(file_path: Path) -> list[Document]:
    return [
        Document(
            page_content=file_path.read_text(encoding="utf-8-sig"),
            metadata={"source": file_path.name},
        )
    ]


def _load_csv(file_path: Path) -> list[Document]:
    with file_path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream))
    content = "\n".join(" | ".join(row) for row in rows)
    return [Document(page_content=content, metadata={"source": file_path.name})]
