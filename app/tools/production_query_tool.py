from collections.abc import Callable
from time import perf_counter
from typing import Any

from app.core.tracing import ToolCallTrace, ToolResult
from app.production.client import ProductionAPIClient, ProductionAPIError
from app.production.schemas import ProductionOrder, ProductionStatus
from app.tools.query_dsl import ProductionQuerySpec, QueryFilter


class ProductionQueryTool:
    name = "ProductionQueryTool"

    def __init__(self, client: ProductionAPIClient) -> None:
        self._client = client

    def query_orders(self, spec: ProductionQuerySpec) -> ToolResult:
        started_at = perf_counter()
        try:
            orders = self._load_orders(spec)
        except ProductionAPIError as exc:
            return ToolResult(
                data=None,
                tool_call=ToolCallTrace(
                    tool=self.name,
                    action="query_orders",
                    args=spec.model_dump(mode="json"),
                    status="error",
                    output_summary="Error al consultar API de produccion con DSL segura",
                    error=str(exc),
                    duration_ms=_duration_ms(started_at),
                    source="Produccion",
                ),
            )

        rows = [order.model_dump(mode="json") for order in orders]
        filtered_rows = _apply_filters(rows, spec.filters, lambda row, field: row[field])
        sorted_rows = _apply_order(filtered_rows, spec.order_by)
        data = [_project_row(row, spec.select) for row in sorted_rows[: spec.limit]]

        return ToolResult(
            data=data,
            tool_call=ToolCallTrace(
                tool=self.name,
                action="query_orders",
                args=spec.model_dump(mode="json"),
                status="success",
                output_summary=(
                    f"{len(data)} pedidos de produccion encontrados por DSL segura"
                ),
                duration_ms=_duration_ms(started_at),
                source="Produccion",
            ),
        )

    def _load_orders(self, spec: ProductionQuerySpec) -> list[ProductionOrder]:
        order_ids = _order_ids_from_filters(spec.filters)
        if order_ids:
            return [
                order
                for order_id in order_ids
                if (order := self._client.get_order(order_id)) is not None
            ]

        status = _single_status_filter(spec.filters)
        return self._client.list_orders(status=status)


def _order_ids_from_filters(filters: list[QueryFilter]) -> list[int]:
    order_ids = []
    for query_filter in filters:
        if query_filter.field != "order_id":
            continue
        values = (
            query_filter.value
            if query_filter.operator == "in"
            else [query_filter.value]
        )
        for value in values:
            if value not in order_ids:
                order_ids.append(value)
    return order_ids


def _single_status_filter(filters: list[QueryFilter]) -> ProductionStatus | None:
    for query_filter in filters:
        if query_filter.field != "production_status" or query_filter.operator != "eq":
            continue
        return query_filter.value
    return None


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
    return sorted(rows, key=lambda row: row[order_by.field], reverse=reverse)


def _project_row(row: dict[str, Any], select: list[str]) -> dict[str, Any]:
    return {field: row[field] for field in select}


def _duration_ms(started_at: float) -> int:
    return round((perf_counter() - started_at) * 1000)
