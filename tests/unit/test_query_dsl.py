import pytest
from pydantic import ValidationError

from app.tools.query_dsl import (
    ERPQuerySpec,
    ProductionQuerySpec,
    QueryFilter,
    QueryOrder,
)


def test_erp_query_spec_accepts_allowlisted_fields_and_normalizes_customer() -> None:
    spec = ERPQuerySpec(
        filters=[QueryFilter(field="customer_id", value="alfki")],
        select=["order_id", "customer_id", "amount"],
        limit=10,
        order_by=QueryOrder(field="amount", direction="desc"),
    )

    assert spec.entity == "orders"
    assert spec.filters[0].value == "ALFKI"
    assert spec.select == ["order_id", "customer_id", "amount"]
    assert spec.limit == 10
    assert spec.order_by is not None
    assert spec.order_by.field == "amount"


def test_erp_query_spec_defaults_to_public_select_fields() -> None:
    spec = ERPQuerySpec()

    assert spec.select == [
        "order_id",
        "customer_id",
        "customer_name",
        "erp_status",
        "order_date",
        "amount",
    ]


def test_erp_query_spec_accepts_in_operator_for_order_ids() -> None:
    spec = ERPQuerySpec(
        filters=[QueryFilter(field="order_id", operator="in", value=[10248, 10252])]
    )

    assert spec.filters[0].value == [10248, 10252]


def test_erp_query_spec_rejects_non_allowlisted_entity() -> None:
    with pytest.raises(ValidationError):
        ERPQuerySpec(entity="customers")


def test_erp_query_spec_rejects_non_allowlisted_filter() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ERPQuerySpec(filters=[QueryFilter(field="raw_sql", value="1=1")])

    assert "filtro no permitido" in str(exc_info.value)


def test_erp_query_spec_rejects_internal_select_fields() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ERPQuerySpec(select=["order_id", "unit_price", "discount"])

    assert "select contiene campos no permitidos" in str(exc_info.value)


def test_erp_query_spec_rejects_limit_above_maximum() -> None:
    with pytest.raises(ValidationError):
        ERPQuerySpec(limit=51)


def test_erp_query_spec_rejects_unknown_operator() -> None:
    with pytest.raises(ValidationError):
        QueryFilter(field="customer_id", operator="contains", value="ALFKI")


def test_erp_query_spec_rejects_joins_and_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ERPQuerySpec(joins=["production_orders"])


def test_erp_query_spec_rejects_invalid_status_value() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ERPQuerySpec(filters=[QueryFilter(field="erp_status", value="blocked")])

    assert "valor no permitido" in str(exc_info.value)


def test_erp_query_spec_rejects_disallowed_order_field() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ERPQuerySpec(order_by=QueryOrder(field="raw_created_at"))

    assert "order_by no permitido" in str(exc_info.value)


def test_production_query_spec_accepts_allowlisted_fields() -> None:
    spec = ProductionQuerySpec(
        filters=[
            QueryFilter(field="production_status", value="blocked"),
            QueryFilter(field="order_id", operator="in", value=[10252, 10312]),
        ],
        select=["order_id", "production_status", "blocked_reason"],
        limit=20,
        order_by=QueryOrder(field="estimated_finish_date"),
    )

    assert spec.entity == "production_orders"
    assert spec.filters[0].value == "blocked"
    assert spec.filters[1].value == [10252, 10312]
    assert spec.select == ["order_id", "production_status", "blocked_reason"]


def test_production_query_spec_defaults_to_public_select_fields() -> None:
    spec = ProductionQuerySpec()

    assert spec.select == [
        "order_id",
        "production_status",
        "blocked_reason",
        "delay_reason",
        "estimated_finish_date",
    ]


def test_production_query_spec_rejects_erp_filter_fields() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ProductionQuerySpec(filters=[QueryFilter(field="customer_id", value="ALFKI")])

    assert "filtro no permitido" in str(exc_info.value)


def test_production_query_spec_rejects_internal_select_fields() -> None:
    with pytest.raises(ValidationError):
        ProductionQuerySpec(select=["order_id", "internal_http_url"])


def test_production_query_spec_rejects_invalid_status_value() -> None:
    with pytest.raises(ValidationError):
        ProductionQuerySpec(
            filters=[QueryFilter(field="production_status", value="pending")]
        )


def test_query_filter_in_operator_rejects_empty_lists() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ERPQuerySpec(filters=[QueryFilter(field="order_id", operator="in", value=[])])

    assert "operator in requiere una lista no vacia" in str(exc_info.value)


def test_query_filter_eq_operator_rejects_lists() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ProductionQuerySpec(
            filters=[QueryFilter(field="order_id", operator="eq", value=[10252])]
        )

    assert "operator eq no acepta listas" in str(exc_info.value)


def test_query_dsl_reports_domain_validation_errors() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ERPQuerySpec(filters=[QueryFilter(field="month", value="mayo")])

    assert "se esperaba entero positivo" in str(exc_info.value)
