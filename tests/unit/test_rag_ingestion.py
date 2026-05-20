import pytest

from app.rag.ingestion import DocumentIngestionService
from app.rag.vector_store import InMemoryDocumentVectorStore, VectorStoreError


class _FailingEmbeddingModel:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("embedding provider unavailable")

    def embed_query(self, text: str) -> list[float]:
        raise RuntimeError("embedding provider unavailable")


def test_document_ingestion_indexes_pdf_chunks_with_required_metadata() -> None:
    vector_store = InMemoryDocumentVectorStore()
    service = DocumentIngestionService(vector_store=vector_store)

    response = service.ingest_pdf(
        content=_pdf_bytes("Contrato marco con penalizacion por retrasos en entrega."),
        filename="contrato.pdf",
    )

    documents = service.list_documents().documents

    assert response.status == "indexed"
    assert response.filename == "contrato.pdf"
    assert response.chunks_indexed == 1
    assert any("FALLBACK_VECTOR_STORE_IN_MEMORY" in fallback for fallback in response.fallbacks)
    assert any("FALLBACK_EMBEDDINGS_DETERMINISTIC" in fallback for fallback in response.fallbacks)
    assert documents[0].document_id == response.document_id
    assert documents[0].chunks_indexed == 1


def test_document_ingestion_returns_controlled_error_when_embedding_fails() -> None:
    service = DocumentIngestionService(
        vector_store=InMemoryDocumentVectorStore(),
        embedding_model=_FailingEmbeddingModel(),
    )

    with pytest.raises(VectorStoreError) as exc_info:
        service.ingest_pdf(
            content=_pdf_bytes("Contrato marco con penalizacion por retrasos."),
            filename="contrato.pdf",
        )

    assert "embeddings" in str(exc_info.value)


def _pdf_bytes(text: str) -> bytes:
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        b"5 0 obj << /Length "
        + str(len(stream)).encode()
        + b" >> stream\n"
        + stream
        + b"\nendstream endobj\n",
    ]
    body = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for pdf_object in objects:
        offsets.append(len(body))
        body.extend(pdf_object)
    xref = len(body)
    body.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    body.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        body.extend(f"{offset:010d} 00000 n \n".encode())
    body.extend(
        f"trailer << /Root 1 0 R /Size {len(objects) + 1} >>\n"
        f"startxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(body)
