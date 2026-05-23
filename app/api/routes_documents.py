from functools import lru_cache

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)

from app.api.upload_parser import (
    UploadParseError,
    UploadTooLargeError,
    read_pdf_upload,
)
from app.core.config import get_settings
from app.core.llm import LLMProviderError
from app.rag.factory import create_document_service
from app.rag.ingestion import (
    DocumentIngestionService,
    EmptyDocumentError,
    InvalidDocumentError,
)
from app.rag.vector_store import VectorStoreError
from app.schemas.documents import DocumentListResponse, DocumentUploadResponse


router = APIRouter(prefix="/api/documents", tags=["documents"])


@lru_cache
def get_document_service() -> DocumentIngestionService:
    try:
        return create_document_service(get_settings())
    except (LLMProviderError, VectorStoreError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    request: Request,
    file: UploadFile | None = File(default=None),
    service: DocumentIngestionService = Depends(get_document_service),
) -> DocumentUploadResponse:
    settings = get_settings()
    try:
        uploaded = await read_pdf_upload(
            request=request,
            max_bytes=settings.max_document_upload_bytes,
            file=file,
        )
        return service.ingest_pdf(content=uploaded.content, filename=uploaded.filename)
    except UploadTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except (UploadParseError, InvalidDocumentError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except EmptyDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except VectorStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("", response_model=DocumentListResponse)
def list_documents(
    service: DocumentIngestionService = Depends(get_document_service),
) -> DocumentListResponse:
    try:
        return service.list_documents()
    except VectorStoreError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
