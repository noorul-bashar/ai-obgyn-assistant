from app.config import get_settings
from app.core.exceptions import RetrievalError
from app.services.ingestion.embedder import BaseEmbeddingClient, get_embedding_client
from app.services.rag.vector_store import PineconeVectorStore, get_vector_store

settings = get_settings()


class ClinicalRetriever:
    def __init__(
        self,
        embedding_client: BaseEmbeddingClient | None = None,
        vector_store: PineconeVectorStore | None = None,
    ):
        self.embedding_client = embedding_client or get_embedding_client()
        self.vector_store = vector_store or get_vector_store()

    def retrieve(self, query: str, top_k: int | None = None) -> list[dict]:
        requested_parent_count = top_k or settings.RETRIEVAL_TOP_K
        try:
            query_vector = self.embedding_client.embed_query(query)
            # Several high-ranking children may belong to one parent. Retrieve
            # extra candidates so the LLM still receives the requested number
            # of distinct parent chunks.
            matches = self.vector_store.query(
                query_vector,
                top_k=requested_parent_count * settings.CHILD_RETRIEVAL_MULTIPLIER,
                metadata_filter={
                    "embedding_provider": "clip",
                    "embedding_model": settings.EMBEDDING_MODEL,
                },
            )
        except Exception as exc:  # noqa: BLE001 - normalize any provider error to our own type
            raise RetrievalError(str(exc)) from exc

        parents: list[dict] = []
        seen_parent_ids: set[str] = set()
        for match in matches:
            if match["score"] < settings.MIN_RELEVANCE_SCORE:
                continue
            metadata = match["metadata"] or {}
            parent_id = metadata.get("parent_id", match["id"])
            if parent_id in seen_parent_ids:
                continue
            seen_parent_ids.add(parent_id)
            parents.append({**match, "text": metadata.get("parent_text", match["text"])})
            if len(parents) == requested_parent_count:
                break
        return parents
