import httpx
import pytest

from app.agents.graph import run_agent_graph
from app.erp.database import create_sqlite_connection, load_seed_sql
from app.erp.repositories import NorthwindRepository
from app.production.client import ProductionAPIClient
from app.rag.embeddings import DeterministicEmbeddingModel
from app.rag.ingestion import DocumentIngestionService
from app.rag.vector_store import InMemoryDocumentVectorStore
from app.tools.erp_tool import ERPTool
from app.tools.production_tool import ProductionAPITool
from app.tools.rag_tool import DocumentRAGTool


@pytest.fixture()
def erp_tool() -> ERPTool:
    connection = create_sqlite_connection()
    load_seed_sql(connection)
    return ERPTool(NorthwindRepository(connection))


@pytest.fixture()
def production_tool() -> ProductionAPITool:
    client = ProductionAPIClient(
        base_url="http://production-api.test",
        transport=_production_transport(),
    )
    return ProductionAPITool(client)


def test_agent_graph_answers_pending_orders_with_production_status(
    erp_tool: ERPTool,
    production_tool: ProductionAPITool,
) -> None:
    response = run_agent_graph(
        erp_tool=erp_tool,
        production_tool=production_tool,
        question="Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?",
    )

    assert response.status == "completed"
    assert response.sources == ["ERP", "Produccion"]
    assert "10248" in response.answer
    assert "10252" in response.answer
    assert "Falta de material" in response.answer
    assert [call.tool for call in response.tool_calls] == [
        "ERPTool",
        "ProductionAPITool",
        "ProductionAPITool",
    ]


def test_agent_graph_answers_blocked_orders_with_erp_customer_context(
    erp_tool: ERPTool,
    production_tool: ProductionAPITool,
) -> None:
    response = run_agent_graph(
        erp_tool=erp_tool,
        production_tool=production_tool,
        question="Que pedidos estan bloqueados y cual es el motivo?",
    )

    assert response.status == "completed"
    assert response.sources == ["Produccion", "ERP"]
    assert "10252" in response.answer
    assert "10312" in response.answer
    assert "Alfreds Futterkiste" in response.answer
    assert "Falta de capacidad" in response.answer


def test_agent_graph_returns_insufficient_context_when_rag_tool_is_not_configured(
    erp_tool: ERPTool,
    production_tool: ProductionAPITool,
) -> None:
    response = run_agent_graph(
        erp_tool=erp_tool,
        production_tool=production_tool,
        question="Resume el PDF del contrato marco",
    )

    assert response.status == "insufficient_context"
    assert response.sources == []
    assert response.tool_calls[0].status == "skipped"
    assert "contexto documental suficiente" in response.answer


def test_agent_graph_answers_rag_query_when_document_tool_is_configured(
    erp_tool: ERPTool,
    production_tool: ProductionAPITool,
) -> None:
    vector_store = InMemoryDocumentVectorStore()
    service = DocumentIngestionService(vector_store=vector_store)
    service.ingest_pdf(
        content=_pdf_bytes("Contrato marco con penalizacion por retrasos en entrega."),
        filename="contrato.pdf",
    )

    response = run_agent_graph(
        erp_tool=erp_tool,
        production_tool=production_tool,
        rag_tool=DocumentRAGTool(
            vector_store=vector_store,
            embedding_model=DeterministicEmbeddingModel(),
        ),
        question="Que dice el PDF del contrato sobre penalizacion por retrasos?",
    )

    assert response.status == "completed"
    assert response.sources == ["Documentos"]
    assert "penalizacion" in response.answer
    assert response.tool_calls[0].tool == "DocumentRAGTool"


def _production_transport() -> httpx.MockTransport:
    orders = {
        10248: {
            "order_id": 10248,
            "production_status": "in_progress",
            "blocked_reason": None,
            "delay_reason": None,
            "estimated_finish_date": "2026-05-22",
        },
        10252: {
            "order_id": 10252,
            "production_status": "blocked",
            "blocked_reason": "Falta de material",
            "delay_reason": None,
            "estimated_finish_date": "2026-05-30",
        },
        10255: {
            "order_id": 10255,
            "production_status": "finished",
            "blocked_reason": None,
            "delay_reason": None,
            "estimated_finish_date": "2026-05-14",
        },
        10301: {
            "order_id": 10301,
            "production_status": "delayed",
            "blocked_reason": None,
            "delay_reason": "Averia en linea de produccion",
            "estimated_finish_date": "2026-06-03",
        },
        10312: {
            "order_id": 10312,
            "production_status": "blocked",
            "blocked_reason": "Falta de capacidad",
            "delay_reason": None,
            "estimated_finish_date": "2026-06-02",
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/production/orders":
            status = request.url.params.get("status")
            filtered_orders = list(orders.values())
            if status:
                filtered_orders = [
                    order
                    for order in filtered_orders
                    if order["production_status"] == status
                ]
            return httpx.Response(200, json={"orders": filtered_orders})

        if request.url.path.startswith("/production/orders/"):
            order_id = int(request.url.path.rsplit("/", 1)[1])
            order = orders.get(order_id)
            if order is None:
                return httpx.Response(
                    404,
                    json={"detail": "Production order not found"},
                )
            return httpx.Response(200, json=order)

        return httpx.Response(500, text="unexpected path")

    return httpx.MockTransport(handler)


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
