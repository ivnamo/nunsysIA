from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.agents.deepagents_policy import ToolPolicy
from app.schemas.query import QueryResponse


@dataclass(frozen=True)
class VerificationResult:
    status: str
    issues: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def repair_prompt(self) -> str:
        if self.passed:
            return ""
        issue_lines = "\n".join(f"- {issue}" for issue in self.issues)
        return (
            "La respuesta anterior no cumple la verificacion de evidencia.\n"
            f"{issue_lines}\n"
            "Repara la respuesta ejecutando las tools necesarias. No inventes "
            "datos. Devuelve una respuesta con answer, sources y reasoning "
            "basada solo en las tool calls disponibles."
        )


def required_evidence(policy: ToolPolicy) -> list[str]:
    required: list[str] = []
    if policy.needs_memory:
        required.append("Memoria")
    if policy.needs_erp or policy.needs_customer_orders or policy.needs_economic_impact:
        required.append("ERP")
    if policy.needs_production or policy.needs_blocked_cross:
        required.append("Produccion")
    if policy.needs_documents or policy.needs_penalty:
        required.append("Documentos")
    if policy.needs_penalty:
        required.extend(["ERP", "Produccion"])
    return _dedupe(required)


def verify_response(
    response: QueryResponse,
    *,
    policy: ToolPolicy,
    data: dict[str, Any],
) -> VerificationResult:
    if response.status in {"needs_clarification", "insufficient_context"}:
        return VerificationResult(status="passed")

    issues: list[str] = []
    required_sources = required_evidence(policy)
    sources = set(response.sources or [])
    tool_sources = {call.source for call in response.tool_calls}
    tool_names = {call.tool for call in response.tool_calls}
    all_sources = sources | tool_sources

    if response.status == "completed":
        if not response.answer.strip():
            issues.append("answer vacio en respuesta completed")
        if _looks_unusable_answer(response.answer):
            issues.append("answer no usable o generico pese a status completed")
        if not response.sources:
            issues.append("sources vacio en respuesta completed")
        if not response.reasoning:
            issues.append("reasoning vacio en respuesta completed")
        if not response.tool_calls:
            issues.append("tool_calls vacio en respuesta completed")

    for source in required_sources:
        if source not in all_sources:
            issues.append(f"falta evidencia obligatoria de {source}")

    if "ERP" in required_sources and not _has_tool(tool_names, "ERP"):
        issues.append("la consulta requiere ERP pero no hay ERPTool/ERPQueryTool")
    if "Produccion" in required_sources and not _has_tool(tool_names, "Production"):
        issues.append(
            "la consulta requiere produccion pero no hay ProductionAPITool/ProductionQueryTool"
        )
    if "Documentos" in required_sources:
        if "DocumentRAGTool" not in tool_names:
            issues.append("la consulta documental no uso DocumentRAGTool")
        elif not _rag_has_citations(data):
            issues.append("RAG no aporta citas documentales auditables")
    if "Memoria" in required_sources and "MemoryTool" not in tool_names:
        issues.append("la consulta conversacional no uso MemoryTool")

    unsupported_order_ids = _unsupported_answer_order_ids(response.answer, data)
    if unsupported_order_ids:
        issues.append(
            "la respuesta menciona order_id sin evidencia: "
            + ", ".join(str(order_id) for order_id in unsupported_order_ids)
        )
    if policy.needs_penalty:
        missing_penalty_order_ids = _missing_supported_order_ids(response.answer, data)
        if missing_penalty_order_ids:
            issues.append(
                "la respuesta de penalizaciones omite pedidos con evidencia: "
                + ", ".join(str(order_id) for order_id in missing_penalty_order_ids)
            )

    if issues:
        return VerificationResult(status="failed", issues=tuple(_dedupe(issues)))
    return VerificationResult(status="passed")


def _has_tool(tool_names: set[str], prefix: str) -> bool:
    return any(tool_name.startswith(prefix) for tool_name in tool_names)


def _rag_has_citations(data: dict[str, Any]) -> bool:
    rag = data.get("rag")
    if not isinstance(rag, dict):
        return False
    if rag.get("status") == "insufficient_context":
        return True
    chunks = rag.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        return False
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        metadata = chunk.get("metadata")
        if not isinstance(metadata, dict):
            continue
        if metadata.get("filename") and metadata.get("page") and metadata.get("chunk_id"):
            return True
    return False


def _unsupported_answer_order_ids(answer: str, data: dict[str, Any]) -> list[int]:
    mentioned = _order_ids_from_text(answer)
    if not mentioned:
        return []
    supported = set()
    for key in (
        "erp_orders",
        "erp_query_orders",
        "production_orders",
        "order_amounts",
    ):
        supported.update(_order_ids_from_rows(data.get(key)))
    production_by_order = data.get("production_by_order")
    if isinstance(production_by_order, dict):
        supported.update(_safe_int(key) for key in production_by_order)
    supported.discard(None)
    if not supported:
        return []
    return [order_id for order_id in mentioned if order_id not in supported]


def _missing_supported_order_ids(answer: str, data: dict[str, Any]) -> list[int]:
    mentioned = set(_order_ids_from_text(answer))
    supported = set()
    for key in ("erp_orders", "production_orders", "order_amounts"):
        supported.update(_order_ids_from_rows(data.get(key)))
    return [order_id for order_id in sorted(supported) if order_id not in mentioned]


def _looks_unusable_answer(answer: str) -> bool:
    lowered = (answer or "").lower()
    return any(
        marker in lowered
        for marker in (
            "respuesta no determinista",
            "sin consultas para inspeccion",
            "deep agents no genero",
            "no se pudo generar una respuesta final",
            "pregunta:",
            "conversation_id:",
            "usa solo las tools",
        )
    )


def _order_ids_from_text(value: str) -> list[int]:
    order_ids: list[int] = []
    for raw in re.findall(r"\b\d{5,}\b", value or ""):
        order_id = int(raw)
        if order_id not in order_ids:
            order_ids.append(order_id)
    return order_ids


def _order_ids_from_rows(value: Any) -> set[int]:
    rows = value if isinstance(value, list) else []
    order_ids: set[int] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        order_id = _safe_int(row.get("order_id"))
        if order_id is not None:
            order_ids.add(order_id)
    return order_ids


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result
