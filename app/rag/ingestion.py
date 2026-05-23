import hashlib
from datetime import UTC, datetime
from pathlib import Path

from app.rag.embeddings import DeterministicEmbeddingModel, EmbeddingModel
from app.rag.loader import PDFExtractionError, PDFLoader
from app.rag.splitter import RecursiveTextSplitter
from app.rag.vector_store import (
    DocumentVectorStore,
    InMemoryDocumentVectorStore,
    VectorStoreError,
)
from app.schemas.documents import DocumentListResponse, DocumentUploadResponse


class InvalidDocumentError(ValueError):
    pass


class EmptyDocumentError(ValueError):
    pass


class DocumentIngestionService:
    def __init__(
        self,
        vector_store: DocumentVectorStore,
        loader: PDFLoader | None = None,
        splitter: RecursiveTextSplitter | None = None,
        embedding_model: EmbeddingModel | None = None,
        fallbacks: list[str] | None = None,
    ) -> None:
        self._vector_store = vector_store
        self._loader = loader or PDFLoader()
        self._splitter = splitter or RecursiveTextSplitter()
        self._embedding_model = embedding_model or DeterministicEmbeddingModel()
        self._fallbacks = list(fallbacks or [])
        if isinstance(self._vector_store, InMemoryDocumentVectorStore):
            self._add_fallback(
                "FALLBACK_VECTOR_STORE_IN_MEMORY: ChromaDB no disponible o no usado; documentos en memoria del proceso."
            )
        if isinstance(self._embedding_model, DeterministicEmbeddingModel):
            self._add_fallback(
                "FALLBACK_EMBEDDINGS_DETERMINISTIC: embeddings locales deterministas; no se esta usando proveedor externo."
            )

    @property
    def vector_store(self) -> DocumentVectorStore:
        return self._vector_store

    @property
    def embedding_model(self) -> EmbeddingModel:
        return self._embedding_model

    @property
    def fallbacks(self) -> list[str]:
        return list(self._fallbacks)

    def ingest_pdf(self, content: bytes, filename: str) -> DocumentUploadResponse:
        if not filename.lower().endswith(".pdf"):
            raise InvalidDocumentError("Solo se permiten archivos PDF.")

        try:
            pages = self._loader.load(content)
        except PDFExtractionError as exc:
            raise InvalidDocumentError(str(exc)) from exc

        if not pages:
            raise EmptyDocumentError("El PDF no contiene texto extraible.")

        document_hash = hashlib.sha256(content).hexdigest()
        document_id = f"doc_{document_hash[:12]}"
        uploaded_at = datetime.now(UTC)
        indexed_at = uploaded_at
        chunks = self._splitter.split_pages(
            pages=pages,
            document_id=document_id,
            document_hash=document_hash,
            filename=filename,
            uploaded_at=uploaded_at,
            indexed_at=indexed_at,
        )
        if not chunks:
            raise EmptyDocumentError("El PDF no genero chunks utiles.")

        try:
            embeddings = self._embedding_model.embed_documents([chunk.text for chunk in chunks])
            self._vector_store.delete_chunks(
                document_id=document_id,
                filename=filename,
                document_hash=document_hash,
            )
            self._vector_store.add_chunks(chunks=chunks, embeddings=embeddings)
        except VectorStoreError:
            raise
        except Exception as exc:
            raise VectorStoreError(
                "No se pudieron generar embeddings o indexar el documento."
            ) from exc

        return DocumentUploadResponse(
            document_id=document_id,
            filename=filename,
            chunks_indexed=len(chunks),
            fallbacks=self.fallbacks,
        )

    def list_documents(self) -> DocumentListResponse:
        return DocumentListResponse(
            documents=self._vector_store.list_documents(),
            fallbacks=self.fallbacks,
        )

    def clear_documents(self) -> int:
        return self._vector_store.clear()

    def ingest_pdf_path(self, path: Path) -> DocumentUploadResponse:
        return self.ingest_pdf(content=path.read_bytes(), filename=path.name)

    def _add_fallback(self, fallback: str) -> None:
        if fallback not in self._fallbacks:
            self._fallbacks.append(fallback)
