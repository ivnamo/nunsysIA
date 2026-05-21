from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation
from typing import Any

from app.agents.penalty_policy import build_order_penalties_answer
from app.agents.planner import ExecutionPlan
from app.agents.state import AgentState
from app.schemas.query import QueryStatus


_ERP_STATUS_LABELS = {
    "pending": "pendiente",
    "completed": "completado",
    "cancelled": "cancelado",
}

_PRODUCTION_STATUS_LABELS = {
    "blocked": "bloqueado",
    "delayed": "retrasado",
    "finished": "finalizado",
    "in_progress": "en curso",
}


def build_deterministic_answer(
    plan: ExecutionPlan,
    state: AgentState,
    status: QueryStatus,
) -> str:
    if status == "unsupported":
        return _unsupported_answer(plan)

    if status == "needs_clarification":
        return _clarification_answer(plan)

    if status == "insufficient_context":
        return "No hay contexto documental suficiente para responder sin inventar."

    if status in {"tool_error", "failed"}:
        return "No se pudo completar la consulta de forma fiable."

    data = state.get("data", {})
    if _is_order_penalty_plan(plan, state) and data.get("erp_orders") and data.get(
        "production_by_order"
    ):
        return build_order_penalties_answer(data)

    if data.get("rag"):
        return data["rag"]["answer"]

    if data.get("production_orders"):
        return _answer_production_orders(data)

    if data.get("period"):
        return _answer_monthly_summary(data)

    if data.get("order_amounts"):
        return _answer_economic_impact(data)

    if data.get("erp_orders") and data.get("production_by_order"):
        return _answer_erp_with_production(data)

    if data.get("erp_orders"):
        return _answer_erp_orders(data)

    if data.get("memory"):
        return _answer_memory(data)

    if status == "partial_answer":
        return "La consulta produjo una respuesta parcial; revisa la traza para ver fuentes faltantes."

    return "La consulta se completo, pero no se encontraron datos relevantes."


def confidence_for_status(status: QueryStatus) -> float | None:
    if status == "completed":
        return 0.9
    if status in {"partial_answer", "insufficient_context"}:
        return 0.45
    if status == "needs_clarification":
        return 0.6
    return None


def erp_status_label(status: str) -> str:
    return _ERP_STATUS_LABELS.get(status, status)


def production_status_label(status: str) -> str:
    return _PRODUCTION_STATUS_LABELS.get(status, status)


def translated_status_text(text: str) -> str:
    translated = []
    for raw, label in _PRODUCTION_STATUS_LABELS.items():
        if raw in text:
            translated.append(label)
    for raw, label in _ERP_STATUS_LABELS.items():
        if raw in text:
            translated.append(label)
    return " ".join(translated)


def _unsupported_answer(plan: ExecutionPlan) -> str:
    return "La pregunta queda fuera del alcance de esta POC en su estado actual."


def _clarification_answer(plan: ExecutionPlan) -> str:
    requirements_text = " ".join(plan.answer_requirements).lower()
    if "cliente concreto" in requirements_text:
        return (
            "Para consultar pedidos pendientes necesito un cliente concreto "
            "o contexto conversacional previo. "
            "Indica el cliente o los pedidos concretos."
        )
    if "contexto conversacional previo" in requirements_text:
        return (
            "Necesito contexto conversacional previo para resolver a que "
            "pedidos te refieres. Indica el cliente o los pedidos concretos."
        )
    return "Necesito un dato mas para responder sin inventar. Indica el cliente, pedido o periodo concreto."


def _answer_erp_orders(data: dict[str, Any]) -> str:
    orders = data.get("erp_orders", [])
    if not orders:
        return "No se encontraron pedidos ERP con los criterios solicitados."

    customer = orders[0]["customer_id"]
    order_ids = ", ".join(str(order["order_id"]) for order in orders)
    return f"El cliente {customer} tiene {len(orders)} pedidos pendientes: {order_ids}."


