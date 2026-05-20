from app.core.config import Settings
from app.core.llm import LLMProviderError, create_embedding_model
from app.rag.embeddings import DeterministicEmbeddingModel
from app.rag.ingestion import DocumentIngestionService
from app.rag.splitter import RecursiveTextSplitter
from app.rag.vector_store import (
    ChromaDocumentVectorStore,
    InMemoryDocumentVectorStore,
    VectorStoreError,
)


def create_document_service(settings: Settings) -> DocumentIngestionService:
    try:
        vector_store = ChromaDocumentVectorStore(
            host=settings.chroma_host,
            port=settings.chroma_port,
            collection_name=settings.chroma_collection,
        )
    except VectorStoreError:
        vector_store = InMemoryDocumentVectorStore()

    try:
        embedding_model = create_embedding_model(settings)
    except LLMProviderError:
        embedding_model = DeterministicEmbeddingModel()

    return DocumentIngestionService(
        vector_store=vector_store,
        splitter=RecursiveTextSplitter(
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
        ),
        embedding_model=embedding_model,
    )
