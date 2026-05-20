import os
from functools import lru_cache

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "nunsysIA"
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://postgres:postgres@postgres:5432/northwind"
    production_api_base_url: str = "http://production-api:8001"
    production_api_timeout_seconds: float = 5.0
    chroma_host: str = "chromadb"
    chroma_port: int = 8000
    chroma_collection: str = "documents"
    rag_chunk_size: int = 900
    rag_chunk_overlap: int = 120
    rag_top_k: int = 3
    max_document_upload_bytes: int = 10 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "nunsysIA"),
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@postgres:5432/northwind",
        ),
        production_api_base_url=os.getenv(
            "PRODUCTION_API_BASE_URL",
            "http://production-api:8001",
        ),
        production_api_timeout_seconds=float(
            os.getenv("PRODUCTION_API_TIMEOUT_SECONDS", "5.0")
        ),
        chroma_host=os.getenv("CHROMA_HOST", "chromadb"),
        chroma_port=int(os.getenv("CHROMA_PORT", "8000")),
        chroma_collection=os.getenv("CHROMA_COLLECTION", "documents"),
        rag_chunk_size=int(os.getenv("RAG_CHUNK_SIZE", "900")),
        rag_chunk_overlap=int(os.getenv("RAG_CHUNK_OVERLAP", "120")),
        rag_top_k=int(os.getenv("RAG_TOP_K", "3")),
        max_document_upload_bytes=int(
            os.getenv("MAX_DOCUMENT_UPLOAD_BYTES", str(10 * 1024 * 1024))
        ),
    )
