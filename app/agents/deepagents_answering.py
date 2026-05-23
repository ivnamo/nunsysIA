from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from app.schemas.query import QueryStatus


def normalized_answer(answer: str | None, status: QueryStatus) -> str:
    if status == "insufficient_context":
        return (
            "No he encontrado informacion en los documentos disponibles para "
            "responder a esa pregunta con fiabilidad."
        )
    if status == "needs_clarification":
        return (
            "Necesito contexto previo o que me indiques el cliente, pedido "
            "o periodo concreto para saber a que te refieres."
        )
    if answer and answer.strip():
        return answer.strip()
    if status == "tool_error":
        return "No se pudo completar la consulta por un error en una fuente."
    return "Deep Agents no genero una respuesta final usable para esta consulta."


def confidence(status: QueryStatus) -> float | None:
    if status == "completed":
        return 0.75
    if status == "insufficient_context":
        return 0.45
    if status == "needs_clarification":
        return 0.6
    return None


def with_deepagents_planning(
    public_data: dict[str, Any] | None,
    raw_data: dict[str, Any],
) -> dict[str, Any] | None:
    planning = raw_data.get("deepagents_planning")
    if not isinstance(planning, dict):
        return public_data
    summary = dict(public_data or {})
    summary["deepagents_planning"] = {
        "todos_used": bool(planning.get("todos_used")),
        "todo_tool_calls_count": int(planning.get("todo_tool_calls_count") or 0),
    }
    required_evidence = planning.get("required_evidence")
    if isinstance(required_evidence, list):
        summary["deepagents_planning"]["required_evidence"] = [
            str(item) for item in required_evidence
        ]
    subagents_available = planning.get("subagents_available")
    if isinstance(subagents_available, list):
        summary["deepagents_planning"]["subagents_available"] = [
            str(item) for item in subagents_available
        ]
    for key in (
        "answer_auditor_subagent_available",
        "answer_auditor_task_used",
        "deterministic_answer_gate_used",
    ):
        if key in planning:
            summary["deepagents_planning"][key] = bool(planning.get(key))
    if "answer_auditor_task_calls_count" in planning:
        summary["deepagents_planning"]["answer_auditor_task_calls_count"] = int(
            planning.get("answer_auditor_task_calls_count") or 0
        )
    return summary


def economic_impact_answer(data: dict[str, Any]) -> str:
    order_amounts = [
        amount
        for amount in data.get("order_amounts", [])
        if isinstance(amount, dict)
    ]
    rows = []
    total = Decimal("0.00")
    for amount in order_amounts:
        order_id = amount.get("order_id")
        value = _money(amount.get("amount"))
        if order_id is None or value is None:
            continue
        total += value
        rows.append([str(order_id), f"{value:.2f}"])

    if not rows:
        return "No se encontraron importes ERP para los pedidos referenciados."
    if len(rows) == 1:
        return (
            "Con los datos disponibles, el impacto economico del pedido "
            f"referenciado es {rows[0][0]}: {rows[0][1]}."
        )
    return (
        "Con los datos disponibles, el impacto economico total de los pedidos "
        f"referenciados es {total:.2f}.\n\n"
        + _markdown_table(["Pedido", "Importe"], rows)
    )


def production_status_answer(data: dict[str, Any]) -> str:
    requested_status = data.get("requested_production_status")
    production_orders = [
        order
        for order in data.get("production_orders", [])
        if isinstance(order, dict)
        and (
            not isinstance(requested_status, str)
            or order.get("production_status") == requested_status
        )
    ]
    if not production_orders:
        return "No se encontraron estados de produccion para los pedidos referenciados."

    customers_by_order = data.get("customers_by_order") or {}
    rows = []
    for order in production_orders:
        order_id = int(order["order_id"])
        customer = customers_by_order.get(order_id) or customers_by_order.get(
            str(order_id)
        )
        customer_label = _customer_label(customer)
        reason = (
            order.get("blocked_reason")
            or order.get("delay_reason")
            or "sin motivo informado"
        )
        rows.append(
            [
                str(order_id),
                customer_label,
                _production_status_label(str(order.get("production_status") or "")),
                str(reason),
            ]
        )

    return (
        "Estos son los estados de produccion de los pedidos referenciados:\n\n"
        + _markdown_table(["Pedido", "Cliente", "Estado", "Motivo"], rows)
    )


