from datetime import UTC, datetime
from uuid import uuid4

from app.rag.embeddings import DeterministicEmbeddingModel, EmbeddingModel
from app.rag.loader import PDFExtractionError, PDFLoader
from app.rag.splitter import RecursiveTextSplitter
from app.rag.vector_store import DocumentVectorStore
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
    ) -> None:
        self._vector_store = vector_store
        self._loader = loader or PDFLoader()
        self._splitter = splitter or RecursiveTextSplitter()
        self._embedding_model = embedding_model or DeterministicEmbeddingModel()

    @property
    def vector_store(self) -> DocumentVectorStore:
        return self._vector_store

    @property
    def embedding_model(self) -> EmbeddingModel:
        return self._embedding_model

    def ingest_pdf(self, content: bytes, filename: str) -> DocumentUploadResponse:
        if not filename.lower().endswith(".pdf"):
            raise InvalidDocumentError("Solo se permiten archivos PDF.")

        try:
            pages = self._loader.load(content)
        except PDFExtractionError as exc:
            raise InvalidDocumentError(str(exc)) from exc

        if not pages:
            raise EmptyDocumentError("El PDF no contiene texto extraible.")

        document_id = f"doc_{uuid4().hex[:12]}"
        uploaded_at = datetime.now(UTC)
        chunks = self._splitter.split_pages(
            pages=pages,
            document_id=document_id,
            filename=filename,
            uploaded_at=uploaded_at,
        )
        if not chunks:
            raise EmptyDocumentError("El PDF no genero chunks utiles.")

        embeddings = self._embedding_model.embed_documents([chunk.text for chunk in chunks])
        self._vector_store.add_chunks(chunks=chunks, embeddings=embeddings)

        return DocumentUploadResponse(
            document_id=document_id,
            filename=filename,
            chunks_indexed=len(chunks),
        )

    def list_documents(self) -> DocumentListResponse:
        return DocumentListResponse(documents=self._vector_store.list_documents())
