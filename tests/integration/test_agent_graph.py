import httpx
import pytest

from app.agents.graph import run_agent_graph
from app.erp.database import create_sqlite_connection, load_seed_sql
from app.erp.repositories import NorthwindRepository
from app.production.client import ProductionAPIClient
from app.tools.erp_tool import ERPTool
from app.tools.production_tool import ProductionAPITool


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


def test_agent_graph_returns_insufficient_context_for_rag_before_phase_6(
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
    assert response.tool_calls == []
    assert "contexto documental suficiente" in response.answer


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
