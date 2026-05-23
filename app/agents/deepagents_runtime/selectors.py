from __future__ import annotations

import re
from typing import Any

from app.agents.deepagents_policy import (
    KNOWN_CUSTOMER_IDS as _KNOWN_CUSTOMER_IDS,
)
from app.agents.deepagents_policy import contains_any as _contains_any
from app.agents.deepagents_policy import normalize_text as _normalize_text
from app.tools.query_dsl import QueryFilter


def _cache_key(action: str, args: dict[str, Any]) -> tuple[Any, ...]:
    return (action, _freeze(args))


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((key, _freeze(item)) for key, item in value.items()))
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _unique_ints(values: list[int]) -> list[int]:
    normalized = []
    for value in values:
        item = int(value)
        if item not in normalized:
            normalized.append(item)
    return normalized


def _order_ids(rows: list[dict[str, Any]]) -> list[int]:
    order_ids = []
    for row in rows:
        if not isinstance(row, dict) or row.get("order_id") is None:
            continue
        order_id = int(row["order_id"])
        if order_id not in order_ids:
            order_ids.append(order_id)
    return order_ids


def _order_ids_from_memory_data(memory: Any) -> list[int]:
    if not isinstance(memory, dict):
        return []
    facts = memory.get("facts")
    if not isinstance(facts, dict):
        return []
    return _unique_ints(facts.get("order_ids") or [])


def _extract_customer_id(text: str) -> str | None:
    for match in re.findall(r"\b[A-Z]{5}\b", text):
        if match in _KNOWN_CUSTOMER_IDS:
            return match
    normalized = _normalize_text(text)
    for customer_id in sorted(_KNOWN_CUSTOMER_IDS):
        if customer_id.lower() in normalized:
            return customer_id
    return None


def _requested_production_status(text: str) -> str | None:
    normalized = _normalize_text(text)
    if "bloque" in normalized:
        return "blocked"
    if "retras" in normalized:
        return "delayed"
    if "progreso" in normalized or "curso" in normalized:
        return "in_progress"
    if "finaliz" in normalized or "termin" in normalized:
        return "finished"
    return None


def _is_month_summary(text: str) -> bool:
    normalized = _normalize_text(text)
    return _contains_any(normalized, ("este mes", "mes", "mayo")) and _contains_any(
        normalized,
        ("pedido", "pedidos", "estado"),
    )


def _merge_rows(left: Any, right: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for collection in (left, right):
        if not isinstance(collection, list):
            continue
        for row in collection:
            if not isinstance(row, dict):
                continue
            order_id = row.get("order_id")
            if order_id is None:
                rows.append(row)
                continue
            normalized_order_id = int(order_id)
            if normalized_order_id in seen:
                continue
            seen.add(normalized_order_id)
            rows.append(row)
    return rows


def _erp_filters(
    customer_id: str | None,
    order_ids: list[int] | None,
    erp_status: str | None,
    year: int | None,
    month: int | None,
) -> list[QueryFilter]:
    filters: list[QueryFilter] = []
    if customer_id:
        filters.append(QueryFilter(field="customer_id", value=customer_id))
    if order_ids:
        filters.append(QueryFilter(field="order_id", operator="in", value=order_ids))
    if erp_status:
        filters.append(QueryFilter(field="erp_status", value=erp_status))
    if year is not None:
        filters.append(QueryFilter(field="year", value=year))
    if month is not None:
        filters.append(QueryFilter(field="month", value=month))
    return filters


def _production_filters(
    order_ids: list[int] | None,
    production_status: str | None,
) -> list[QueryFilter]:
    filters: list[QueryFilter] = []
    if order_ids:
        filters.append(QueryFilter(field="order_id", operator="in", value=order_ids))
    if production_status:
        filters.append(QueryFilter(field="production_status", value=production_status))
    return filters
