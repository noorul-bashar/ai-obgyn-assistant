"""CLIP-only embedding client used for both indexing and retrieval."""
from abc import ABC, abstractmethod
from functools import lru_cache

from app.config import get_settings

settings = get_settings()


class BaseEmbeddingClient(ABC):
    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        ...


class CLIPEmbeddingClient(BaseEmbeddingClient):
    """Use the same local CLIP text encoder for documents and user queries.

    The 512-dimensional CLIP output is L2-normalized and zero-padded to the
    existing 1,024-dimension Pinecone index. This is deliberately the only
    active embedding model; mixing it with Voyage vectors in the same search
    result would make similarity scores unreliable.
    """

    def __init__(self, model_name: str | None = None, target_dim: int | None = None):
        import torch
        from transformers import CLIPModel, CLIPTokenizer

        self._torch = torch
        self._tokenizer = CLIPTokenizer.from_pretrained(model_name or settings.EMBEDDING_MODEL)
        self._model = CLIPModel.from_pretrained(model_name or settings.EMBEDDING_MODEL)
        self._model.eval()
        self._target_dim = target_dim or settings.VECTOR_DIMENSION

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        import torch.nn.functional as functional

        embeddings: list[list[float]] = []
        for start in range(0, len(texts), 32):
            batch = texts[start : start + 32]
            inputs = self._tokenizer(batch, padding=True, truncation=True, return_tensors="pt")
            with self._torch.no_grad():
                features = self._model.get_text_features(**inputs)
                # Transformers versions return either a tensor or a model
                # output containing the pooled text representation.
                if hasattr(features, "text_embeds"):
                    features = features.text_embeds
                elif hasattr(features, "pooler_output"):
                    features = features.pooler_output
                features = functional.normalize(features, p=2, dim=1)
                if features.shape[1] > self._target_dim:
                    raise RuntimeError(
                        f"CLIP returned {features.shape[1]} dimensions, exceeding the "
                        f"{self._target_dim}-dimension Pinecone index"
                    )
                if features.shape[1] < self._target_dim:
                    features = functional.pad(features, (0, self._target_dim - features.shape[1]))
            embeddings.extend(features.tolist())
        return embeddings

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]


@lru_cache
def get_embedding_client() -> BaseEmbeddingClient:
    """Cached so the local CLIP model is loaded only once per process."""
    return CLIPEmbeddingClient()
