from app.core.tracing import ToolCallTrace
from app.schemas.documents import DocumentUploadResponse
from app.schemas.query import QueryResponse
from chainlit_app.formatting import (
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


def test_format_upload_response_summarizes_indexing() -> None:
    response = DocumentUploadResponse(
        document_id="doc_123",
        filename="contrato.pdf",
        chunks_indexed=3,
    )

    assert format_upload_response(response) == "Documento indexado: `contrato.pdf` (3 chunks)."


def test_format_error_returns_controlled_message() -> None:
    assert format_error("Backend caido") == "No se pudo completar la operacion: Backend caido"
