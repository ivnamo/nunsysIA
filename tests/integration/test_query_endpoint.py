import httpx
import pytest
from fastapi.testclient import TestClient

from app.agents.deep_agent import DeepAgentService
from app.agents.deepagents_tools_service import DeepAgentsToolsQueryService
from app.agents.router import AgentRouter
from app.api.routes_documents import get_document_service
from app.api.routes_query import get_agent_router
from app.core.config import get_settings
from app.erp.database import create_sqlite_connection, load_seed_sql
from app.erp.repositories import NorthwindRepository
from app.main import create_app
from app.production.client import ProductionAPIClient
from app.rag.embeddings import DeterministicEmbeddingModel
from app.rag.ingestion import DocumentIngestionService
from app.rag.vector_store import InMemoryDocumentVectorStore
from app.schemas.query import QueryResponse
from app.services.response_normalizer import ResponseNormalizer
from app.tools.erp_query_tool import ERPQueryTool
from app.tools.erp_tool import ERPTool
from app.tools.production_query_tool import ProductionQueryTool
from app.tools.production_tool import ProductionAPITool
from app.tools.rag_tool import DocumentRAGTool


@pytest.fixture()
def client() -> TestClient:
    app = create_app()
    vector_store = InMemoryDocumentVectorStore()
    document_service = DocumentIngestionService(
        vector_store=vector_store,
        embedding_model=DeterministicEmbeddingModel(),
    )
    agent_router = _agent_router(document_service)

    app.dependency_overrides[get_document_service] = lambda: document_service
    app.dependency_overrides[get_agent_router] = lambda: agent_router
    return TestClient(app)


