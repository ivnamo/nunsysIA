from typing import Any

from app.core.tracing import ToolCallTrace


_REDACTED = "[redacted]"
_SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "connection_string",
    "database_url",
    "dsn",
    "password",
    "secret",
    "token",
}
_SENSITIVE_VALUE_MARKERS = (
    "bearer ",
    "postgres://",
    "postgresql://",
    "postgresql+",
    "mysql://",
    "sqlite://",
)


def sanitize_tool_calls(tool_calls: list[ToolCallTrace]) -> list[ToolCallTrace]:
    return [
        ToolCallTrace(
            tool=call.tool,
            args=_sanitize_value(call.args),
            status=call.status,
            output_summary=_short_text(call.output_summary),
            error=_short_text(_sanitize_error(call.error)),
            duration_ms=call.duration_ms,
            source=call.source,
        )
        for call in tool_calls
    ]


def sanitize_reasoning(reasoning: list[str]) -> list[str]:
    return [
        text
        for text in (_short_text(step, max_length=240) for step in reasoning)
        if text
    ]


def sanitize_failure_reason(reason: str | None) -> str | None:
    return _short_text(_sanitize_error(reason), max_length=240)


def build_public_data_summary(data: dict[str, Any]) -> dict[str, Any] | None:
    summary: dict[str, Any] = {}

    if data.get("erp_orders") is not None:
        erp_orders = _as_list(data.get("erp_orders"))
        summary["erp_orders_count"] = len(erp_orders)
        summary["erp_order_ids"] = _order_ids(erp_orders)

    if data.get("production_orders") is not None:
        production_orders = _as_list(data.get("production_orders"))
        summary["production_orders_count"] = len(production_orders)
        summary["production_order_ids"] = _order_ids(production_orders)

    if data.get("production_by_order") is not None:
        production_by_order = data.get("production_by_order") or {}
        summary["production_statuses_count"] = len(production_by_order)

    if data.get("customers_by_order") is not None:
        customers_by_order = data.get("customers_by_order") or {}
        summary["customers_resolved_count"] = len(
            [customer for customer in customers_by_order.values() if customer]
        )

    if data.get("period"):
        summary["period"] = data["period"]

    if data.get("rag"):
        rag = data["rag"]
        chunks = _as_list(rag.get("chunks"))
        summary["rag"] = {
            "status": rag.get("status"),
            "chunks_count": len(chunks),
            "documents": _document_names(chunks),
        }

    return summary or None


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _REDACTED if _is_sensitive_key(key) else _sanitize_value(inner_value)
            for key, inner_value in value.items()
        }

    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]

    if isinstance(value, tuple):
        return [_sanitize_value(item) for item in value]

    if isinstance(value, str):
        return _short_text(_sanitize_string(value), max_length=160)

    return value


def _sanitize_error(error: str | None) -> str | None:
    if not error:
        return None
    return _sanitize_string(error)


def _sanitize_string(value: str) -> str:
    lower = value.lower()
    if any(marker in lower for marker in _SENSITIVE_VALUE_MARKERS):
        return _REDACTED
    return value


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return normalized in _SENSITIVE_KEYS or any(
        sensitive_key in normalized for sensitive_key in _SENSITIVE_KEYS
    )


def _short_text(value: str | None, max_length: int = 200) -> str | None:
    if value is None:
        return None

    normalized = " ".join(value.split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3].rstrip() + "..."


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _order_ids(rows: list[Any]) -> list[int]:
    order_ids: list[int] = []
    for row in rows:
        if isinstance(row, dict) and row.get("order_id") is not None:
            order_ids.append(int(row["order_id"]))
    return order_ids


def _document_names(chunks: list[Any]) -> list[str]:
    names = set()
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        metadata = chunk.get("metadata") or {}
        filename = metadata.get("filename")
        if filename:
            names.add(str(filename))
    return sorted(names)
