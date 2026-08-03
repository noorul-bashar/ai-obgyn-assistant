import pytest
import tiktoken

from app.db.models.document import DocumentStatus
from app.services.ingestion.chunker import chunk_markdown, chunk_text
from app.services.ingestion.pipeline import IngestionPipeline
from app.services.ingestion.cleaner import clean_text


def test_clean_text_collapses_whitespace():
    raw = "Hello   world\n\n\n\nPage 1 of 3"
    cleaned = clean_text(raw)
    assert "   " not in cleaned
    assert "Page 1 of 3" not in cleaned


def test_chunk_text_uses_token_limits():
    text = "clinically relevant " * 100
    chunks = chunk_text(text, chunk_size=32, overlap=4)
    encoder = tiktoken.get_encoding("cl100k_base")

    assert len(chunks) > 1
    assert all(len(encoder.encode(chunk.text)) <= 32 for chunk in chunks)


def test_markdown_parent_child_chunking_preserves_headers_and_parent_context():
    markdown = "# Male reproductive anatomy\n\n## Testes\n\n" + ("The testes produce sperm and testosterone. " * 80)

    chunks = chunk_markdown(
        markdown,
        parent_chunk_size=64,
        parent_chunk_overlap=8,
        child_chunk_size=16,
        child_chunk_overlap=2,
        metadata={"document_id": "document-1"},
    )

    assert len(chunks) > 1
    assert all(chunk.metadata["chunk_level"] == "child" for chunk in chunks)
    assert all(chunk.metadata["parent_text"] for chunk in chunks)
    assert all(chunk.metadata["document_id"] == "document-1" for chunk in chunks)
    assert all(chunk.metadata["header_1"] == "Male reproductive anatomy" for chunk in chunks)
    assert all(chunk.metadata["header_2"] == "Testes" for chunk in chunks)
    assert len({chunk.metadata["parent_id"] for chunk in chunks}) > 1


def test_chunk_text_rejects_bad_overlap():
    with pytest.raises(ValueError):
        chunk_text("short text", chunk_size=100, overlap=100)


def test_database_outage_returns_a_valid_failed_ingestion_record(monkeypatch, tmp_path):
    class UnavailableDb:
        def add(self, record):
            pass

        def commit(self):
            raise ConnectionError("PostgreSQL unavailable")

        def rollback(self):
            pass

    class FailingEmbeddings:
        def embed_documents(self, texts):
            raise RuntimeError("Voyage quota exceeded")

    class UnusedVectorStore:
        pass

    monkeypatch.setattr("app.services.ingestion.pipeline.load_document", lambda path: "# Heading\n\nClinical text")
    pipeline = IngestionPipeline(embedding_client=FailingEmbeddings(), vector_store=UnusedVectorStore())

    result = pipeline.run(UnavailableDb(), tmp_path / "reference.pdf")

    assert result.status == DocumentStatus.FAILED
    assert result.chunk_count == 0
    assert result.error_message == "Voyage quota exceeded"
