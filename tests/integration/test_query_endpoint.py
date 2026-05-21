import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agents.service import QueryWorkflowService
from app.api.routes_documents import get_document_service
from app.api.routes_query import get_query_service
from app.erp.database import create_sqlite_connection, load_seed_sql
from app.erp.repositories import NorthwindRepository
from app.main import create_app
from app.production.client import ProductionAPIClient
from app.rag.embeddings import DeterministicEmbeddingModel
from app.rag.ingestion import DocumentIngestionService
from app.rag.vector_store import InMemoryDocumentVectorStore
from app.schemas.query import QueryRequest
from app.tools.erp_tool import ERPTool
from app.tools.production_tool import ProductionAPITool
from app.tools.rag_tool import DocumentRAGTool


@pytest.fixture()
def client() -> TestClient:
    app = create_app()
    vector_store = InMemoryDocumentVectorStore()
    document_service = DocumentIngestionService(vector_store=vector_store)
    query_service = QueryWorkflowService(
        erp_tool=_erp_tool(),
        production_tool=_production_tool(),
        rag_tool=DocumentRAGTool(
            vector_store=vector_store,
            embedding_model=DeterministicEmbeddingModel(),
        ),
    )

    app.dependency_overrides[get_document_service] = lambda: document_service
    app.dependency_overrides[get_query_service] = lambda: query_service
    return TestClient(app)


