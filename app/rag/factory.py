from app.core.config import Settings
from app.core.llm import LLMProviderError, create_embedding_model
from app.rag.embeddings import DeterministicEmbeddingModel
from app.rag.ingestion import DocumentIngestionService
from app.rag.splitter import RecursiveTextSplitter
from app.rag.vector_store import (
    ChromaDocumentVectorStore,
)


def create_document_service(settings: Settings) -> DocumentIngestionService:
    embedding_model = create_embedding_model(settings)
    if isinstance(embedding_model, DeterministicEmbeddingModel):
        raise LLMProviderError(
            "El runtime documental requiere embeddings reales. "
            "Configura EMBEDDING_PROVIDER=gemini/openai y la clave correspondiente."
        )

    vector_store = ChromaDocumentVectorStore(
        mode=settings.chroma_mode,
        host=settings.chroma_host,
        port=settings.chroma_port,
        collection_name=_embedding_scoped_collection_name(
            settings.chroma_collection,
            embedding_model,
        ),
        persist_directory=settings.chroma_persist_directory,
    )

    return DocumentIngestionService(
        vector_store=vector_store,
        splitter=RecursiveTextSplitter(
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
        ),
        embedding_model=embedding_model,
    )


def _embedding_scoped_collection_name(
    base_name: str,
    embedding_model: object,
) -> str:
    if isinstance(embedding_model, DeterministicEmbeddingModel):
        suffix = f"deterministic_{embedding_model.dimensions}"
    else:
        suffix = (
            str(getattr(embedding_model, "model", ""))
            or str(getattr(embedding_model, "model_name", ""))
            or embedding_model.__class__.__name__
        )
    return _safe_chroma_collection_name(f"{base_name}_{suffix}")


def _safe_chroma_collection_name(value: str) -> str:
    safe = "".join(
        character.lower() if character.isalnum() else "_"
        for character in value.strip()
    )
    safe = "_".join(part for part in safe.split("_") if part)
    if len(safe) < 3:
        safe = f"{safe}_rag"
    return safe[:512].strip("_") or "documents_rag"