def erp_with_production_answer(data: dict[str, Any]) -> str:
    orders = [
        order
        for order in data.get("erp_orders", [])
        if isinstance(order, dict)
    ]
    production_by_order = data.get("production_by_order") or {}
    if not orders:
        return "No se encontraron pedidos ERP con los criterios solicitados."

    rows = []
    for order in orders:
        order_id = int(order["order_id"])
        production = production_by_order.get(order_id) or production_by_order.get(
            str(order_id)
        )
        if isinstance(production, dict):
            production_status = _production_status_label(
                str(production.get("production_status") or "")
            )
            observation = (
                production.get("blocked_reason")
                or production.get("delay_reason")
                or "sin bloqueo informado"
            )
        else:
            production_status = "sin informacion"
            observation = "sin estado de produccion disponible"
        rows.append(
            [
                str(order_id),
                _erp_status_label(str(order.get("erp_status") or "")),
                production_status,
                str(observation),
            ]
        )

    customer_id = str(orders[0].get("customer_id") or "cliente")
    return (
        f"El cliente {customer_id} tiene {len(orders)} pedidos pendientes:\n\n"
        + _markdown_table(
            ["Pedido", "Estado ERP", "Estado produccion", "Observacion"],
            rows,
        )
    )


def month_summary_answer(data: dict[str, Any]) -> str:
    orders = [
        order
        for order in data.get("erp_orders", [])
        if isinstance(order, dict)
    ]
    production_by_order = data.get("production_by_order") or {}
    period = data.get("period") or {}
    rows = []
    status_counts: dict[str, int] = {}
    for order in orders:
        order_id = int(order["order_id"])
        production = production_by_order.get(order_id) or production_by_order.get(
            str(order_id)
        )
        if isinstance(production, dict):
            status = _production_status_label(
                str(production.get("production_status") or "")
            )
        else:
            status = "sin informacion"
        status_counts[status] = status_counts.get(status, 0) + 1
        rows.append([str(order_id), _erp_status_label(str(order.get("erp_status") or "")), status])

    month = int(period.get("month") or 5)
    year = int(period.get("year") or 2026)
    summary = ", ".join(
        f"{status}: {count}" for status, count in sorted(status_counts.items())
    )
    return (
        f"En mayo de {year} hay {len(orders)} pedidos ERP. "
        f"Distribucion por estado de produccion: {summary}.\n\n"
        + _markdown_table(["Pedido", "Estado ERP", "Estado produccion"], rows)
        + f"\n\nPeriodo auditado: {year}-{month:02d}."
    )


def erp_orders_answer(data: dict[str, Any]) -> str:
    orders = [
        order
        for order in data.get("erp_orders", [])
        if isinstance(order, dict)
    ]
    if not orders:
        return "No se encontraron pedidos ERP con los criterios solicitados."

    rows = [
        [
            str(order.get("order_id")),
            _erp_status_label(str(order.get("erp_status") or "")),
        ]
        for order in orders
    ]
    customer_id = str(orders[0].get("customer_id") or "cliente")
    return (
        f"El cliente {customer_id} tiene {len(orders)} pedidos pendientes:\n\n"
        + _markdown_table(["Pedido", "Estado ERP"], rows)
    )


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def _money(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def _customer_label(customer: Any) -> str:
    if not isinstance(customer, dict):
        return "cliente ERP no resuelto"
    customer_id = customer.get("customer_id")
    customer_name = customer.get("company_name") or customer.get("customer_name")
    if customer_id and customer_name:
        return f"{customer_id} - {customer_name}"
    if customer_id:
        return str(customer_id)
    return "cliente ERP no resuelto"


def _production_status_label(status: str) -> str:
    labels = {
        "blocked": "bloqueado",
        "delayed": "retrasado",
        "finished": "finalizado",
        "in_progress": "en curso",
    }
    return labels.get(status, status or "sin informacion")


def _erp_status_label(status: str) -> str:
    labels = {
        "pending": "pendiente",
        "shipped": "enviado",
        "completed": "completado",
        "cancelled": "cancelado",
    }
    return labels.get(status, status or "sin informacion")
