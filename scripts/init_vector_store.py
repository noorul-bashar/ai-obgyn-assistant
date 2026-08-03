"""
One-time setup: creates the Pinecone index if it doesn't already exist.
Run this once per environment (or manage it via IaC/Terraform) — the app
itself assumes the index is already there and only connects to it.

Usage:
    python scripts/init_vector_store.py

Note: the Pinecone Python SDK went through a v9 rewrite that introduced a
namespaced `pc.indexes.*` API for index management (create/list/delete),
separate from `pc.index(name)` used to connect to an index for
upsert/query. If this script errors on your installed version, check
https://sdk.pinecone.io/python/ for the current index-management calls —
the client-connection code the rest of the app relies on
(app/services/rag/vector_store.py) is unaffected either way.
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from pinecone import Pinecone, ServerlessSpec  # noqa: E402

from app.config import get_settings  # noqa: E402


def main() -> None:
    settings = get_settings()
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)

    existing_names = {idx.name for idx in pc.indexes.list()}
    if settings.PINECONE_INDEX_NAME in existing_names:
        print(f"Index '{settings.PINECONE_INDEX_NAME}' already exists — nothing to do.")
        return

    pc.indexes.create(
        name=settings.PINECONE_INDEX_NAME,
        dimension=settings.VECTOR_DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(cloud=settings.PINECONE_CLOUD, region=settings.PINECONE_REGION),
    )
    print(f"Created index '{settings.PINECONE_INDEX_NAME}'.")


if __name__ == "__main__":
    main()
