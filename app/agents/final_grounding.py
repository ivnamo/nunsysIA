from __future__ import annotations

import re
from typing import Any

from app.agents.final_answer_templates import (
    erp_status_label,
    production_status_label,
    translated_status_text,
)
from app.agents.planner import ExecutionPlan
from app.agents.state import AgentState
from app.core.tracing import ToolCallTrace
from app.core.traceability import sanitize_reasoning, sanitize_tool_calls


def sanitize_tool_call_traces(values: list[ToolCallTrace]) -> list[ToolCallTrace]:
    return sanitize_tool_calls([ToolCallTrace.model_validate(value) for value in values])


def build_final_evidence_payload(
    question: str,
    plan: ExecutionPlan,
    state: AgentState,
    public_summary: dict[str, Any],
    deterministic_answer: str,
) -> dict[str, Any]:
    data = state.get("data", {})
    return {
        "question": question,
        "intent": plan.intent,
        "answer_requirements": plan.answer_requirements,
        "sources": state.get("sources", []),
        "reasoning_visible": sanitize_reasoning(state.get("reasoning", [])),
        "tool_calls": [
            call.model_dump(mode="json")
            for call in sanitize_tool_call_traces(state.get("tool_calls", []))
        ],
        "public_summary": public_summary,
        "evidence": _normalized_evidence(data),
        "safe_fallback_answer": deterministic_answer,
    }


def unsupported_critical_facts(answer: str, evidence_text: str) -> list[str]:
    allowed_text = evidence_text + " " + translated_status_text(evidence_text)
    allowed = _critical_fact_sets(allowed_text)
    actual = _critical_fact_sets(answer)
    unsupported = []

    for number in sorted(actual["numbers"] - allowed["numbers"]):
        unsupported.append(f"numero no soportado: {number}")
    for identifier in sorted(actual["identifiers"] - allowed["identifiers"]):
        unsupported.append(f"identificador no soportado: {identifier}")
    for filename in sorted(actual["filenames"] - allowed["filenames"]):
        unsupported.append(f"documento no soportado: {filename}")
    for status in sorted(actual["statuses"] - allowed["statuses"]):
        unsupported.append(f"estado no soportado: {status}")
    for proper_name in sorted(actual["proper_names"] - allowed["proper_names"]):
        unsupported.append(f"nombre no soportado: {proper_name}")

    return unsupported


def _normalized_evidence(data: dict[str, Any]) -> dict[str, Any]:
    evidence: dict[str, Any] = {}

    if data.get("erp_orders") is not None:
        evidence["erp_orders"] = [
            _normalize_erp_order(order)
            for order in _as_list(data.get("erp_orders"))
        ]

    if data.get("production_orders") is not None:
        evidence["production_orders"] = [
            _normalize_production_order(order)
            for order in _as_list(data.get("production_orders"))
        ]

    if data.get("production_by_order") is not None:
        production_by_order = _as_dict(data.get("production_by_order"))
        evidence["production_by_order"] = [
            _normalize_production_order(production)
            for _, production in _sorted_mapping_items(production_by_order)
            if isinstance(production, dict)
        ]

    if data.get("order_amounts") is not None:
        evidence["order_amounts"] = [
            _clean_mapping(order_amount)
            for order_amount in _as_list(data.get("order_amounts"))
            if isinstance(order_amount, dict)
        ]

    if data.get("customers_by_order") is not None:
        customers_by_order = _as_dict(data.get("customers_by_order"))
        evidence["customers_by_order"] = [
            {
                "order_id": _coerce_int(order_id),
                "customer": _clean_mapping(customer),
            }
            for order_id, customer in _sorted_mapping_items(customers_by_order)
            if isinstance(customer, dict)
        ]

    if data.get("period"):
        evidence["period"] = _clean_mapping(data["period"])

    if data.get("rag"):
        evidence["rag"] = _normalize_rag_evidence(_as_dict(data.get("rag")))

    if data.get("memory"):
        memory = _as_dict(data.get("memory"))
        evidence["memory"] = {
            "status": memory.get("status"),
            "facts": _clean_mapping(memory.get("facts") or {}),
            "turns_count": len(_as_list(memory.get("turns"))),
        }

    return evidence


