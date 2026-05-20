import os
from functools import lru_cache

from dotenv import load_dotenv
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
    llm_provider: str = "deterministic"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.0
    llm_timeout_seconds: float = 8.0
    embedding_provider: str = "deterministic"
    gemini_embedding_model: str = "gemini-embedding-001"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_model: str = "deterministic"


@lru_cache
def get_settings() -> Settings:
    load_dotenv(override=False)
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
        llm_provider=os.getenv("LLM_PROVIDER", "deterministic").lower(),
        gemini_api_key=_empty_to_none(os.getenv("GEMINI_API_KEY")),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        openai_api_key=_empty_to_none(os.getenv("OPENAI_API_KEY")),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "8")),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "deterministic").lower(),
        gemini_embedding_model=os.getenv(
            "GEMINI_EMBEDDING_MODEL",
            "gemini-embedding-001",
        ),
        openai_embedding_model=os.getenv(
            "OPENAI_EMBEDDING_MODEL",
            "text-embedding-3-small",
        ),
        embedding_model=os.getenv("EMBEDDING_MODEL", "deterministic"),
    )


def _empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
