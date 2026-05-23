from datetime import datetime

from app.rag.loader import DocumentPage
from app.schemas.documents import DocumentChunk, DocumentChunkMetadata


class RecursiveTextSplitter:
    def __init__(self, chunk_size: int = 900, chunk_overlap: int = 120) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap debe ser menor que chunk_size")
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def split_pages(
        self,
        pages: list[DocumentPage],
        document_id: str,
        document_hash: str,
        filename: str,
        uploaded_at: datetime,
        indexed_at: datetime,
    ) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        for page in pages:
            for page_chunk_index, text in enumerate(self._split_text(page.text), start=1):
                chunk_id = f"{document_id}_p{page.page}_c{page_chunk_index}"
                chunks.append(
                    DocumentChunk(
                        text=text,
                        metadata=DocumentChunkMetadata(
                            document_id=document_id,
                            document_hash=document_hash,
                            filename=filename,
                            page=page.page,
                            chunk_id=chunk_id,
                            uploaded_at=uploaded_at,
                            indexed_at=indexed_at,
                        ),
                    )
                )
        return chunks

    def _split_text(self, text: str) -> list[str]:
        normalized = " ".join(text.split())
        if not normalized:
            return []

        if len(normalized) <= self._chunk_size:
            return [normalized]

        chunks: list[str] = []
        start = 0
        while start < len(normalized):
            end = min(start + self._chunk_size, len(normalized))
            if end < len(normalized):
                boundary = normalized.rfind(" ", start, end)
                if boundary > start:
                    end = boundary

            chunk = normalized[start:end].strip()
            if chunk:
                chunks.append(chunk)

            if end >= len(normalized):
                break

            start = max(end - self._chunk_overlap, 0)

        return chunks
