import re
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
            action=call.action,
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


def sanitize_exception(exc: BaseException, max_length: int = 240) -> str:
    detail = f"{exc.__class__.__name__}: {exc}"
    return _short_text(_sanitize_error(detail), max_length=max_length) or exc.__class__.__name__


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

    if data.get("order_amounts") is not None:
        order_amounts = _as_list(data.get("order_amounts"))
        summary["order_amounts_count"] = len(order_amounts)
        summary["order_amount_order_ids"] = _order_ids(order_amounts)
        total = _amount_total(order_amounts)
        if total is not None:
            summary["economic_impact_total"] = total

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
            "citations": _rag_citations(chunks),
        }
        if rag.get("fallbacks"):
            summary["rag"]["fallbacks"] = [
                str(fallback) for fallback in rag.get("fallbacks", [])
            ]

    if data.get("memory"):
        memory = data["memory"]
        turns = _as_list(memory.get("turns"))
        memory_summary: dict[str, Any] = {
            "status": memory.get("status"),
            "turns_count": len(turns),
        }
        facts = memory.get("facts")
        if isinstance(facts, dict):
            if facts.get("customer_id"):
                memory_summary["customer_id"] = str(facts["customer_id"])
            order_ids = _memory_order_ids(facts.get("order_ids"))
            if order_ids:
                memory_summary["order_ids"] = order_ids
            documents = facts.get("documents")
            if isinstance(documents, list):
                memory_summary["documents"] = [str(document) for document in documents]
        summary["memory"] = memory_summary

    if data.get("replanning"):
        replans = _public_replan_events(data.get("replanning"))
        if replans:
            summary["replanning"] = {
                "replans_count": len(replans),
                "max_replans": replans[-1].get("max_replans"),
                "events": replans,
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
    value = re.sub(r"AIza[0-9A-Za-z_-]{20,}", _REDACTED, value)
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


def _rag_citations(chunks: list[Any]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    seen_chunk_ids: set[str] = set()
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue

        metadata = chunk.get("metadata") or {}
        if not isinstance(metadata, dict):
            continue

        filename = metadata.get("filename")
        page = metadata.get("page")
        chunk_id = metadata.get("chunk_id")
        score = chunk.get("score")
        if not filename or page is None or not chunk_id or score is None:
            continue

        chunk_id_text = str(chunk_id)
        if chunk_id_text in seen_chunk_ids:
            continue
        seen_chunk_ids.add(chunk_id_text)

        try:
            page_value = int(page)
            score_value = round(float(score), 4)
        except (TypeError, ValueError):
            continue

        citations.append(
            {
                "filename": str(filename),
                "page": page_value,
                "chunk_id": chunk_id_text,
                "score": score_value,
            }
        )
    return citations


def _memory_order_ids(values: Any) -> list[int]:
    order_ids: list[int] = []
    if not isinstance(values, list):
        return order_ids
    for value in values:
        try:
            order_id = int(value)
        except (TypeError, ValueError):
            continue
        if order_id not in order_ids:
            order_ids.append(order_id)
    return order_ids


def _amount_total(rows: list[Any]) -> str | None:
    total = 0.0
    found = False
    for row in rows:
        if not isinstance(row, dict) or row.get("amount") is None:
            continue
        try:
            total += float(row["amount"])
        except (TypeError, ValueError):
            continue
        found = True
    if not found:
        return None
    return f"{total:.2f}"


def _public_replan_events(events: Any) -> list[dict[str, Any]]:
    public_events: list[dict[str, Any]] = []
    for event in _as_list(events):
        if not isinstance(event, dict):
            continue
        public_event: dict[str, Any] = {}
        attempt = _bounded_int(event.get("attempt"), minimum=1, maximum=10)
        max_replans = _bounded_int(event.get("max_replans"), minimum=0, maximum=10)
        if attempt is not None:
            public_event["attempt"] = attempt
        decision = str(event.get("decision") or "")
        if decision in {"replan", "fail"}:
            public_event["decision"] = decision
        status = str(event.get("status") or "")
        if status:
            public_event["status"] = _short_text(status, max_length=80)
        failure_reason = sanitize_failure_reason(str(event.get("failure_reason") or ""))
        if failure_reason:
            public_event["failure_reason"] = failure_reason
        if max_replans is not None:
            public_event["max_replans"] = max_replans
        if public_event:
            public_events.append(public_event)
    return public_events


def _bounded_int(value: Any, minimum: int, maximum: int) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return max(minimum, min(maximum, number))
