from app.services.ingestion.embedder import CLIPEmbeddingClient


def test_clip_client_is_the_only_active_embedding_provider():
    client = CLIPEmbeddingClient.__new__(CLIPEmbeddingClient)

    assert client.__class__.__name__ == "CLIPEmbeddingClient"
