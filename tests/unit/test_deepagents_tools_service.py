import httpx

from app.agents.deepagents_tools_service import DeepAgentsToolsQueryService
from app.erp.database import create_sqlite_connection, load_seed_sql
from app.erp.repositories import NorthwindRepository
from app.production.client import ProductionAPIClient
from app.rag.embeddings import DeterministicEmbeddingModel
from app.rag.ingestion import DocumentIngestionService
from app.rag.vector_store import InMemoryDocumentVectorStore
from app.schemas.query import QueryRequest
from app.tools.erp_query_tool import ERPQueryTool
from app.tools.erp_tool import ERPTool
from app.tools.production_query_tool import ProductionQueryTool
from app.tools.production_tool import ProductionAPITool
from app.tools.rag_tool import DocumentRAGTool


class _FakeAgent:
    def __init__(self, tools):
        self._tools = {tool.__name__: tool for tool in tools}

    def invoke(self, payload: dict) -> dict:
        orders = self._tools["get_pending_orders_by_customer"]("ALFKI")
        order_ids = [order["order_id"] for order in orders]
        self._tools["get_production_status_for_order_ids"](order_ids)
        return {
            "messages": [
                {
                    "content": (
                        "El cliente ALFKI tiene los pedidos 10248 y 10252; "
                        "10252 esta bloqueado por falta de material."
                    )
                }
            ]
        }


def test_deepagents_tools_service_records_direct_tool_traces() -> None:
    service = DeepAgentsToolsQueryService(
        erp_tool=_erp_tool(),
        production_tool=_production_tool(),
        erp_query_tool=_erp_query_tool(),
        production_query_tool=_production_query_tool(),
        rag_tool=_rag_tool(),
        model="google_genai:gemini-3.5-flash",
        agent_builder=lambda **kwargs: _FakeAgent(kwargs["tools"]),
    )

    response = service.run(
        QueryRequest(
            question="Que pedidos pendientes tiene el cliente ALFKI y en que estado estan?",
            conversation_id="tools-demo",
        )
    )

    assert response.status == "completed"
    assert response.sources == ["ERP", "Produccion"]
    assert [call.tool for call in response.tool_calls] == [
        "ERPTool",
        "ProductionAPITool",
    ]
    assert response.data == {
        "erp_orders_count": 2,
        "erp_order_ids": [10248, 10252],
        "production_orders_count": 2,
        "production_order_ids": [10248, 10252],
        "production_statuses_count": 2,
    }
    assert "10252" in response.answer


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
        if request.url.path.startswith("/production/orders/"):
            order_id = int(request.url.path.rsplit("/", 1)[1])
            return httpx.Response(200, json=orders[order_id])
        if request.url.path == "/production/orders":
            return httpx.Response(200, json={"orders": list(orders.values())})
        return httpx.Response(500, text="unexpected path")

    return ProductionAPIClient(
        base_url="http://production-api.test",
        transport=httpx.MockTransport(handler),
    )


def _rag_tool() -> DocumentRAGTool:
    document_service = DocumentIngestionService(
        vector_store=InMemoryDocumentVectorStore(),
        embedding_model=DeterministicEmbeddingModel(),
    )
    return DocumentRAGTool(
        vector_store=document_service.vector_store,
        embedding_model=document_service.embedding_model,
    )
