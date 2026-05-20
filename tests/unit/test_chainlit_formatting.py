from app.core.tracing import ToolCallTrace
from datetime import UTC, datetime

from app.schemas.documents import DocumentListResponse, DocumentUploadResponse, IndexedDocument
from app.schemas.query import QueryResponse
from chainlit_app.formatting import (
    format_document_list,
    format_error,
    format_query_response,
    format_upload_response,
)


def test_format_query_response_includes_traceability_sections() -> None:
    response = QueryResponse(
        answer="El cliente ALFKI tiene 2 pedidos pendientes.",
        sources=["ERP", "Produccion"],
        reasoning=["Consulta ERP", "Consulta produccion"],
        tool_calls=[
            ToolCallTrace(
                tool="ERPTool",
                args={"customer_id": "ALFKI"},
                status="success",
                output_summary="2 pedidos encontrados",
                source="ERP",
            )
        ],
        confidence=0.9,
        status="completed",
    )

    content = format_query_response(response)

    assert "El cliente ALFKI" in content
    assert "Estado: `completed`" in content
    assert "- ERP" in content
    assert "1. Consulta ERP" in content
    assert "`ERPTool` [success]: 2 pedidos encontrados" in content


def test_format_query_response_shows_fallbacks() -> None:
    response = QueryResponse(
        answer="Respuesta determinista.",
        status="completed",
        fallbacks=[
            "FALLBACK_PLANNER_RULE_BASED: LLM planner no configurado; plan creado por reglas."
        ],
    )

    content = format_query_response(response)

    assert "**FALLBACKS**" in content
    assert "FALLBACK_PLANNER_RULE_BASED" in content


def test_format_query_response_shows_document_citations() -> None:
    response = QueryResponse(
        answer="El contrato fija penalizaciones.",
        sources=["Documentos"],
        status="completed",
        data={
            "rag": {
                "status": "completed",
                "chunks_count": 1,
                "documents": ["contrato.pdf"],
                "citations": [
                    {
                        "filename": "contrato.pdf",
                        "page": 1,
                        "chunk_id": "doc_123_p1_c1",
                        "score": 0.91234,
                    }
                ],
            }
        },
    )

    content = format_query_response(response)

    assert "**Citas documentales**" in content
    assert "`contrato.pdf`, pagina `1`, chunk `doc_123_p1_c1`, score `0.9123`" in content


def test_format_upload_response_summarizes_indexing() -> None:
    response = DocumentUploadResponse(
        document_id="doc_123",
        filename="contrato.pdf",
        chunks_indexed=3,
    )

    assert format_upload_response(response) == "Documento indexado: `contrato.pdf` (3 chunks)."


def test_format_upload_response_shows_fallbacks() -> None:
    response = DocumentUploadResponse(
        document_id="doc_123",
        filename="contrato.pdf",
        chunks_indexed=3,
        fallbacks=["FALLBACK_VECTOR_STORE_IN_MEMORY: ChromaDB no usado."],
    )

    content = format_upload_response(response)

    assert "Documento indexado: `contrato.pdf` (3 chunks)." in content
    assert "FALLBACK_VECTOR_STORE_IN_MEMORY" in content


def test_format_document_list_summarizes_document_space() -> None:
    response = DocumentListResponse(
        documents=[
            IndexedDocument(
                document_id="doc_123",
                filename="contrato.pdf",
                uploaded_at=datetime(2026, 5, 20, tzinfo=UTC),
                chunks_indexed=3,
            )
        ]
    )

    content = format_document_list(response)

    assert "**Espacio documental**" in content
    assert "`contrato.pdf` (3 chunks)" in content


def test_format_document_list_handles_empty_space() -> None:
    assert format_document_list(DocumentListResponse(documents=[])) == "Espacio documental vacio."


def test_format_error_returns_controlled_message() -> None:
    assert format_error("Backend caido") == "No se pudo completar la operacion: Backend caido"
