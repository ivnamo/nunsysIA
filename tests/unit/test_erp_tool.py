from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.erp.database import create_sqlite_connection, load_seed_sql
from app.erp.repositories import NorthwindRepository
from app.tools.erp_tool import (
    CustomerByOrderInput,
    ERPTool,
    OrderAmountInput,
    OrdersByMonthInput,
    PendingOrdersByCustomerInput,
)


@pytest.fixture()
def erp_tool() -> ERPTool:
    connection = create_sqlite_connection()
    load_seed_sql(connection)
    return ERPTool(NorthwindRepository(connection))


def test_erp_tool_get_pending_orders_returns_structured_data_and_trace(
    erp_tool: ERPTool,
) -> None:
    result = erp_tool.get_pending_orders_by_customer(
        PendingOrdersByCustomerInput(customer_id="ALFKI")
    )

    assert [order["order_id"] for order in result.data] == [10248, 10252]
    assert [order["amount"] for order in result.data] == ["440.00", "1863.00"]
    assert result.tool_call.tool == "ERPTool"
    assert result.tool_call.args == {"customer_id": "ALFKI"}
    assert result.tool_call.status == "success"
    assert result.tool_call.source == "ERP"
    assert result.tool_call.output_summary == "2 pedidos pendientes encontrados"


def test_erp_tool_get_customer_by_order_returns_customer(
    erp_tool: ERPTool,
) -> None:
    result = erp_tool.get_customer_by_order(CustomerByOrderInput(order_id=10301))

    assert result.data["customer_id"] == "ANATR"
    assert result.tool_call.status == "success"


def test_erp_tool_get_orders_by_month_returns_all_controlled_orders(
    erp_tool: ERPTool,
) -> None:
    result = erp_tool.get_orders_by_month(OrdersByMonthInput(year=2026, month=5))

    assert [order["order_id"] for order in result.data] == [10248, 10252, 10255, 10301, 10312]
    assert result.tool_call.output_summary == "5 pedidos encontrados para el mes"


def test_erp_tool_calculate_order_amount_returns_amount(
    erp_tool: ERPTool,
) -> None:
    result = erp_tool.calculate_order_amount(OrderAmountInput(order_id=10252))

    assert result.data == {"order_id": 10252, "amount": str(Decimal("1863.00"))}
    assert result.tool_call.action == "calculate_order_amount"
    assert result.tool_call.output_summary == "Importe calculado"


def test_erp_tool_rejects_invalid_order_amount_input() -> None:
    with pytest.raises(ValidationError):
        OrderAmountInput(order_id=0)