def _normalize_erp_order(order: Any) -> dict[str, Any]:
    values = _clean_mapping(order)
    status = values.get("erp_status")
    if isinstance(status, str):
        values["erp_status_label"] = erp_status_label(status)
    return values


def _normalize_production_order(order: Any) -> dict[str, Any]:
    values = _clean_mapping(order)
    status = values.get("production_status")
    if isinstance(status, str):
        values["production_status_label"] = production_status_label(status)
    reason = values.get("blocked_reason") or values.get("delay_reason")
    if reason:
        values["reason"] = reason
    return values


def _normalize_rag_evidence(rag: dict[str, Any]) -> dict[str, Any]:
    chunks = []
    for index, chunk in enumerate(_as_list(rag.get("chunks")), start=1):
        if not isinstance(chunk, dict):
            continue
        metadata = _as_dict(chunk.get("metadata"))
        chunks.append(
            {
                "evidence_id": f"D{index}",
                "filename": metadata.get("filename"),
                "page": metadata.get("page"),
                "chunk_id": metadata.get("chunk_id"),
                "score": _round_score(chunk.get("score")),
                "text": str(chunk.get("text") or ""),
            }
        )
    return {
        "status": rag.get("status"),
        "chunks": chunks,
    }


def _critical_fact_sets(text: str) -> dict[str, set[str]]:
    return {
        "numbers": _number_facts(text),
        "identifiers": _identifier_facts(text),
        "filenames": {
            value.lower()
            for value in re.findall(r"[\w.-]+\.pdf\b", text, flags=re.IGNORECASE)
        },
        "statuses": _status_facts(text),
        "proper_names": _proper_name_facts(text),
    }


def _number_facts(text: str) -> set[str]:
    return {
        _normalize_number(match)
        for match in re.findall(r"\b\d+(?:[.,]\d+)?%?\b", text)
    }


def _normalize_number(value: str) -> str:
    suffix = "%" if value.endswith("%") else ""
    number = value[:-1] if suffix else value
    if re.fullmatch(r"\d+", number):
        return str(int(number)) + suffix
    return number.replace(",", ".") + suffix


def _identifier_facts(text: str) -> set[str]:
    allowed_common = {"API", "ERP", "ID", "LLM", "PDF", "POC", "RAG", "SLA", "JSON"}
    identifiers = set(re.findall(r"\b[A-Z]{2,}\d*\b", text))
    return {identifier for identifier in identifiers if identifier not in allowed_common}


def _proper_name_facts(text: str) -> set[str]:
    phrases = re.findall(
        r"\b[A-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00d1]"
        r"[a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1]+"
        r"(?:\s+[A-Z\u00c1\u00c9\u00cd\u00d3\u00da\u00d1]"
        r"[a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1]+)+\b",
        text,
    )
    return {phrase.lower() for phrase in phrases}


def _status_facts(text: str) -> set[str]:
    normalized = text.lower()
    status_groups = {
        "pending": ("pending", "pendiente", "pendientes"),
        "in_progress": ("in_progress", "en curso"),
        "blocked": (
            "blocked",
            "bloqueado",
            "bloqueada",
            "bloqueados",
            "bloqueadas",
            "bloqueo",
            "bloqueos",
        ),
        "delayed": (
            "delayed",
            "retrasado",
            "retrasada",
            "retrasados",
            "retrasadas",
            "retraso",
            "retrasos",
        ),
        "finished": (
            "finished",
            "finalizado",
            "finalizada",
            "finalizados",
            "finalizadas",
        ),
    }
    return {
        status
        for status, forms in status_groups.items()
        if any(form in normalized for form in forms)
    }


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _clean_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): _clean_value(inner_value)
        for key, inner_value in value.items()
        if inner_value is not None
    }


def _clean_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _clean_mapping(value)
    if isinstance(value, list):
        return [_clean_value(item) for item in value]
    return value


def _sorted_mapping_items(value: dict[Any, Any]) -> list[tuple[Any, Any]]:
    return sorted(value.items(), key=lambda item: str(item[0]))


def _coerce_int(value: Any) -> int | str:
    try:
        return int(value)
    except (TypeError, ValueError):
        return str(value)


def _round_score(value: Any) -> float | None:
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None
