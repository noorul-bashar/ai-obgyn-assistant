"""
Turns raw source files (PDF, scanned image) into plain text.

Keeping loaders separate from cleaning/chunking means each new file type
(e.g. DOCX, an HL7 export) only needs a new function here.
"""
from pathlib import Path

import pytesseract
from PIL import Image


def load_pdf_markdown(path: str | Path) -> str:
    """Extract a PDF as layout-aware Markdown with PyMuPDF4LLM."""
    try:
     import pymupdf4llm
    except ImportError as exc:  # pragma: no cover - dependency validation happens at startup/deploy
        raise RuntimeError("pymupdf4llm is required to ingest PDFs") from exc
    return pymupdf4llm.to_markdown(str(path))


def load_image(path: str | Path) -> str:
    """OCR a scanned document/photo (e.g. a lab report photographed on a phone)."""
    image = Image.open(path)
    return pytesseract.image_to_string(image)


def load_document(path: str | Path) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return load_pdf_markdown(path)
    if suffix in {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}:
        return load_image(path)
    raise ValueError(f"Unsupported file type: {suffix}")
