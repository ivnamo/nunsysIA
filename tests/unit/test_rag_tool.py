from app.rag.embeddings import DeterministicEmbeddingModel
from app.rag.ingestion import DocumentIngestionService
from app.rag.vector_store import InMemoryDocumentVectorStore
from app.tools.rag_tool import DocumentRAGInput, DocumentRAGTool


class _FailingEmbeddingModel:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("embedding provider unavailable")

    def embed_query(self, text: str) -> list[float]:
        raise RuntimeError("embedding provider unavailable")


def test_document_rag_tool_returns_grounded_answer_and_trace() -> None:
    vector_store = InMemoryDocumentVectorStore()
    service = DocumentIngestionService(vector_store=vector_store)
    service.ingest_pdf(
        content=_pdf_bytes("Contrato marco con penalizacion por retrasos en entrega."),
        filename="contrato.pdf",
    )
    tool = DocumentRAGTool(
        vector_store=vector_store,
        embedding_model=DeterministicEmbeddingModel(),
    )

    result = tool.query(
        DocumentRAGInput(query="penalizacion retrasos", top_k=2, min_score=0.2)
    )

    assert result.data["status"] == "completed"
    assert "penalizacion" in result.data["answer"]
    assert result.data["chunks"][0]["metadata"]["filename"] == "contrato.pdf"
    assert result.data["chunks"][0]["metadata"]["page"] == 1
    assert result.data["chunks"][0]["metadata"]["chunk_id"].endswith("_p1_c1")
    assert isinstance(result.data["chunks"][0]["score"], float)
    assert any(
        "FALLBACK_EMBEDDINGS_DETERMINISTIC" in fallback
        for fallback in result.data["fallbacks"]
    )
    assert result.tool_call.tool == "DocumentRAGTool"
    assert result.tool_call.source == "Documentos"
    assert result.tool_call.status == "success"
    assert "FALLBACK" in result.tool_call.output_summary


def test_document_rag_tool_returns_insufficient_context_without_relevant_chunks() -> None:
    vector_store = InMemoryDocumentVectorStore()
    service = DocumentIngestionService(vector_store=vector_store)
    service.ingest_pdf(
        content=_pdf_bytes("Manual de calidad de fabricacion interna."),
        filename="manual.pdf",
    )
    tool = DocumentRAGTool(vector_store=vector_store)

    result = tool.query(
        DocumentRAGInput(query="facturacion internacional", top_k=2, min_score=1.0)
    )

    assert result.data["status"] == "insufficient_context"
    assert result.data["chunks"] == []
    assert any("FALLBACK" in fallback for fallback in result.data["fallbacks"])
    assert result.tool_call.output_summary == "0 chunks relevantes recuperados"


def test_document_rag_tool_returns_tool_error_when_embedding_fails() -> None:
    tool = DocumentRAGTool(
        vector_store=InMemoryDocumentVectorStore(),
        embedding_model=_FailingEmbeddingModel(),
    )

    result = tool.query(DocumentRAGInput(query="penalizacion retrasos"))

    assert result.data is None
    assert result.tool_call.status == "error"
    assert result.tool_call.source == "Documentos"
    assert "embeddings" in result.tool_call.error


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
