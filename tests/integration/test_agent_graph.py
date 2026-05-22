import httpx
import pytest

from app.agents.graph import run_agent_graph
from app.erp.database import create_sqlite_connection, load_seed_sql
from app.erp.repositories import NorthwindRepository
from app.production.client import ProductionAPIClient
from app.rag.embeddings import DeterministicEmbeddingModel
from app.rag.ingestion import DocumentIngestionService
from app.rag.vector_store import InMemoryDocumentVectorStore
from app.tools.erp_query_tool import ERPQueryTool
from app.tools.erp_tool import ERPTool
from app.tools.production_query_tool import ProductionQueryTool
from app.tools.production_tool import ProductionAPITool
from app.tools.rag_tool import DocumentRAGTool


class _FailingEmbeddingModel:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("embedding provider unavailable")

    def embed_query(self, text: str) -> list[float]:
        raise RuntimeError("embedding provider unavailable")


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _SequenceChatModel:
    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self.calls = 0

    def invoke(self, input: object, **kwargs: object) -> _FakeMessage:
        response = self._responses[min(self.calls, len(self._responses) - 1)]
        self.calls += 1
        return _FakeMessage(response)


@pytest.fixture()
def erp_tool() -> ERPTool:
    connection = create_sqlite_connection()
    load_seed_sql(connection)
    return ERPTool(NorthwindRepository(connection))


@pytest.fixture()
def erp_query_tool() -> ERPQueryTool:
    connection = create_sqlite_connection()
    load_seed_sql(connection)
    return ERPQueryTool(NorthwindRepository(connection))


@pytest.fixture()
def production_tool() -> ProductionAPITool:
    client = ProductionAPIClient(
        base_url="http://production-api.test",
        transport=_production_transport(),
    )
    return ProductionAPITool(client)


@pytest.fixture()
def production_query_tool() -> ProductionQueryTool:
    client = ProductionAPIClient(
        base_url="http://production-api.test",
        transport=_production_transport(),
    )
    return ProductionQueryTool(client)


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


def test_agent_graph_uses_memory_to_resolve_follow_up(
    erp_tool: ERPTool,
    production_tool: ProductionAPITool,
) -> None:
    response = run_agent_graph(
        erp_tool=erp_tool,
        production_tool=production_tool,
        question="Y en que estado estan?",
        conversation_id="demo-memory",
        conversation_history=[
            {
                "question": "Que pedidos pendientes tiene el cliente ALFKI?",
                "answer": "El cliente ALFKI tiene 2 pedidos pendientes: 10248, 10252.",
                "status": "completed",
                "sources": ["ERP"],
                "facts": {"customer_id": "ALFKI", "order_ids": [10248, 10252]},
            }
        ],
    )

    assert response.status == "completed"
    assert response.sources == ["Memoria", "ERP", "Produccion"]
    assert "10248" in response.answer
    assert "10252" in response.answer
    assert [call.tool for call in response.tool_calls] == [
        "MemoryTool",
        "ERPTool",
        "ProductionAPITool",
        "ProductionAPITool",
    ]
    assert response.data["memory"]["customer_id"] == "ALFKI"
    assert response.data["memory"]["order_ids"] == [10248, 10252]


def test_agent_graph_filters_blocked_orders_from_memory_follow_up(
    erp_tool: ERPTool,
    production_tool: ProductionAPITool,
) -> None:
    response = run_agent_graph(
        erp_tool=erp_tool,
        production_tool=production_tool,
        question="Y cuales de esos pedidos estan bloqueados?",
        conversation_id="demo-memory",
        conversation_history=[
            {
                "question": "Que pedidos pendientes tiene el cliente ALFKI?",
                "answer": "El cliente ALFKI tiene 2 pedidos pendientes: 10248, 10252.",
                "status": "completed",
                "sources": ["ERP"],
                "facts": {"customer_id": "ALFKI", "order_ids": [10248, 10252]},
            }
        ],
    )

    assert response.status == "completed"
    assert response.sources == ["Memoria", "Produccion", "ERP"]
    assert "10252" in response.answer
    assert "Falta de material" in response.answer
    assert "10248" not in response.answer
    assert [call.tool for call in response.tool_calls] == [
        "MemoryTool",
        "ProductionAPITool",
        "ERPTool",
    ]
    assert response.data["production_order_ids"] == [10252]
    assert response.data["memory"]["order_ids"] == [10248, 10252]


