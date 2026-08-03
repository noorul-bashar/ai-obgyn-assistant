"""
Thin wrapper around Pinecone so the rest of the app depends only on this
interface, not the Pinecone SDK directly (swap for Chroma/pgvector later
without touching retrieval or ingestion code).

Assumes PINECONE_INDEX_NAME already exists — create it once via
scripts/init_vector_store.py (or Terraform/the Pinecone console). Index
provisioning intentionally does not happen as a side effect of building a
request-time client.
"""
import uuid
from functools import lru_cache

from pinecone import Pinecone, Vector

from app.config import get_settings
from app.services.ingestion.chunker import Chunk

settings = get_settings()


class PineconeVectorStore:
    def __init__(self):
        self._pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self._index = self._pc.index(settings.PINECONE_INDEX_NAME)

    def upsert_chunks(self, chunks: list[Chunk], vectors: list[list[float]]) -> list[str]:
        vector_ids = [str(uuid.uuid4()) for _ in chunks]
        records = [
            Vector(
                id=vector_ids[i],
                values=vectors[i],
                metadata={**chunks[i].metadata, "text": chunks[i].text},
            )
            for i in range(len(chunks))
        ]
        # batch_size lets the SDK split large upserts into parallel batches itself.
        self._index.upsert(vectors=records, batch_size=100)
        return vector_ids

    def query(
        self, query_vector: list[float], top_k: int = 5, metadata_filter: dict | None = None
    ) -> list[dict]:
        results = self._index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
            filter=metadata_filter,
        )
        return [
            {
                "id": match.id,
                "score": match.score,
                "text": (match.metadata or {}).get("text", ""),
                "metadata": match.metadata,
            }
            for match in results.matches
        ]


@lru_cache
def get_vector_store() -> PineconeVectorStore:
    """Cached so the Pinecone client is constructed once per process, not per request."""
    return PineconeVectorStore()
