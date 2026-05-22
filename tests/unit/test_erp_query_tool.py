import pytest
from pydantic import ValidationError

from app.erp.database import create_sqlite_connection, load_seed_sql
from app.erp.repositories import NorthwindRepository
from app.tools.erp_query_tool import ERPQueryTool
from app.tools.query_dsl import ERPQuerySpec, QueryFilter, QueryOrder


@pytest.fixture()
def erp_query_tool() -> ERPQueryTool:
    connection = create_sqlite_connection()
    load_seed_sql(connection)
    return ERPQueryTool(NorthwindRepository(connection))


def test_erp_query_tool_filters_projects_and_traces_safe_spec(
    erp_query_tool: ERPQueryTool,
) -> None:
    spec = ERPQuerySpec(
        filters=[QueryFilter(field="customer_id", value="alfki")],
        select=["order_id", "customer_id", "amount"],
        order_by=QueryOrder(field="amount", direction="desc"),
        limit=2,
    )

    result = erp_query_tool.query_orders(spec)

    assert result.data == [
        {"order_id": 10255, "customer_id": "ALFKI", "amount": "2490.00"},
        {"order_id": 10252, "customer_id": "ALFKI", "amount": "1863.00"},
    ]
    assert result.tool_call.tool == "ERPQueryTool"
    assert result.tool_call.action == "query_orders"
    assert result.tool_call.status == "success"
    assert result.tool_call.source == "ERP"
    assert result.tool_call.args["entity"] == "orders"
    assert result.tool_call.args["filters"][0]["value"] == "ALFKI"
    assert result.tool_call.output_summary == "2 pedidos ERP encontrados por DSL segura"


def test_erp_query_tool_filters_by_status_month_and_year(
    erp_query_tool: ERPQueryTool,
) -> None:
    spec = ERPQuerySpec(
        filters=[
            QueryFilter(field="erp_status", value="pending"),
            QueryFilter(field="year", value=2026),
            QueryFilter(field="month", value=5),
        ],
        select=["order_id", "erp_status"],
    )

    result = erp_query_tool.query_orders(spec)

    assert result.data == [
        {"order_id": 10248, "erp_status": "pending"},
        {"order_id": 10252, "erp_status": "pending"},
        {"order_id": 10301, "erp_status": "pending"},
        {"order_id": 10312, "erp_status": "pending"},
    ]


def test_erp_query_tool_filters_by_order_ids_with_limit(
    erp_query_tool: ERPQueryTool,
) -> None:
    spec = ERPQuerySpec(
        filters=[QueryFilter(field="order_id", operator="in", value=[10312, 10252])],
        select=["order_id", "customer_name"],
        limit=1,
    )

    result = erp_query_tool.query_orders(spec)

    assert result.data == [{"order_id": 10252, "customer_name": "Alfreds Futterkiste"}]


def test_erp_query_tool_does_not_expose_unselected_internal_fields(
    erp_query_tool: ERPQueryTool,
) -> None:
    spec = ERPQuerySpec(
        filters=[QueryFilter(field="order_id", value=10248)],
        select=["order_id"],
    )

    result = erp_query_tool.query_orders(spec)

    assert result.data == [{"order_id": 10248}]
    assert "required_date" not in result.data[0]
    assert "shipped_date" not in result.data[0]


def test_erp_query_tool_requires_valid_dsl_spec() -> None:
    with pytest.raises(ValidationError):
        ERPQuerySpec(select=["order_id", "unit_price"])
