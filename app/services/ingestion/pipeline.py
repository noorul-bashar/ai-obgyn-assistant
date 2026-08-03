"""
Standalone ingestion pipeline: load -> clean -> chunk -> embed -> upsert.

This module has no FastAPI/HTTP dependency on purpose — it's called both
from the API (document upload endpoint) and from the CLI script in
scripts/ingest_documents.py, so it can run as its own job outside the web
process if ingestion volume grows.
"""
import logging
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models.document import DocumentSourceType, DocumentStatus, IngestedDocument
from app.services.ingestion.chunker import chunk_markdown
from app.services.ingestion.cleaner import clean_text
from app.services.ingestion.embedder import BaseEmbeddingClient, get_embedding_client
from app.services.ingestion.loaders import load_document
from app.services.rag.vector_store import PineconeVectorStore, get_vector_store

logger = logging.getLogger(__name__)
settings = get_settings()


class IngestionPipeline:
    def __init__(
        self,
        embedding_client: BaseEmbeddingClient | None = None,
        vector_store: PineconeVectorStore | None = None,
    ):
        self.embedding_client = embedding_client or get_embedding_client()
        self.vector_store = vector_store or get_vector_store()

    def run(
        self,
        db: Session,
        file_path: str | Path,
        patient_id: uuid.UUID | None = None,
    ) -> IngestedDocument:
        file_path = Path(file_path)
        source_type = (
            DocumentSourceType.PDF if file_path.suffix.lower() == ".pdf" else DocumentSourceType.IMAGE
        )
        doc_id = uuid.uuid4()

        doc_record = IngestedDocument(
            id=doc_id,
            filename=file_path.name,
            source_type=source_type,
            status=DocumentStatus.PROCESSING,
            patient_id=patient_id,
            # Defaults are normally set by a database flush. Set them now as
            # well, so a database outage returns a valid failure response.
            chunk_count=0,
            vector_ids=[],
        )

        db_available = True
        try:
            if db:
                db.add(doc_record)
                db.commit()
                db.refresh(doc_record)
        except Exception as db_exc:
            logger.warning("Database insert failed for document %s: %s", file_path.name, db_exc)
            db_available = False
            try:
                if db:
                    db.rollback()
            except Exception:
                pass

        try:
            raw_text = load_document(file_path)
            cleaned = clean_text(raw_text)
            chunk_metadata = {
                "document_id": str(doc_record.id),
                "filename": file_path.name,
                "embedding_provider": "clip",
                "embedding_model": settings.EMBEDDING_MODEL,
            }
            if patient_id:
                chunk_metadata["patient_id"] = str(patient_id)

            chunks = chunk_markdown(
                cleaned,
                parent_chunk_size=settings.PARENT_CHUNK_SIZE,
                parent_chunk_overlap=settings.PARENT_CHUNK_OVERLAP,
                child_chunk_size=settings.CHILD_CHUNK_SIZE,
                child_chunk_overlap=settings.CHILD_CHUNK_OVERLAP,
                metadata=chunk_metadata,
            )

            if not chunks:
                doc_record.status = DocumentStatus.FAILED
                doc_record.error_message = "No extractable text was found in this file."
                doc_record.chunk_count = 0
            else:
                vectors = self.embedding_client.embed_documents([c.text for c in chunks])
                vector_ids = self.vector_store.upsert_chunks(chunks, vectors)

                doc_record.status = DocumentStatus.COMPLETED
                doc_record.chunk_count = len(chunks)
                doc_record.vector_ids = vector_ids

        except Exception as exc:  # noqa: BLE001 - we want to persist *any* failure reason
            logger.exception("Ingestion failed for %s", file_path)
            doc_record.status = DocumentStatus.FAILED
            doc_record.error_message = str(exc)[:1024]

        if db_available:
            try:
                if db:
                    db.commit()
                    db.refresh(doc_record)
            except Exception as db_commit_exc:
                logger.warning("Final DB commit failed: %s", db_commit_exc)
                try:
                    if db:
                        db.rollback()
                except Exception:
                    pass

        return doc_record
