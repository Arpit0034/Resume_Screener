"""Turn uploaded resume files (bytes) into plain text."""
import io
from pathlib import Path

from docx import Document
from pypdf import PdfReader

SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".txt"]


def read_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted and not reader.decrypt(""):
        raise ValueError("The PDF is password-protected.")
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(p for p in pages if p.strip())


def read_docx(data: bytes) -> str:
    document = Document(io.BytesIO(data))
    lines = [p.text for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            seen = None
            for cell in row.cells:
                text = cell.text.strip()
                if text and text != seen:  # merged cells repeat their text
                    lines.append(text)
                seen = text
    return "\n".join(lines)


def extract_text(file_name: str, data: bytes) -> str:
    suffix = Path(file_name).suffix.lower()
    if suffix == ".pdf":
        return read_pdf(data)
    if suffix == ".docx":
        return read_docx(data)
    if suffix == ".txt":
        return data.decode("utf-8", errors="ignore")
    raise ValueError(f"Unsupported file type: {suffix or 'unknown'}")
