from collections.abc import Callable
from decimal import Decimal
from time import perf_counter
from typing import Any

from app.core.tracing import ToolCallTrace, ToolResult
from app.erp.repositories import NorthwindRepository
from app.erp.schemas import OrderSummary
from app.tools.query_dsl import ERPQuerySpec, QueryFilter


class ERPQueryTool:
    name = "ERPQueryTool"

    def __init__(self, repository: NorthwindRepository) -> None:
        self._repository = repository

    def query_orders(self, spec: ERPQuerySpec) -> ToolResult:
        started_at = perf_counter()
        orders = self._repository.list_order_summaries()
        rows = [order.model_dump(mode="json") for order in orders]
        filtered_rows = _apply_filters(rows, spec.filters, _erp_filter_value)
        sorted_rows = _apply_order(filtered_rows, spec.order_by)
        data = [_project_row(row, spec.select) for row in sorted_rows[: spec.limit]]

        return ToolResult(
            data=data,
            tool_call=ToolCallTrace(
                tool=self.name,
                action="query_orders",
                args=spec.model_dump(mode="json"),
                status="success",
                output_summary=f"{len(data)} pedidos ERP encontrados por DSL segura",
                duration_ms=_duration_ms(started_at),
                source="ERP",
            ),
        )


def _apply_filters(
    rows: list[dict[str, Any]],
    filters: list[QueryFilter],
    value_getter: Callable[[dict[str, Any], str], Any],
) -> list[dict[str, Any]]:
    filtered_rows = rows
    for query_filter in filters:
        filtered_rows = [
            row
            for row in filtered_rows
            if _matches_filter(
                value_getter(row, query_filter.field),
                query_filter.operator,
                query_filter.value,
            )
        ]
    return filtered_rows


def _erp_filter_value(row: dict[str, Any], field: str) -> Any:
    if field == "year":
        return _order_date(row).year
    if field == "month":
        return _order_date(row).month
    return row.get(field)


def _order_date(row: dict[str, Any]) -> Any:
    return OrderSummary.model_validate(row).order_date


def _matches_filter(current_value: Any, operator: str, expected_value: Any) -> bool:
    if operator == "in":
        return current_value in expected_value
    return current_value == expected_value


def _apply_order(
    rows: list[dict[str, Any]],
    order_by: Any,
) -> list[dict[str, Any]]:
    if order_by is None:
        return sorted(rows, key=lambda row: row["order_id"])
    reverse = order_by.direction == "desc"
    return sorted(
        rows,
        key=lambda row: _order_value(row, order_by.field),
        reverse=reverse,
    )


def _order_value(row: dict[str, Any], field: str) -> Any:
    if field == "amount":
        return Decimal(row[field])
    return row[field]


def _project_row(row: dict[str, Any], select: list[str]) -> dict[str, Any]:
    return {field: row[field] for field in select}


def _duration_ms(started_at: float) -> int:
    return round((perf_counter() - started_at) * 1000)
