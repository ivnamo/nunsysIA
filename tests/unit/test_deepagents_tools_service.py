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


class _DocumentRedactionAgent:
    def __init__(self, seen: dict) -> None:
        self._seen = seen

    def invoke(self, payload: dict) -> dict:
        prompt = payload["messages"][0]["content"]
        self._seen["prompt"] = prompt
        return {
            "messages": [
                {
                    "content": (
                        "```json\n"
                        "{\n"
                        '  "answer": "El documento establece que, para pedidos '
                        "standard, el plazo maximo de entrega es de 5 dias "
                        "laborables desde la liberacion de produccion. Tambien "
                        'fija 48 horas para pedidos urgentes.",\n'
                        '  "sources": ["Documentos"],\n'
                        '  "reasoning": ["Sintesis documental"]\n'
                        "}\n"
                        "```"
                    )
                }
            ]
        }


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
        self._tools["get_blocked_production_orders_with_erp"]()
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


class _DelayedOverqueryAgent:
    def __init__(self, tools):
        self._tools = {tool.__name__: tool for tool in tools}

    def invoke(self, payload: dict) -> dict:
        if "query_production_orders" in self._tools:
            self._tools["query_production_orders"]()
        if "query_erp_orders" in self._tools:
            self._tools["query_erp_orders"](limit=2)
        return {"messages": [{"content": "Respuesta no determinista."}]}


class _StaticAgent:
    def __init__(self, content: str) -> None:
        self._content = content

    def invoke(self, payload: dict) -> dict:
        return {"messages": [{"content": self._content}]}


class _ExplodingAgent:
    def invoke(self, payload: dict) -> dict:
        raise AssertionError("DeepAgents no deberia ejecutarse en este preflight")


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