def test_query_endpoint_without_mode_uses_deepagent(client: TestClient) -> None:
    response = client.post(
        "/api/query",
        json={
            "question": (
                "Que pedidos pendientes tiene ALFKI y en que estado de produccion estan?"
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["agent_mode"] == "deepagent"
    assert payload["metadata"]["agent_framework"] == "LangChain DeepAgents"
    assert payload["sources"] == ["ERP", "Produccion"]
    assert "10248" in payload["answer"]
    assert "10252" in payload["answer"]


def test_query_endpoint_with_deepagent_mode_works(client: TestClient) -> None:
    response = client.post(
        "/api/query",
        json={
            "question": (
                "Que pedidos pendientes tiene ALFKI y en que estado de produccion estan?"
            ),
            "mode": "deepagent",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["agent_mode"] == "deepagent"
    assert payload["status"] == "completed"


def test_query_endpoint_legacy_mode_works_when_available(client: TestClient) -> None:
    response = client.post(
        "/api/query",
        json={"question": "Comparativa legacy", "mode": "legacy_langgraph"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Respuesta legacy"
    assert payload["metadata"]["agent_mode"] == "legacy_langgraph"
    assert payload["metadata"]["experimental"] is True


def test_query_endpoint_sidecar_mode_works_when_available(client: TestClient) -> None:
    response = client.post(
        "/api/query",
        json={"question": "Comparativa sidecar", "mode": "deepagent_sidecar"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Respuesta sidecar"
    assert payload["metadata"]["agent_mode"] == "deepagent_sidecar"
    assert payload["metadata"]["experimental"] is True


def test_query_endpoint_erp_production_question_uses_both_sources(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/query",
        json={
            "question": (
                "Que pedidos pendientes tiene ALFKI y en que estado de produccion estan?"
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sources"] == ["ERP", "Produccion"]
    assert [call["tool"] for call in payload["tool_calls"]] == [
        "ERPTool",
        "ProductionAPITool",
    ]
    assert payload["data"]["erp_order_ids"] == [10248, 10252]
    assert payload["data"]["production_order_ids"] == [10248, 10252]


def test_query_endpoint_document_question_uses_rag(client: TestClient) -> None:
    upload_response = client.post(
        "/api/documents/upload",
        files={
            "file": (
                "plazos.pdf",
                _pdf_bytes("El documento fija plazos de entrega de 5 dias laborables."),
                "application/pdf",
            )
        },
    )
    assert upload_response.status_code == 201

    response = client.post(
        "/api/query",
        json={"question": "Que dice este documento sobre plazos de entrega?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sources"] == ["Documentos"]
    assert payload["tool_calls"][0]["tool"] == "DocumentRAGTool"
    assert payload["data"]["rag"]["documents"] == ["plazos.pdf"]
    assert "5 dias laborables" in payload["answer"]


def test_query_endpoint_rejects_blank_question(client: TestClient) -> None:
    response = client.post("/api/query", json={"question": "   "})

    assert response.status_code == 422


def test_query_endpoint_returns_controlled_500_when_router_fails() -> None:
    app = create_app()
    app.dependency_overrides[get_agent_router] = lambda: _FailingRouter()
    client = TestClient(app)

    response = client.post("/api/query", json={"question": "Que pedidos hay?"})

    assert response.status_code == 500
    assert response.json() == {
        "detail": "No se pudo procesar la consulta de forma controlada."
    }


def _agent_router(document_service: DocumentIngestionService) -> AgentRouter:
    erp_tool = _erp_tool()
    production_tool = _production_tool()
    deepagent = DeepAgentService(
        DeepAgentsToolsQueryService(
            erp_tool=erp_tool,
            production_tool=production_tool,
            erp_query_tool=_erp_query_tool(),
            production_query_tool=_production_query_tool(),
            rag_tool=DocumentRAGTool(
                vector_store=document_service.vector_store,
                embedding_model=document_service.embedding_model,
            ),
            model=get_settings().deepagents_model,
            agent_builder=lambda **kwargs: _StaticAgent("Respuesta no determinista."),
        )
    )
    return AgentRouter(
        deepagent_service=deepagent,
        sidecar_service=_ModeService("Respuesta sidecar"),
        legacy_service=_ModeService("Respuesta legacy"),
        response_normalizer=ResponseNormalizer(),
    )


class _StaticAgent:
    def __init__(self, content: str) -> None:
        self._content = content

    def invoke(self, payload: dict) -> dict:
        return {"messages": [{"content": self._content}]}


class _ModeService:
    def __init__(self, answer: str) -> None:
        self._answer = answer

    async def query(
        self,
        question: str,
        conversation_id: str | None = None,
        include_citation_previews: bool = False,
    ) -> QueryResponse:
        return QueryResponse(
            answer=self._answer,
            sources=["ERP"],
            reasoning=["Modo experimental solicitado"],
            status="completed",
        )


class _FailingRouter:
    async def query(self, **kwargs):
        raise RuntimeError("boom")


def _erp_tool() -> ERPTool:
    connection = create_sqlite_connection(check_same_thread=False)
    load_seed_sql(connection)
    return ERPTool(NorthwindRepository(connection))


def _erp_query_tool() -> ERPQueryTool:
    connection = create_sqlite_connection(check_same_thread=False)
    load_seed_sql(connection)
    return ERPQueryTool(NorthwindRepository(connection))


def _production_tool() -> ProductionAPITool:
    return ProductionAPITool(_production_client())


def _production_query_tool() -> ProductionQueryTool:
    return ProductionQueryTool(_production_client())


def _production_client() -> ProductionAPIClient:
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
        if request.url.path == "/production/orders":
            status = request.url.params.get("status")
            values = list(orders.values())
            if status:
                values = [
                    order
                    for order in values
                    if order["production_status"] == status
                ]
            return httpx.Response(200, json={"orders": values})

        if request.url.path.startswith("/production/orders/"):
            order_id = int(request.url.path.rsplit("/", 1)[1])
            order = orders.get(order_id)
            if order is None:
                return httpx.Response(404, json={"detail": "not found"})
            return httpx.Response(200, json=order)

        return httpx.Response(500, text="unexpected path")

    return ProductionAPIClient(
        base_url="http://production-api.test",
        transport=httpx.MockTransport(handler),
    )


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
