from decimal import Decimal

import pytest

from app.erp.database import create_sqlite_connection, load_seed_sql
from app.erp.repositories import NorthwindRepository


@pytest.fixture()
def repository() -> NorthwindRepository:
    connection = create_sqlite_connection()
    load_seed_sql(connection)
    return NorthwindRepository(connection)


def test_get_customer_returns_controlled_northwind_customer(
    repository: NorthwindRepository,
) -> None:
    customer = repository.get_customer("ALFKI")

    assert customer is not None
    assert customer.customer_id == "ALFKI"
    assert customer.company_name == "Alfreds Futterkiste"


def test_get_pending_orders_by_customer_returns_expected_orders(
    repository: NorthwindRepository,
) -> None:
    orders = repository.get_pending_orders_by_customer("ALFKI")

    assert [order.order_id for order in orders] == [10248, 10252]
    assert [order.amount for order in orders] == [
        Decimal("440.00"),
        Decimal("1863.00"),
    ]
    assert all(order.erp_status == "pending" for order in orders)


def test_get_pending_orders_by_unknown_customer_returns_empty_list(
    repository: NorthwindRepository,
) -> None:
    assert repository.get_pending_orders_by_customer("UNKNOWN") == []


def test_get_customer_by_order_maps_order_to_customer(
    repository: NorthwindRepository,
) -> None:
    customer = repository.get_customer_by_order(10301)

    assert customer is not None
    assert customer.customer_id == "ANATR"


def test_get_orders_by_month_returns_controlled_may_orders(
    repository: NorthwindRepository,
) -> None:
    orders = repository.get_orders_by_month(2026, 5)

    assert [order.order_id for order in orders] == [10248, 10252, 10255, 10301, 10312]
    assert sum(order.amount for order in orders) == Decimal("6923.00")


def test_calculate_order_amount_returns_expected_amount(
    repository: NorthwindRepository,
) -> None:
    assert repository.calculate_order_amount(10252) == Decimal("1863.00")


def test_calculate_order_amount_returns_none_for_unknown_order(
    repository: NorthwindRepository,
) -> None:
    assert repository.calculate_order_amount(99999) is None


def test_get_order_lines_returns_product_details(
    repository: NorthwindRepository,
) -> None:
    lines = repository.get_order_lines(10248)

    assert [line.product_name for line in lines] == [
        "Queso Cabrales",
        "Singaporean Hokkien Fried Mee",
    ]
    assert [line.quantity for line in lines] == [10, 30]
