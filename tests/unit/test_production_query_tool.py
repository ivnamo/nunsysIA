import httpx

from app.production.client import ProductionAPIClient
from app.tools.production_query_tool import ProductionQueryTool
from app.tools.query_dsl import ProductionQuerySpec, QueryFilter, QueryOrder


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
        if request.url.path == "/production/orders/10312":
            return httpx.Response(
                200,
                json={
                    "order_id": 10312,
                    "production_status": "blocked",
                    "blocked_reason": "Falta de capacidad",
                    "delay_reason": None,
                    "estimated_finish_date": "2026-06-02",
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
            return httpx.Response(
                200,
                json={
                    "orders": [
                        {
                            "order_id": 10248,
                            "production_status": "in_progress",
                            "blocked_reason": None,
                            "delay_reason": None,
                            "estimated_finish_date": "2026-05-22",
                        },
                        {
                            "order_id": 10301,
                            "production_status": "delayed",
                            "blocked_reason": None,
                            "delay_reason": "Averia en linea de produccion",
                            "estimated_finish_date": "2026-06-03",
                        },
                    ]
                },
            )
        return httpx.Response(500, text="unexpected path")

    return httpx.MockTransport(handler)


def _tool(transport: httpx.MockTransport | None = None) -> ProductionQueryTool:
    client = ProductionAPIClient(
        base_url="http://production-api.test",
        transport=transport or _mock_transport(),
    )
    return ProductionQueryTool(client)


def test_production_query_tool_filters_projects_and_traces_safe_spec() -> None:
    tool = _tool()
    spec = ProductionQuerySpec(
        filters=[QueryFilter(field="production_status", value="blocked")],
        select=["order_id", "production_status", "blocked_reason"],
        order_by=QueryOrder(field="estimated_finish_date", direction="desc"),
    )

    result = tool.query_orders(spec)

    assert result.data == [
        {
            "order_id": 10312,
            "production_status": "blocked",
            "blocked_reason": "Falta de capacidad",
        },
        {
            "order_id": 10252,
            "production_status": "blocked",
            "blocked_reason": "Falta de material",
        },
    ]
    assert result.tool_call.tool == "ProductionQueryTool"
    assert result.tool_call.action == "query_orders"
    assert result.tool_call.status == "success"
    assert result.tool_call.source == "Produccion"
    assert result.tool_call.args["entity"] == "production_orders"
    assert result.tool_call.output_summary == (
        "2 pedidos de produccion encontrados por DSL segura"
    )


def test_production_query_tool_uses_order_id_filters_without_exposing_raw_fields() -> None:
    tool = _tool()
    spec = ProductionQuerySpec(
        filters=[QueryFilter(field="order_id", operator="in", value=[99999, 10252])],
        select=["order_id", "production_status"],
    )

    result = tool.query_orders(spec)

    assert result.data == [{"order_id": 10252, "production_status": "blocked"}]
    assert "blocked_reason" not in result.data[0]
    assert "estimated_finish_date" not in result.data[0]


def test_production_query_tool_applies_limit() -> None:
    tool = _tool()
    spec = ProductionQuerySpec(
        filters=[QueryFilter(field="production_status", value="blocked")],
        select=["order_id"],
        limit=1,
    )

    result = tool.query_orders(spec)

    assert result.data == [{"order_id": 10252}]


def test_production_query_tool_returns_error_trace_for_api_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="service unavailable")

    tool = _tool(httpx.MockTransport(handler))
    spec = ProductionQuerySpec(select=["order_id"])

    result = tool.query_orders(spec)

    assert result.data is None
    assert result.tool_call.tool == "ProductionQueryTool"
    assert result.tool_call.action == "query_orders"
    assert result.tool_call.status == "error"
    assert result.tool_call.source == "Produccion"
    assert result.tool_call.error is not None
    assert "status 500" in result.tool_call.error
