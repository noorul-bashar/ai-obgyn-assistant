"""LangChain parent-child chunking for retrieval-augmented generation."""
from dataclasses import dataclass, field
import uuid

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


@dataclass
class Chunk:
    """A child chunk to embed and persist in Pinecone."""

    text: str
    metadata: dict = field(default_factory=dict)


def _token_splitter(chunk_size: int, chunk_overlap: int) -> RecursiveCharacterTextSplitter:
    if chunk_size <= 0 or chunk_overlap < 0 or chunk_size <= chunk_overlap:
        raise ValueError("chunk_size must be positive and greater than chunk_overlap")
    return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def chunk_markdown(
    markdown: str,
    *,
    parent_chunk_size: int = 1024,
    parent_chunk_overlap: int = 128,
    child_chunk_size: int = 256,
    child_chunk_overlap: int = 32,
    metadata: dict | None = None,
) -> list[Chunk]:
    """Build child chunks with their complete parent context in metadata.

    PDFs are extracted as Markdown first. LangChain then splits on Markdown
    headings (``#``, ``##``, ``###``), forms parent chunks for LLM context,
    and sub-splits each parent into smaller child chunks for embedding. The
    child's ``parent_text`` is stored with its vector so retrieval can expand
    a semantically matched child back to its 1,024-token parent.
    """
    if not markdown.strip():
        return []

    base_metadata = metadata or {}
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "header_1"), ("##", "header_2"), ("###", "header_3")],
        strip_headers=False,
    )
    parent_splitter = _token_splitter(parent_chunk_size, parent_chunk_overlap)
    child_splitter = _token_splitter(child_chunk_size, child_chunk_overlap)

    header_sections = header_splitter.split_text(markdown)
    parent_documents = parent_splitter.split_documents(header_sections)
    child_chunks: list[Chunk] = []

    for parent_index, parent_document in enumerate(parent_documents):
        parent_text = parent_document.page_content.strip()
        if not parent_text:
            continue

        parent_id = str(uuid.uuid4())
        child_documents = child_splitter.split_documents([parent_document])
        for child_index, child_document in enumerate(child_documents):
            child_text = child_document.page_content.strip()
            if not child_text:
                continue
            child_chunks.append(
                Chunk(
                    text=child_text,
                    metadata={
                        **base_metadata,
                        **child_document.metadata,
                        "chunking_strategy": "langchain_parent_child_v1",
                        "chunk_level": "child",
                        "parent_id": parent_id,
                        "parent_index": parent_index,
                        "child_index": child_index,
                        "parent_text": parent_text,
                    },
                )
            )

    return child_chunks


def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 120,
    metadata: dict | None = None,
) -> list[Chunk]:
    """Compatibility wrapper for non-Markdown callers.

    New ingestion uses :func:`chunk_markdown` with explicit parent/child token
    limits. This keeps the previous public helper available for image/OCR
    callers and tests while using LangChain's recursive splitter.
    """
    splitter = _token_splitter(chunk_size, overlap)
    return [
        Chunk(text=document.page_content, metadata={**(metadata or {}), **document.metadata})
        for document in splitter.create_documents([text])
        if document.page_content.strip()
    ]
