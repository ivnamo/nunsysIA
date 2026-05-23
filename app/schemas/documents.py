from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


DocumentStatus = Literal["indexed"]
RAGStatus = Literal["completed", "insufficient_context"]


class DocumentChunkMetadata(BaseModel):
    document_id: str
    document_hash: str
    filename: str
    page: int = Field(ge=1)
    chunk_id: str
    uploaded_at: datetime
    indexed_at: datetime


class DocumentChunk(BaseModel):
    text: str = Field(min_length=1)
    metadata: DocumentChunkMetadata


class RetrievedDocumentChunk(BaseModel):
    text: str
    metadata: DocumentChunkMetadata
    score: float = Field(ge=0)


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: DocumentStatus = "indexed"
    chunks_indexed: int
    fallbacks: list[str] = Field(default_factory=list)


class IndexedDocument(BaseModel):
    document_id: str
    filename: str
    uploaded_at: datetime
    chunks_indexed: int


class DocumentListResponse(BaseModel):
    documents: list[IndexedDocument]
    fallbacks: list[str] = Field(default_factory=list)


class DocumentRAGAnswer(BaseModel):
    answer: str
    status: RAGStatus
    chunks: list[RetrievedDocumentChunk] = Field(default_factory=list)
    fallbacks: list[str] = Field(default_factory=list)