def test_agent_graph_calculates_economic_impact_from_memory_follow_up(
    erp_tool: ERPTool,
    production_tool: ProductionAPITool,
) -> None:
    response = run_agent_graph(
        erp_tool=erp_tool,
        production_tool=production_tool,
        question="Cual es el impacto economico de esos?",
        conversation_id="demo-memory",
        conversation_history=[
            {
                "question": "Y cuales de esos pedidos estan bloqueados?",
                "answer": "El pedido 10252 esta bloqueado por Falta de material.",
                "status": "completed",
                "sources": ["Memoria", "Produccion", "ERP"],
                "facts": {"customer_id": "ALFKI", "order_ids": [10252]},
            }
        ],
    )

    assert response.status == "completed"
    assert response.sources == ["Memoria", "ERP"]
    assert "10252" in response.answer
    assert "1863.00" in response.answer
    assert [call.tool for call in response.tool_calls] == [
        "MemoryTool",
        "ERPTool",
    ]
    assert response.data["order_amounts_count"] == 1
    assert response.data["order_amount_order_ids"] == [10252]
    assert response.data["economic_impact_total"] == "1863.00"
    assert "product_id" not in str(response.data)


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


def test_agent_graph_answers_delayed_orders_with_erp_customer_context(
    erp_tool: ERPTool,
    production_tool: ProductionAPITool,
) -> None:
    response = run_agent_graph(
        erp_tool=erp_tool,
        production_tool=production_tool,
        question="Que clientes tienen pedidos retrasados por problemas de produccion?",
    )

    assert response.status == "completed"
    assert response.sources == ["Produccion", "ERP"]
    assert "clientes afectados" in response.answer
    assert "retrasado" in response.answer
    assert "10301" in response.answer
    assert "Ana Trujillo Emparedados" in response.answer
    assert "Averia en linea de produccion" in response.answer


def test_agent_graph_answers_problematic_production_orders(
    erp_tool: ERPTool,
    production_tool: ProductionAPITool,
) -> None:
    response = run_agent_graph(
        erp_tool=erp_tool,
        production_tool=production_tool,
        question="Que pedidos tengo parados o con problemas de produccion?",
    )

    assert response.status == "completed"
    assert response.sources == ["Produccion", "ERP"]
    assert "10252" in response.answer
    assert "10312" in response.answer
    assert "10301" in response.answer
    assert "Falta de material" in response.answer
    assert "Falta de capacidad" in response.answer
    assert "Averia en linea de produccion" in response.answer
    assert [call.action for call in response.tool_calls[:3]] == [
        "list_orders",
        "list_orders",
        "get_customers_for_production_orders",
    ]
    assert response.data["production_order_ids"] == [10252, 10312, 10301]


def test_agent_graph_executes_safe_query_dsl_for_cross_blocked_customers(
    erp_tool: ERPTool,
    production_tool: ProductionAPITool,
    erp_query_tool: ERPQueryTool,
    production_query_tool: ProductionQueryTool,
) -> None:
    response = run_agent_graph(
        erp_tool=erp_tool,
        production_tool=production_tool,
        erp_query_tool=erp_query_tool,
        production_query_tool=production_query_tool,
        question="Cruza produccion con ERP y dime clientes afectados por bloqueos.",
    )

    assert response.status == "completed"
    assert response.sources == ["Produccion", "ERP"]
    assert [call.tool for call in response.tool_calls] == [
        "ProductionQueryTool",
        "ERPQueryTool",
    ]
    assert [call.action for call in response.tool_calls] == [
        "query_orders",
        "query_orders",
    ]
    assert response.tool_calls[0].args["filters"] == [
        {
            "field": "production_status",
            "operator": "eq",
            "value": "blocked",
        }
    ]
    assert response.tool_calls[1].args["filters"] == [
        {"field": "order_id", "operator": "in", "value": [10252, 10312]}
    ]
    assert response.answer.startswith("Hay clientes afectados por bloqueos")
    assert "10252" in response.answer
    assert "10312" in response.answer
    assert "Alfreds Futterkiste" in response.answer
    assert "BONAP - Bon app" in response.answer
    assert "10301" not in response.answer
    assert response.data["production_order_ids"] == [10252, 10312]
    assert response.data["erp_query_order_ids"] == [10252, 10312]
    assert response.data["customers_resolved_count"] == 2
    assert "product_id" not in str(response.data)