def test_query_endpoint_answers_erp_production_question(client: TestClient) -> None:
    request_payload = json.loads(
        (Path(__file__).resolve().parents[2] / "query.json").read_text(
            encoding="utf-8"
        )
    )

    response = client.post(
        "/api/query",
        json=request_payload,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["sources"] == ["ERP", "Produccion"]
    assert "10248" in payload["answer"]
    assert "10252" in payload["answer"]
    assert [call["tool"] for call in payload["tool_calls"]] == [
        "ERPTool",
        "ProductionAPITool",
        "ProductionAPITool",
    ]
    assert [call["action"] for call in payload["tool_calls"]] == [
        "get_pending_orders_by_customer",
        "get_status_for_erp_orders",
        "get_status_for_erp_orders",
    ]
    assert payload["data"] == {
        "erp_orders_count": 2,
        "erp_order_ids": [10248, 10252],
        "production_statuses_count": 2,
    }
    assert "amount" not in str(payload["data"])
    assert all("error" in call for call in payload["tool_calls"])


def test_query_endpoint_does_not_assume_customer_for_pending_orders(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/query",
        json={"question": "Que pedidos pendientes hay?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "needs_clarification"
    assert payload["sources"] == []
    assert payload["tool_calls"] == []
    assert "cliente concreto" in payload["answer"]
    assert "ALFKI" not in payload["answer"]


def test_query_endpoint_keeps_conversation_memory_by_id(client: TestClient) -> None:
    first_response = client.post(
        "/api/query",
        json={
            "question": "Que pedidos pendientes tiene el cliente ALFKI?",
            "conversation_id": "memory-api-001",
        },
    )
    assert first_response.status_code == 200

    second_response = client.post(
        "/api/query",
        json={
            "question": "Y en que estado estan?",
            "conversation_id": "memory-api-001",
        },
    )

    assert second_response.status_code == 200
    payload = second_response.json()
    assert payload["status"] == "completed"
    assert payload["sources"] == ["Memoria", "ERP", "Produccion"]
    assert "10248" in payload["answer"]
    assert "10252" in payload["answer"]
    assert [call["tool"] for call in payload["tool_calls"]] == [
        "MemoryTool",
        "ERPTool",
        "ProductionAPITool",
        "ProductionAPITool",
    ]
    assert [call["action"] for call in payload["tool_calls"]] == [
        "recall",
        "get_pending_orders_by_customer",
        "get_status_for_erp_orders",
        "get_status_for_erp_orders",
    ]
    assert payload["data"]["memory"]["customer_id"] == "ALFKI"

    isolated_response = client.post(
        "/api/query",
        json={
            "question": "Y en que estado estan?",
            "conversation_id": "memory-api-002",
        },
    )
    assert isolated_response.status_code == 200
    isolated_payload = isolated_response.json()
    assert isolated_payload["status"] == "needs_clarification"
    assert "contexto conversacional previo" in isolated_payload["answer"]


def test_query_endpoint_resolves_blocked_and_economic_memory_follow_ups(
    client: TestClient,
) -> None:
    first_response = client.post(
        "/api/query",
        json={
            "question": "Que pedidos pendientes tiene el cliente ALFKI?",
            "conversation_id": "memory-api-impact-001",
        },
    )
    assert first_response.status_code == 200

    blocked_response = client.post(
        "/api/query",
        json={
            "question": "Y cuales de esos pedidos estan bloqueados?",
            "conversation_id": "memory-api-impact-001",
        },
    )

    assert blocked_response.status_code == 200
    blocked_payload = blocked_response.json()
    assert blocked_payload["status"] == "completed"
    assert blocked_payload["sources"] == ["Memoria", "Produccion", "ERP"]
    assert "10252" in blocked_payload["answer"]
    assert "Falta de material" in blocked_payload["answer"]
    assert "10248" not in blocked_payload["answer"]
    assert blocked_payload["data"]["production_order_ids"] == [10252]

    impact_response = client.post(
        "/api/query",
        json={
            "question": "Cual es el impacto economico de esos?",
            "conversation_id": "memory-api-impact-001",
        },
    )

    assert impact_response.status_code == 200
    impact_payload = impact_response.json()
    assert impact_payload["status"] == "completed"
    assert impact_payload["sources"] == ["Memoria", "ERP"]
    assert "10252" in impact_payload["answer"]
    assert "1863.00" in impact_payload["answer"]
    assert impact_payload["data"]["order_amount_order_ids"] == [10252]
    assert impact_payload["data"]["economic_impact_total"] == "1863.00"
    assert "product_id" not in str(impact_payload["data"])


def test_query_endpoint_answers_document_question_after_upload(
    client: TestClient,
) -> None:
    upload_response = client.post(
        "/api/documents/upload",
        files={
            "file": (
                "contrato.pdf",
                _pdf_bytes("Contrato marco con penalizacion por retrasos en entrega."),
                "application/pdf",
            )
        },
    )

    assert upload_response.status_code == 201

    response = client.post(
        "/api/query",
        json={"question": "Que dice el PDF del contrato sobre penalizacion?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["sources"] == ["Documentos"]
    assert "penalizacion" in payload["answer"]
    assert payload["tool_calls"][0]["tool"] == "DocumentRAGTool"
    assert payload["tool_calls"][0]["action"] == "query"
    assert payload["data"]["rag"]["status"] == "completed"
    assert payload["data"]["rag"]["chunks_count"] >= 1
    assert payload["data"]["rag"]["documents"] == ["contrato.pdf"]
    citation = payload["data"]["rag"]["citations"][0]
    assert citation["filename"] == "contrato.pdf"
    assert citation["page"] == 1
    assert citation["chunk_id"].endswith("_p1_c1")
    assert isinstance(citation["score"], float)
    assert "Contrato marco" not in str(payload["data"])


def test_query_endpoint_rejects_blank_question(client: TestClient) -> None:
    response = client.post("/api/query", json={"question": "   "})

    assert response.status_code == 422


def test_query_endpoint_returns_controlled_500_when_service_fails() -> None:
    app = create_app()
    app.dependency_overrides[get_query_service] = lambda: _FailingQueryService()
    client = TestClient(app)

    response = client.post("/api/query", json={"question": "Que pedidos hay?"})

    assert response.status_code == 500
    assert response.json() == {
        "detail": "No se pudo procesar la consulta de forma controlada."
    }


class _FailingQueryService:
    def run(self, request: QueryRequest) -> None:
        raise RuntimeError("boom")


def _erp_tool() -> ERPTool:
    connection = create_sqlite_connection(check_same_thread=False)
    load_seed_sql(connection)
    return ERPTool(NorthwindRepository(connection))


def _production_tool() -> ProductionAPITool:
    client = ProductionAPIClient(
        base_url="http://production-api.test",
        transport=_production_transport(),
    )
    return ProductionAPITool(client)


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
    }

    def handler(request: httpx.Request) -> httpx.Response:
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