class _ChunkAnswerRAGTool:
    def query(self, tool_input: DocumentRAGInput) -> ToolResult:
        return ToolResult(
            data={
                "answer": (
                    "Contrato marco de logistica 2026 - version extendida "
                    "Pagina 2 de 4 - Plazos ordinarios: Los pedidos standard "
                    "deben entregarse en un plazo maximo de 5 dias laborables."
                ),
                "status": "completed",
                "chunks": [
                    {
                        "text": (
                            "Contrato marco de logistica 2026 - version extendida "
                            "Pagina 2 de 4 - Plazos ordinarios: Los pedidos "
                            "standard deben entregarse en un plazo maximo de "
                            "5 dias laborables desde la liberacion de produccion."
                        ),
                        "score": 0.91,
                        "metadata": {
                            "filename": "contrato.pdf",
                            "page": 2,
                            "chunk_id": "contrato-2",
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


class _EmptyRAGTool:
    def query(self, tool_input: DocumentRAGInput) -> ToolResult:
        return ToolResult(
            data={
                "answer": "No hay contexto documental suficiente para responder sin inventar.",
                "status": "insufficient_context",
                "chunks": [],
            },
            tool_call=ToolCallTrace(
                tool="DocumentRAGTool",
                action="query",
                args=tool_input.model_dump(),
                status="success",
                output_summary="0 chunks documentales recuperados",
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
    assert response.data["erp_orders_count"] == 2
    assert response.data["erp_order_ids"] == [10248, 10252]
    assert response.data["production_orders_count"] == 2
    assert response.data["production_order_ids"] == [10248, 10252]
    assert response.data["production_statuses_count"] == 2
    assert response.data["deepagents_planning"]["required_evidence"] == [
        "ERP",
        "Produccion",
    ]
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
    assert "query_erp_orders" not in seen["tool_names"]
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


def test_deepagents_tools_service_uses_deepagent_redaction_for_documents() -> None:
    seen: dict = {}
    service = DeepAgentsToolsQueryService(
        erp_tool=_erp_tool(),
        production_tool=_production_tool(),
        erp_query_tool=_erp_query_tool(),
        production_query_tool=_production_query_tool(),
        rag_tool=_ChunkAnswerRAGTool(),
        model="google_genai:gemini-3.5-flash",
        agent_builder=lambda **kwargs: _DocumentRedactionAgent(seen),
    )

    response = service.run(
        QueryRequest(
            question="Que dice el documento sobre plazos de entrega standard?",
            conversation_id="tools-rag-redaction",
        )
    )

    assert response.status == "completed"
    assert response.sources == ["Documentos"]
    assert response.answer.startswith(
        "El documento establece que, para pedidos standard"
    )
    assert "```json" not in response.answer
    assert '"answer"' not in response.answer
    assert "Pagina 2 de 4" not in response.answer
    assert response.reasoning == [
        "Consulta RAG documental para localizar evidencia verificable sobre la pregunta",
        "Selecciona 1 chunk(s) relevante(s) de contrato.pdf como base de evidencia",
        (
            "Sintetiza la respuesta final usando solo el contexto recuperado y "
            "deja las citas documentales auditables en data.rag.citations"
        ),
    ]
    assert "Contexto documental recuperado" in seen["prompt"]
    assert "No pegues chunks completos" in seen["prompt"]
    assert "contrato.pdf, pagina 2" in seen["prompt"]


def test_deepagents_tools_service_preflights_isolated_followup() -> None:
    service = DeepAgentsToolsQueryService(
        erp_tool=_erp_tool(),
        production_tool=_production_tool(),
        erp_query_tool=_erp_query_tool(),
        production_query_tool=_production_query_tool(),
        rag_tool=_rag_tool(),
        model="google_genai:gemini-3.5-flash",
        agent_builder=lambda **kwargs: _ExplodingAgent(),
    )

    response = service.run(
        QueryRequest(
            question="Y en que estado estan?",
            conversation_id="tools-isolated",
        )
    )

    assert response.status == "needs_clarification"
    assert response.sources == []
    assert response.tool_calls == []
    assert "cliente" in response.answer


def test_deepagents_tools_service_preserves_document_insufficient_context() -> None:
    service = DeepAgentsToolsQueryService(
        erp_tool=_erp_tool(),
        production_tool=_production_tool(),
        erp_query_tool=_erp_query_tool(),
        production_query_tool=_production_query_tool(),
        rag_tool=_EmptyRAGTool(),
        model="google_genai:gemini-3.5-flash",
        agent_builder=lambda **kwargs: _StaticAgent(
            "Te recomiendo una receta vegana inventada."
        ),
    )

    response = service.run(
        QueryRequest(
            question="Segun el PDF, que receta de cocina vegana recomienda?",
            conversation_id="tools-document-guardrail",
        )
    )

    assert response.status == "insufficient_context"
    assert response.sources == ["Documentos"]
    assert [call.tool for call in response.tool_calls] == ["DocumentRAGTool"]
    assert response.data["rag"]["chunks_count"] == 0
    assert "recomiendo" not in response.answer.lower()


def test_deepagents_tools_service_uses_beta_safe_penalty_tools() -> None:
    service = DeepAgentsToolsQueryService(
        erp_tool=_erp_tool(),
        production_tool=_production_tool_with_all_beta_orders(),
        erp_query_tool=_erp_query_tool(),
        production_query_tool=_production_query_tool(),
        rag_tool=_CountingRAGTool(),
        model="google_genai:gemini-3.5-flash",
        agent_builder=lambda **kwargs: _StaticAgent(
            "El pedido 10248 tiene penalizacion de 22.00."
        ),
    )

    response = service.run(
        QueryRequest(
            question=(
                "en funcion de los pedidos y su estado dime que penalizaciones "
                "vamos a tener en cada uno"
            ),
            conversation_id="tools-penalty-beta",
        )
    )

    assert response.status == "completed"
    assert response.sources == ["ERP", "Produccion", "Documentos"]
    assert [call.tool for call in response.tool_calls] == [
        "ERPTool",
        "ProductionAPITool",
        "DocumentRAGTool",
    ]
    assert response.data["erp_order_ids"] == [10248, 10252, 10255, 10301, 10312]
    assert "10248" in response.answer
    assert "10312" in response.answer
    assert "22.00" not in response.answer


def test_deepagents_tools_service_handles_delayed_orders_beta_case() -> None:
    service = DeepAgentsToolsQueryService(
        erp_tool=_erp_tool(),
        production_tool=_production_tool_with_all_beta_orders(),
        erp_query_tool=_erp_query_tool(),
        production_query_tool=_production_query_tool(),
        rag_tool=_rag_tool(),
        model="google_genai:gemini-3.5-flash",
        agent_builder=lambda **kwargs: _DelayedOverqueryAgent(kwargs["tools"]),
    )

    response = service.run(
        QueryRequest(
            question="Que clientes tienen pedidos retrasados por problemas de produccion?",
            conversation_id="tools-delayed-beta",
        )
    )

    assert response.status == "completed"
    assert response.sources == ["Produccion", "ERP"]
    assert "ProductionQueryTool" in [call.tool for call in response.tool_calls]
    assert "ERPQueryTool" in [call.tool for call in response.tool_calls]
    assert response.data["production_order_ids"] == [10301]
    assert "10301" in response.answer
    assert "ANATR" in response.answer
    assert "10252" not in response.answer
    assert "10312" not in response.answer
    assert "bloqueado" not in response.answer


def test_deepagents_tools_service_handles_month_summary_beta_case() -> None:
    service = DeepAgentsToolsQueryService(
        erp_tool=_erp_tool(),
        production_tool=_production_tool_with_all_beta_orders(),
        erp_query_tool=_erp_query_tool(),
        production_query_tool=_production_query_tool(),
        rag_tool=_rag_tool(),
        model="google_genai:gemini-3.5-flash",
        agent_builder=lambda **kwargs: _StaticAgent("Respuesta no determinista."),
    )

    response = service.run(
        QueryRequest(
            question="Dame un resumen del estado de los pedidos de este mes",
            conversation_id="tools-month-beta",
        )
    )

    assert response.status == "completed"
    assert response.sources == ["ERP", "Produccion"]
    assert response.data["period"] == {"year": 2026, "month": 5}
    assert response.data["erp_order_ids"] == [10248, 10252, 10255, 10301, 10312]
    assert "mayo" in response.answer
    assert "2026-05" in response.answer
    assert "bloqueado" in response.answer
    assert "retrasado" in response.answer
    assert "enviado" in response.answer
    assert "shipped" not in response.answer


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

    assert response.sources == ["Memoria", "Produccion", "ERP"]
    tool_names = [call.tool for call in response.tool_calls]
    assert tool_names[:2] == ["MemoryTool", "ProductionAPITool"]
    assert tool_names.count("MemoryTool") == 1
    assert "ERPTool" in tool_names


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

    assert response.data["deepagents_planning"]["todos_used"] is True
    assert response.data["deepagents_planning"]["todo_tool_calls_count"] == 1
    assert response.data["deepagents_planning"]["required_evidence"] == [
        "ERP",
        "Produccion",
    ]
    assert "erp_specialist" in response.data["deepagents_planning"]["subagents_available"]
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


def test_deepagents_tools_service_resolves_conversational_economic_impact() -> None:
    service = DeepAgentsToolsQueryService(
        erp_tool=_erp_tool(),
        production_tool=_production_tool(),
        erp_query_tool=_erp_query_tool(),
        production_query_tool=_production_query_tool(),
        rag_tool=_rag_tool(),
        model="google_genai:gemini-3.5-flash",
        agent_builder=lambda **kwargs: _StaticAgent("Respuesta no determinista."),
    )

    service.run(
        QueryRequest(
            question="Que pedidos pendientes tiene el cliente ALFKI?",
            conversation_id="tools-economic-memory",
        )
    )
    blocked_response = service.run(
        QueryRequest(
            question="Y cuales de esos pedidos estan bloqueados?",
            conversation_id="tools-economic-memory",
        )
    )
    response = service.run(
        QueryRequest(
            question="Cual es el impacto economico de esos?",
            conversation_id="tools-economic-memory",
        )
    )

    assert blocked_response.data["production_order_ids"] == [10252]
    assert response.sources == ["Memoria", "ERP"]
    assert [call.tool for call in response.tool_calls] == ["MemoryTool", "ERPTool"]
    assert response.data["order_amount_order_ids"] == [10252]
    assert response.data["economic_impact_total"] == "1863.00"
    assert "1863.00" in response.answer


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


def _production_tool_with_all_beta_orders() -> ProductionAPITool:
    return ProductionAPITool(_production_client(include_all_beta_orders=True))


def _production_query_tool() -> ProductionQueryTool:
    return ProductionQueryTool(_production_client())


def _production_client(include_all_beta_orders: bool = False) -> ProductionAPIClient:
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
    if include_all_beta_orders:
        orders.update(
            {
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
        )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/production/orders/"):
            order_id = int(request.url.path.rsplit("/", 1)[1])
            return httpx.Response(200, json=orders[order_id])
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
