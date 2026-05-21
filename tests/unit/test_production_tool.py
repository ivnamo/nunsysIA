import httpx
import pytest
from pydantic import ValidationError

from app.production.client import ProductionAPIClient
from app.tools.production_tool import (
    ProductionAPITool,
    ProductionOrderInput,
    ProductionOrdersByIdsInput,
    ProductionOrdersInput,
)


def _mock_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/production/orders/10252":
            return httpx.Response(
                200,
                json={
                    "order_id": 10252,
                    "production_status": "blocked",
                    "blocked_reason": "Falta de material",
                    "delay_reason": None,
                    "estimated_finish_date": "2026-05-30",
                },
            )
        if request.url.path == "/production/orders/10248":
            return httpx.Response(
                200,
                json={
                    "order_id": 10248,
                    "production_status": "in_progress",
                    "blocked_reason": None,
                    "delay_reason": None,
                    "estimated_finish_date": "2026-05-22",
                },
            )
        if request.url.path == "/production/orders/99999":
            return httpx.Response(404, json={"detail": "Production order not found"})
        if request.url.path == "/production/orders":
            status = request.url.params.get("status")
            if status == "blocked":
                return httpx.Response(
                    200,
                    json={
                        "orders": [
                            {
                                "order_id": 10252,
                                "production_status": "blocked",
                                "blocked_reason": "Falta de material",
                                "delay_reason": None,
                                "estimated_finish_date": "2026-05-30",
                            },
                            {
                                "order_id": 10312,
                                "production_status": "blocked",
                                "blocked_reason": "Falta de capacidad",
                                "delay_reason": None,
                                "estimated_finish_date": "2026-06-02",
                            },
                        ]
                    },
                )
        return httpx.Response(500, text="unexpected path")

    return httpx.MockTransport(handler)


@pytest.fixture()
def production_tool() -> ProductionAPITool:
    client = ProductionAPIClient(
        base_url="http://production-api.test",
        transport=_mock_transport(),
    )
    return ProductionAPITool(client)


def test_production_tool_get_order_status_returns_structured_data_and_trace(
    production_tool: ProductionAPITool,
) -> None:
    result = production_tool.get_order_status(ProductionOrderInput(order_id=10252))

    assert result.data == {
        "order_id": 10252,
        "production_status": "blocked",
        "blocked_reason": "Falta de material",
        "delay_reason": None,
        "estimated_finish_date": "2026-05-30",
    }
    assert result.tool_call.tool == "ProductionAPITool"
    assert result.tool_call.args == {"order_id": 10252}
    assert result.tool_call.status == "success"
    assert result.tool_call.source == "Produccion"


def test_production_tool_list_orders_filters_by_status(
    production_tool: ProductionAPITool,
) -> None:
    result = production_tool.list_orders(ProductionOrdersInput(status="blocked"))

    assert [order["order_id"] for order in result.data] == [10252, 10312]
    assert result.tool_call.args == {"status": "blocked"}
    assert result.tool_call.output_summary == "2 pedidos de produccion encontrados con estado blocked"


def test_production_tool_get_status_for_order_ids_filters_by_status(
    production_tool: ProductionAPITool,
) -> None:
    result = production_tool.get_status_for_order_ids(
        ProductionOrdersByIdsInput(order_ids=[10248, 10252], status="blocked")
    )

    assert [order["order_id"] for order in result.data] == [10252]
    assert result.tool_call.args == {
        "order_ids": [10248, 10252],
        "status": "blocked",
    }
    assert result.tool_call.action == "get_status_for_order_ids"
    assert (
        result.tool_call.output_summary
        == "1 pedidos de produccion encontrados por ids con estado blocked"
    )


def test_production_tool_returns_success_with_none_for_missing_order(
    production_tool: ProductionAPITool,
) -> None:
    result = production_tool.get_order_status(ProductionOrderInput(order_id=99999))

    assert result.data is None
    assert result.tool_call.status == "success"
    assert result.tool_call.output_summary == "Pedido no encontrado en produccion"


def test_production_tool_returns_error_trace_for_api_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="service unavailable")

    client = ProductionAPIClient(
        base_url="http://production-api.test",
        transport=httpx.MockTransport(handler),
    )
    tool = ProductionAPITool(client)

    result = tool.get_order_status(ProductionOrderInput(order_id=10252))

    assert result.data is None
    assert result.tool_call.status == "error"
    assert result.tool_call.error is not None
    assert "status 500" in result.tool_call.error


def test_production_tool_rejects_invalid_order_input() -> None:
    with pytest.raises(ValidationError):
        ProductionOrderInput(order_id=0)
