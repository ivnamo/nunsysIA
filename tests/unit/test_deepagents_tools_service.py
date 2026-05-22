import httpx

from app.agents import deepagents_tools_service as service_module
from app.agents.deepagents_tools_service import DeepAgentsToolsQueryService
from app.core.tracing import ToolCallTrace, ToolResult
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
from app.tools.rag_tool import DocumentRAGInput
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


class _ToolNamesAgent:
    def __init__(self, tools, seen: dict):
        seen["tool_names"] = [tool.__name__ for tool in tools]

    def invoke(self, payload: dict) -> dict:
        return {"messages": [{"content": "Sin consultas para inspeccion de tools."}]}


class _RAGSpamAgent:
    def __init__(self, tools):
        self._tools = {tool.__name__: tool for tool in tools}

    def invoke(self, payload: dict) -> dict:
        query_documents = self._tools["query_documents"]
        query_documents("contrato penalizaciones")
        query_documents("otra consulta documental")
        query_documents("contrato penalizaciones")
        return {"messages": [{"content": "Respuesta documental con presupuesto RAG."}]}


class _FollowupAgent:
    def __init__(self, tools):
        self._tools = {tool.__name__: tool for tool in tools}

    def invoke(self, payload: dict) -> dict:
        if "resolve_referenced_orders_with_erp_and_production" in self._tools:
            self._tools["resolve_referenced_orders_with_erp_and_production"]()
        else:
            self._tools["get_pending_orders_by_customer"]("ALFKI")
        return {
            "messages": [
                {
                    "content": (
                        "ALFKI tiene los pedidos 10248 y 10252 con estados "
                        "actuales consultados."
                    )
                }
            ]
        }


class _TodosAgent:
    def __init__(self, tools):
        self._tools = {tool.__name__: tool for tool in tools}

    def invoke(self, payload: dict) -> dict:
        self._tools["query_erp_orders"](limit=1)
        return {
            "messages": [
                {
                    "content": "",
                    "tool_calls": [
                        {
                            "name": "write_todos",
                            "args": {
                                "todos": [
                                    {"content": "Consultar ERP", "status": "done"}
                                ]
                            },
                        }
                    ],
                },
                {"content": "Respuesta con planificacion interna Deep Agents."},
            ]
        }


class _CountingRAGTool:
    def __init__(self) -> None:
        self.query_count = 0

    def query(self, tool_input: DocumentRAGInput) -> ToolResult:
        self.query_count += 1
        return ToolResult(
            data={
                "status": "completed",
                "chunks": [
                    {
                        "text": "No se aplican penalizaciones por falta de material.",
                        "score": 0.91,
                        "metadata": {
                            "filename": "contrato.pdf",
                            "page": 1,
                            "chunk_id": "contrato-1",
                        },
                    }
                ],
            },
            tool_call=ToolCallTrace(
                tool="DocumentRAGTool",
                action="query",
                args=tool_input.model_dump(),
                status="success",
                output_summary="1 chunks documentales recuperados",
                duration_ms=0,
                source="Documentos",
            ),
        )


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


def test_deepagents_tools_service_selects_tools_by_intent() -> None:
    seen: dict = {}
    service = DeepAgentsToolsQueryService(
        erp_tool=_erp_tool(),
        production_tool=_production_tool(),
        erp_query_tool=_erp_query_tool(),
        production_query_tool=_production_query_tool(),
        rag_tool=_rag_tool(),
        model="google_genai:gemini-3.5-flash",
        agent_builder=lambda **kwargs: _ToolNamesAgent(kwargs["tools"], seen),
    )

    service.run(
        QueryRequest(
            question="Que pedidos pendientes tiene ALFKI?",
            conversation_id="tools-selection",
        )
    )

    assert "query_documents" not in seen["tool_names"]
    assert "get_pending_orders_by_customer" in seen["tool_names"]
    assert "query_erp_orders" in seen["tool_names"]
    assert "query_production_orders" not in seen["tool_names"]


def test_deepagents_tools_service_limits_document_queries() -> None:
    rag_tool = _CountingRAGTool()
    service = DeepAgentsToolsQueryService(
        erp_tool=_erp_tool(),
        production_tool=_production_tool(),
        erp_query_tool=_erp_query_tool(),
        production_query_tool=_production_query_tool(),
        rag_tool=rag_tool,
        model="google_genai:gemini-3.5-flash",
        agent_builder=lambda **kwargs: _RAGSpamAgent(kwargs["tools"]),
    )

    response = service.run(
        QueryRequest(
            question="Que dice el contrato sobre penalizaciones?",
            conversation_id="tools-rag-budget",
        )
    )

    assert rag_tool.query_count == 1
    assert [call.tool for call in response.tool_calls] == ["DocumentRAGTool"]
    assert response.data["rag"]["chunks_count"] == 1


def test_deepagents_tools_service_resolves_followups_with_erp_and_production() -> None:
    service = DeepAgentsToolsQueryService(
        erp_tool=_erp_tool(),
        production_tool=_production_tool(),
        erp_query_tool=_erp_query_tool(),
        production_query_tool=_production_query_tool(),
        rag_tool=_rag_tool(),
        model="google_genai:gemini-3.5-flash",
        agent_builder=lambda **kwargs: _FollowupAgent(kwargs["tools"]),
    )

    service.run(
        QueryRequest(
            question="Que pedidos pendientes tiene ALFKI?",
            conversation_id="tools-followup",
        )
    )
    response = service.run(
        QueryRequest(
            question="Y en que estado estan?",
            conversation_id="tools-followup",
        )
    )

    assert response.sources == ["Memoria", "ERP", "Produccion"]
    assert [call.tool for call in response.tool_calls] == [
        "MemoryTool",
        "ERPQueryTool",
        "ProductionAPITool",
    ]


def test_deepagents_tools_service_exposes_sanitized_todo_usage() -> None:
    service = DeepAgentsToolsQueryService(
        erp_tool=_erp_tool(),
        production_tool=_production_tool(),
        erp_query_tool=_erp_query_tool(),
        production_query_tool=_production_query_tool(),
        rag_tool=_rag_tool(),
        model="google_genai:gemini-3.5-flash",
        agent_builder=lambda **kwargs: _TodosAgent(kwargs["tools"]),
    )

    response = service.run(
        QueryRequest(
            question="Cruza produccion con ERP y dime clientes afectados por bloqueos.",
            conversation_id="tools-todos",
        )
    )

    assert response.data["deepagents_planning"] == {
        "todos_used": True,
        "todo_tool_calls_count": 1,
    }
    assert "Consultar ERP" not in str(response.data["deepagents_planning"])


def test_deepagents_business_harness_excludes_system_tools() -> None:
    captured: dict = {}

    class _Profile:
        def __init__(self, excluded_tools):
            self.excluded_tools = excluded_tools

    def register(key, profile) -> None:
        captured["key"] = key
        captured["excluded_tools"] = profile.excluded_tools

    service_module._REGISTERED_BUSINESS_HARNESS_MODELS.clear()
    service_module._register_business_harness_profile(
        "google_genai:gemini-3.5-flash",
        harness_profile=_Profile,
        register_harness_profile=register,
    )

    assert captured["key"] == "google_genai:gemini-3.5-flash"
    assert {"read_file", "write_file", "execute", "task"}.issubset(
        captured["excluded_tools"]
    )
    assert "write_todos" not in captured["excluded_tools"]


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