def _answer_erp_with_production(data: dict[str, Any]) -> str:
    orders = data.get("erp_orders", [])
    production_by_order = data.get("production_by_order", {})
    if not orders:
        return "No se encontraron pedidos ERP con los criterios solicitados."

    lines = []
    for order in orders:
        order_id = order["order_id"]
        production = production_by_order.get(order_id)
        if production is None:
            production = production_by_order.get(str(order_id))

        if production:
            detail = production_status_label(production["production_status"])
            reason = production.get("blocked_reason") or production.get("delay_reason")
            if reason:
                detail = f"{detail} ({reason})"
        else:
            detail = "sin informacion de produccion"

        erp_status = erp_status_label(order["erp_status"])
        lines.append(f"{order_id}: ERP {erp_status}, produccion {detail}")

    customer = orders[0]["customer_id"]
    return f"Pedidos del cliente {customer}: " + "; ".join(lines) + "."


def _answer_production_orders(data: dict[str, Any]) -> str:
    production_orders = data.get("production_orders", [])
    customers_by_order = data.get("customers_by_order", {})
    if not production_orders:
        return "No se encontraron pedidos de produccion con los criterios solicitados."

    lines = []
    for production_order in production_orders:
        order_id = production_order["order_id"]
        customer = customers_by_order.get(order_id)
        if customer is None:
            customer = customers_by_order.get(str(order_id))
        customer_label = (
            f"{customer['customer_id']} - {customer['company_name']}"
            if customer
            else "cliente no encontrado en ERP"
        )
        status = production_status_label(production_order["production_status"])
        reason = (
            production_order.get("blocked_reason")
            or production_order.get("delay_reason")
            or "sin motivo informado"
        )
        lines.append(f"{order_id} ({customer_label}): {status}, {reason}")

    raw_statuses = {order["production_status"] for order in production_orders}
    if raw_statuses == {"blocked"}:
        prefix = "Pedidos bloqueados en produccion"
    elif raw_statuses == {"delayed"}:
        prefix = "Pedidos retrasados en produccion"
    else:
        prefix = "Pedidos de produccion"
    return prefix + ": " + "; ".join(lines) + "."


def _answer_monthly_summary(data: dict[str, Any]) -> str:
    orders = data.get("erp_orders", [])
    production_by_order = data.get("production_by_order", {})
    period = data.get("period", {})
    statuses = Counter()

    for order in orders:
        production = production_by_order.get(order["order_id"])
        if production is None:
            production = production_by_order.get(str(order["order_id"]))
        status = (
            production_status_label(production["production_status"])
            if production
            else "sin datos"
        )
        statuses[status] += 1

    status_summary = ", ".join(
        f"{status}: {count}" for status, count in sorted(statuses.items())
    )
    return (
        f"En {period.get('year')}-{int(period.get('month')):02d} hay "
        f"{len(orders)} pedidos ERP. Estados de produccion: {status_summary}."
    )


def _answer_economic_impact(data: dict[str, Any]) -> str:
    order_amounts = data.get("order_amounts", [])
    if not order_amounts:
        return "No se encontraron importes ERP para los pedidos referenciados."

    total = Decimal("0.00")
    lines = []
    for order_amount in order_amounts:
        order_id = order_amount.get("order_id")
        amount = _money(order_amount.get("amount"))
        if order_id is None or amount is None:
            continue
        total += amount
        lines.append(f"{order_id}: {amount:.2f}")

    if not lines:
        return "No se encontraron importes ERP para los pedidos referenciados."

    if len(lines) == 1:
        return f"Impacto economico del pedido referenciado: {lines[0]}."
    return (
        "Impacto economico de los pedidos referenciados: "
        + "; ".join(lines)
        + f". Total: {total:.2f}."
    )


def _answer_memory(data: dict[str, Any]) -> str:
    memory = data.get("memory") or {}
    turns = memory.get("turns") or []
    if not turns:
        return "No hay historial conversacional previo para resumir."

    summaries = []
    for turn in turns[-3:]:
        question = str(turn.get("question") or "")
        answer = str(turn.get("answer") or "")
        if question and answer:
            summaries.append(f"Pregunta: {question} Respuesta: {answer}")

    if not summaries:
        return "Hay historial conversacional, pero no contiene respuestas resumibles."
    return "Resumen del historial reciente: " + " | ".join(summaries)


def _is_order_penalty_plan(plan: ExecutionPlan, state: AgentState) -> bool:
    if plan.intent != "mixed":
        return False
    question = str(state.get("question") or "").lower()
    return "penaliz" in question and ("pedido" in question or "order" in question)


def _money(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return None
