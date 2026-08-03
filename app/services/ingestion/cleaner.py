import re


def clean_text(raw_text: str) -> str:
    """
    Normalizes OCR/PDF-extraction noise before chunking:
    - collapses repeated whitespace
    - drops common page-header/footer artifacts
    - strips stray null bytes
    """
    text = raw_text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"Page \d+ of \d+", "", text, flags=re.IGNORECASE)
    return text.strip()