def test_agent_graph_answers_lowercase_customer_operational_risk(
    erp_tool: ERPTool,
    production_tool: ProductionAPITool,
) -> None:
    response = run_agent_graph(
        erp_tool=erp_tool,
        production_tool=production_tool,
        question="que tiene pendiente alfki y que riesgo operativo tiene?",
    )

    assert response.status == "completed"
    assert response.sources == ["ERP", "Produccion"]
    assert "10248" in response.answer
    assert "10252" in response.answer
    assert "Falta de material" in response.answer


def test_agent_graph_answers_explicit_order_status_query(
    erp_tool: ERPTool,
    production_tool: ProductionAPITool,
) -> None:
    response = run_agent_graph(
        erp_tool=erp_tool,
        production_tool=production_tool,
        question="en que estado esta el pedido 10252?",
    )

    assert response.status == "completed"
    assert response.sources == ["Produccion", "ERP"]
    assert "10252" in response.answer
    assert "Falta de material" in response.answer
    assert "Alfreds Futterkiste" in response.answer
    assert response.data["production_order_ids"] == [10252]


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
    assert response.tool_calls[0].action == "query"
    assert "documentos disponibles" in response.answer


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
    citation = response.data["rag"]["citations"][0]
    assert citation["filename"] == "contrato.pdf"
    assert citation["page"] == 1
    assert citation["chunk_id"].endswith("_p1_c1")
    assert isinstance(citation["score"], float)
    assert response.tool_calls[0].tool == "DocumentRAGTool"


def test_agent_graph_answers_order_penalties_with_erp_production_and_documents(
    erp_tool: ERPTool,
    production_tool: ProductionAPITool,
) -> None:
    vector_store = InMemoryDocumentVectorStore()
    service = DocumentIngestionService(vector_store=vector_store)
    service.ingest_pdf(
        content=_pdf_bytes(
            "Penalizaciones por retrasos. No aplicacion por bloqueo de produccion, "
            "falta de material, falta de capacidad o averia en linea."
        ),
        filename="anexo_penalizaciones_sla.pdf",
    )

    response = run_agent_graph(
        erp_tool=erp_tool,
        production_tool=production_tool,
        rag_tool=DocumentRAGTool(
            vector_store=vector_store,
            embedding_model=DeterministicEmbeddingModel(),
        ),
        question="en funcion de los pedidos y su estado dime que penalizaciones vamos a tener en cada uno",
    )

    assert response.status == "completed"
    assert response.sources == ["ERP", "Produccion", "Documentos"]
    assert "evaluacion de penalizaciones por pedido" in response.answer
    assert "10252" in response.answer
    assert "Falta de material" in response.answer
    assert "10301" in response.answer
    assert "Averia en linea de produccion" in response.answer
    assert "No aplicable" in response.answer
    assert [call.tool for call in response.tool_calls] == [
        "ERPTool",
        "ProductionAPITool",
        "ProductionAPITool",
        "ProductionAPITool",
        "ProductionAPITool",
        "ProductionAPITool",
        "DocumentRAGTool",
    ]
    assert response.data["rag"]["documents"] == ["anexo_penalizaciones_sla.pdf"]


