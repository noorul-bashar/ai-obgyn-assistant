"""
Centralized application configuration.

All secrets and environment-specific values are loaded from environment
variables (via a .env file in local dev). Never hardcode credentials.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    APP_NAME: str = "AI OB-GYN Clinical Assistant"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    API_KEY: str = "change-me"  # simple shared-secret auth for internal/front-end calls

    # --- Relational DB (patient records / consultation history) ---
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/obgyn_assistant"

    # --- Vector DB (Pinecone) ---
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "obgyne"
    PINECONE_CLOUD: str = "aws"
    PINECONE_REGION: str = "us-east-1"
    VECTOR_DIMENSION: int = 1024  # voyage-4-large default output dimension

    # --- Embeddings ---
    EMBEDDING_MODEL: str = "openai/clip-vit-base-patch32"

    # --- LLM ---
    GROQ_API_KEY: str = ""
    LLM_MODEL: str = "openai/gpt-oss-120b"
    LLM_MAX_TOKENS: int = 1500

    # --- Ingestion ---
    PARENT_CHUNK_SIZE: int = 1024
    PARENT_CHUNK_OVERLAP: int = 128
    CHILD_CHUNK_SIZE: int = 256
    CHILD_CHUNK_OVERLAP: int = 32
    CHILD_RETRIEVAL_MULTIPLIER: int = 4

    # --- RAG ---
    RETRIEVAL_TOP_K: int = 10
    MIN_RELEVANCE_SCORE: float = 0.5  # tune against evaluation queries after re-indexing


@lru_cache
def get_settings() -> Settings:
    return Settings()
