from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


_PRODUCTION_STATUS_LABELS = {
    "blocked": "bloqueado",
    "delayed": "retrasado",
    "finished": "finalizado",
    "in_progress": "en curso",
}

_PENALTY_EVIDENCE_MARKERS = (
    "penaliz",
    "no aplic",
    "exclusion",
    "retras",
    "bloque",
    "falta de material",
    "falta de capacidad",
    "averia",
)


@dataclass(frozen=True)
class PenaltyAssessment:
    order_id: int | str
    customer: str
    status_detail: str
    decision: str

    def render(self) -> str:
        return (
            f"{self.order_id} ({self.customer}): "
            f"{self.status_detail}; {self.decision}"
        )


@dataclass(frozen=True)
class PenaltyPolicyResult:
    assessments: list[PenaltyAssessment]
    has_document_evidence: bool

    def answer(self) -> str:
        if not self.has_document_evidence:
            return (
                "No hay contexto documental suficiente para estimar "
                "penalizaciones sin inventar."
            )
        if not self.assessments:
            return "No se encontraron pedidos ERP para estimar penalizaciones."
        return (
            "Penalizaciones estimadas por pedido: "
            + "; ".join(assessment.render() for assessment in self.assessments)
            + "."
        )


def build_order_penalties_answer(data: dict[str, Any]) -> str:
    result = evaluate_order_penalties(
        orders=_as_list(data.get("erp_orders")),
        production_by_order=_as_dict(data.get("production_by_order")),
        rag_evidence=_as_dict(data.get("rag")),
    )
    return result.answer()


def evaluate_order_penalties(
    orders: list[dict[str, Any]],
    production_by_order: dict[Any, Any],
    rag_evidence: dict[str, Any] | None = None,
) -> PenaltyPolicyResult:
    has_document_evidence = _has_penalty_document_evidence(rag_evidence)
    if not has_document_evidence:
        return PenaltyPolicyResult(
            assessments=[],
            has_document_evidence=False,
        )

    assessments = [
        _build_assessment(order, production_by_order)
        for order in orders
        if isinstance(order, dict)
    ]
    return PenaltyPolicyResult(
        assessments=assessments,
        has_document_evidence=True,
    )


def _build_assessment(
    order: dict[str, Any],
    production_by_order: dict[Any, Any],
) -> PenaltyAssessment:
    order_id = order["order_id"]
    production = production_by_order.get(order_id)
    if production is None:
        production = production_by_order.get(str(order_id))
    if not isinstance(production, dict):
        production = None

    status = (
        _production_status_label(str(production.get("production_status") or ""))
        if production
        else "sin informacion de produccion"
    )
    reason = None
    if production:
        reason = production.get("blocked_reason") or production.get("delay_reason")
    status_detail = f"{status} ({reason})" if reason else status

    return PenaltyAssessment(
        order_id=order_id,
        customer=str(order.get("customer_name") or order.get("customer_id")),
        status_detail=status_detail,
        decision=_penalty_decision(order, production),
    )


def _penalty_decision(
    order: dict[str, Any],
    production: dict[str, Any] | None,
) -> str:
    if production is None:
        return "no calculable porque falta estado de produccion"

    status = str(production.get("production_status") or "")
    reason = str(production.get("blocked_reason") or production.get("delay_reason") or "")

    if status == "blocked" or _is_penalty_exclusion_reason(reason):
        return "sin penalizacion aplicable segun la evidencia actual por exclusion documental"

    required_date = _parse_date(order.get("required_date"))
    shipped_date = _parse_date(order.get("shipped_date"))

    if shipped_date and required_date:
        if shipped_date <= required_date:
            return "sin penalizacion aplicable porque consta enviado antes del plazo requerido"
        return (
            "requiere calcular dias laborables de retraso e imputabilidad logistica "
            "antes de aplicar 2%, 5% o 3% si era urgente"
        )

    if status == "delayed":
        return (
            "pendiente de fecha real de entrega e imputabilidad; no se puede aplicar "
            "penalizacion todavia"
        )

    return "sin penalizacion aplicable con la evidencia actual"


def _has_penalty_document_evidence(rag_evidence: dict[str, Any] | None) -> bool:
    if not rag_evidence or rag_evidence.get("status") != "completed":
        return False

    chunks = _as_list(rag_evidence.get("chunks"))
    if not chunks:
        return False

    evidence_text = " ".join(
        str(chunk.get("text") or "")
        for chunk in chunks
        if isinstance(chunk, dict)
    ).lower()
    return any(marker in evidence_text for marker in _PENALTY_EVIDENCE_MARKERS)


def _is_penalty_exclusion_reason(reason: str) -> bool:
    normalized = reason.lower()
    return any(
        marker in normalized
        for marker in (
            "falta de material",
            "falta de capacidad",
            "averia",
            "bloqueo",
            "cambio de prioridad",
        )
    )


def _production_status_label(status: str) -> str:
    return _PRODUCTION_STATUS_LABELS.get(status, status)


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> dict[Any, Any]:
    return value if isinstance(value, dict) else {}