def test_agent_graph_answers_potential_penalty_orders_with_enriched_rag_query(
    erp_tool: ERPTool,
    production_tool: ProductionAPITool,
) -> None:
    vector_store = InMemoryDocumentVectorStore()
    service = DocumentIngestionService(vector_store=vector_store)
    service.ingest_pdf(
        content=_pdf_bytes(
            "Penalizaciones por retrasos. No aplicacion por bloqueo de produccion, "
            "falta de material, falta de capacidad o averia en linea."
        ),
        filename="anexo_penalizaciones_sla.pdf",
    )

    response = run_agent_graph(
        erp_tool=erp_tool,
        production_tool=production_tool,
        rag_tool=DocumentRAGTool(
            vector_store=vector_store,
            embedding_model=DeterministicEmbeddingModel(),
        ),
        question="Dame los pedidos que puedan generar penalizacion y dime por que.",
    )

    assert response.status == "completed"
    assert response.sources == ["ERP", "Produccion", "Documentos"]
    assert "evaluacion de penalizaciones por pedido" in response.answer
    assert "10252" in response.answer
    assert "10301" in response.answer
    assert "No aplicable" in response.answer
    assert response.tool_calls[-1].tool == "DocumentRAGTool"
    assert response.tool_calls[-1].args["query"] == (
        "penalizaciones por retrasos no aplicacion bloqueo produccion falta "
        "material falta capacidad averia linea"
    )
    assert response.data["rag"]["documents"] == ["anexo_penalizaciones_sla.pdf"]


def test_agent_graph_blocks_order_penalties_when_document_context_is_insufficient(
    erp_tool: ERPTool,
    production_tool: ProductionAPITool,
) -> None:
    response = run_agent_graph(
        erp_tool=erp_tool,
        production_tool=production_tool,
        rag_tool=DocumentRAGTool(
            vector_store=InMemoryDocumentVectorStore(),
            embedding_model=DeterministicEmbeddingModel(),
        ),
        question="en funcion de los pedidos y su estado dime que penalizaciones vamos a tener en cada uno",
    )

    assert response.status == "insufficient_context"
    assert response.sources == ["ERP", "Produccion", "Documentos"]
    assert "documentos disponibles" in response.answer
    assert "evaluacion de penalizaciones por pedido" not in response.answer
    assert response.data["rag"]["status"] == "insufficient_context"


def test_agent_graph_returns_tool_error_when_rag_embedding_fails(
    erp_tool: ERPTool,
    production_tool: ProductionAPITool,
) -> None:
    response = run_agent_graph(
        erp_tool=erp_tool,
        production_tool=production_tool,
        rag_tool=DocumentRAGTool(
            vector_store=InMemoryDocumentVectorStore(),
            embedding_model=_FailingEmbeddingModel(),
        ),
        question="Que dice el PDF del contrato sobre penalizacion por retrasos?",
    )

    assert response.status == "tool_error"
    assert response.sources == ["Documentos"]
    assert response.tool_calls[0].status == "error"
    assert "fiabilidad" in response.answer


def test_agent_graph_exposes_replan_trace_without_raw_attempt_data(
    erp_tool: ERPTool,
    production_tool: ProductionAPITool,
) -> None:
    chat_model = _SequenceChatModel(
        [
            """
            {
              "intent": "erp_production",
              "steps": [
                {
                  "step_id": 1,
                  "tool": "ERPTool",
                  "action": "get_pending_orders_by_customer",
                  "args": {"customer_id": "ALFKI"},
                  "required": true
                }
              ],
              "expected_sources": ["ERP", "Produccion"],
              "answer_requirements": []
            }
            """,
            """
            {
              "intent": "erp_production",
              "steps": [
                {
                  "step_id": 1,
                  "tool": "ERPTool",
                  "action": "get_pending_orders_by_customer",
                  "args": {"customer_id": "ALFKI"},
                  "required": true
                },
                {
                  "step_id": 2,
                  "tool": "ProductionAPITool",
                  "action": "get_status_for_erp_orders",
                  "args": {},
                  "required": true
                }
              ],
              "expected_sources": ["ERP", "Produccion"],
              "answer_requirements": []
            }
            """,
            "{}",
        ]
    )

    response = run_agent_graph(
        erp_tool=erp_tool,
        production_tool=production_tool,
        question="Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?",
        chat_model=chat_model,
    )

    assert response.status == "completed"
    assert response.sources == ["ERP", "Produccion"]
    assert response.data["replanning"] == {
        "replans_count": 1,
        "max_replans": 2,
        "events": [
            {
                "attempt": 1,
                "decision": "replan",
                "status": "partial_answer",
                "failure_reason": "Faltan fuentes obligatorias: Produccion.",
                "max_replans": 2,
            }
        ],
    }
    assert "steps" not in str(response.data["replanning"])
    assert "raw" not in str(response.data["replanning"]).lower()
    assert chat_model.calls >= 2


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
