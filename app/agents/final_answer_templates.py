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
    "shipped": "enviado",
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
        return (
            "No he encontrado informacion en los documentos disponibles para "
            "responder a esa pregunta con fiabilidad."
        )

    if status in {"tool_error", "failed"}:
        return (
            "No se pudo completar la consulta con fiabilidad. Revisa la "
            "disponibilidad de las fuentes y vuelve a intentarlo."
        )

    data = state.get("data", {})
    if status == "partial_answer":
        return _partial_answer(plan, state, data)

    if _is_order_penalty_plan(plan, state) and data.get("erp_orders") and data.get(
        "production_by_order"
    ):
        return build_order_penalties_answer(data)

    if data.get("rag"):
        return data["rag"]["answer"]

    if data.get("production_orders") and _is_affected_customer_query(plan, state):
        return _answer_affected_customers(data)

    if data.get("production_orders"):
        return _answer_production_orders(data)

    if data.get("erp_query_orders"):
        return _answer_erp_query_orders(data)

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

    return "La consulta se completo, pero no se encontraron datos relevantes para la pregunta."


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
    return (
        "Esta consulta no forma parte del alcance actual del sistema. Ahora mismo "
        "puedo ayudarte con pedidos, clientes, estados de produccion, bloqueos, "
        "importes y documentos asociados."
    )


def _clarification_answer(plan: ExecutionPlan) -> str:
    requirements_text = " ".join(plan.answer_requirements).lower()
    if "cliente concreto" in requirements_text:
        return (
            "Para consultar los pedidos pendientes necesito que me indiques un "
            "cliente, un numero de pedido o un periodo concreto."
        )
    if "contexto conversacional previo" in requirements_text:
        return (
            "Para resolver a que pedidos te refieres necesito que me indiques "
            "el cliente o los numeros de pedido concretos."
        )
    return "Necesito un dato mas para responder: cliente, pedido o periodo concreto."


def _answer_erp_orders(data: dict[str, Any]) -> str:
    orders = data.get("erp_orders", [])
    if not orders:
        return "No se encontraron pedidos ERP con los criterios solicitados."

    customer = orders[0]["customer_id"]
    order_label = _order_collection_label(orders)
    rows = [
        [str(order["order_id"]), _title(erp_status_label(order["erp_status"]))]
        for order in orders
    ]
    return (
        f"El cliente {customer} tiene {len(orders)} {order_label}:\n\n"
        + _markdown_table(["Pedido", "Estado ERP"], rows)
    )


def _answer_erp_with_production(data: dict[str, Any]) -> str:
    orders = data.get("erp_orders", [])
    production_by_order = data.get("production_by_order", {})
    if not orders:
        return "No se encontraron pedidos ERP con los criterios solicitados."

    rows = []
    attention_order_ids = []
    for order in orders:
        order_id = order["order_id"]
        production = production_by_order.get(order_id)
        if production is None:
            production = production_by_order.get(str(order_id))

        if production:
            raw_status = str(production["production_status"])
            production_state = _title(production_status_label(raw_status))
            reason = production.get("blocked_reason") or production.get("delay_reason")
            if reason:
                observation = str(reason)
            elif raw_status == "in_progress":
                observation = "Sin bloqueo informado"
            elif raw_status == "finished":
                observation = "Produccion finalizada"
            else:
                observation = "Sin motivo informado"
            if raw_status in {"blocked", "delayed"}:
                attention_order_ids.append(str(order_id))
        else:
            production_state = "Sin informacion"
            observation = "No hay estado de produccion disponible"

        erp_status = erp_status_label(order["erp_status"])
        rows.append(
            [
                str(order_id),
                _title(erp_status),
                production_state,
                observation,
            ]
        )

    customer = orders[0]["customer_id"]
    order_label = _order_collection_label(orders)
    answer = (
        f"El cliente {customer} tiene {len(orders)} {order_label}:\n\n"
        + _markdown_table(
            ["Pedido", "Estado ERP", "Estado produccion", "Observacion"],
            rows,
        )
    )
    if attention_order_ids:
        answer += (
            "\n\nEl punto de atencion es "
            f"{_orders_text(attention_order_ids)}, porque requiere seguimiento "
            "operativo desde produccion."
        )
    return answer


def _answer_production_orders(data: dict[str, Any]) -> str:
    production_orders = data.get("production_orders", [])
    customers_by_order = data.get("customers_by_order", {})
    if not production_orders:
        return "No se encontraron pedidos de produccion con los criterios solicitados."

    rows = []
    attention_order_ids = []
    for production_order in production_orders:
        order_id = production_order["order_id"]
        customer = customers_by_order.get(order_id)
        if customer is None:
            customer = customers_by_order.get(str(order_id))
        customer_label = (
            f"{customer['customer_id']} - {_customer_name(customer)}"
            if customer
            else "cliente no encontrado en ERP"
        )
        status = production_status_label(production_order["production_status"])
        reason = (
            production_order.get("blocked_reason")
            or production_order.get("delay_reason")
            or "sin motivo informado"
        )
        if production_order["production_status"] in {"blocked", "delayed"}:
            attention_order_ids.append(str(order_id))
        rows.append([str(order_id), customer_label, _title(status), str(reason)])

    raw_statuses = {order["production_status"] for order in production_orders}
    if raw_statuses == {"blocked"}:
        prefix = "Hay pedidos bloqueados en produccion"
    elif raw_statuses == {"delayed"}:
        prefix = "Hay pedidos retrasados en produccion"
    else:
        prefix = "Estos son los pedidos de produccion consultados"
    answer = (
        f"{prefix}:\n\n"
        + _markdown_table(
            ["Pedido", "Cliente", "Estado produccion", "Motivo"],
            rows,
        )
    )
    if attention_order_ids:
        answer += (
            "\n\nEl siguiente punto de atencion es "
            f"{_orders_text(attention_order_ids)}."
        )
    return answer


def _answer_affected_customers(data: dict[str, Any]) -> str:
    production_orders = data.get("production_orders", [])
    customers_by_order = data.get("customers_by_order", {})
    if not production_orders:
        return "No se encontraron pedidos de produccion con los criterios solicitados."

    rows = []
    customer_labels = set()
    unresolved = []
    for production_order in production_orders:
        order_id = production_order["order_id"]
        customer = customers_by_order.get(order_id)
        if customer is None:
            customer = customers_by_order.get(str(order_id))
        reason = (
            production_order.get("blocked_reason")
            or production_order.get("delay_reason")
            or "sin motivo informado"
        )
        if customer:
            customer_label = f"{customer['customer_id']} - {_customer_name(customer)}"
            customer_labels.add(customer_label)
            rows.append([customer_label, str(order_id), str(reason)])
        else:
            unresolved.append([str(order_id), "cliente ERP no resuelto", str(reason)])

    if unresolved:
        rows.extend(unresolved)

    if not rows:
        return "No se pudieron resolver clientes afectados con los datos disponibles."
    prefix = _affected_customers_prefix(production_orders)
    customer_count = len(customer_labels) if customer_labels else len(rows)
    return (
        f"{prefix}: {customer_count}.\n\n"
        + _markdown_table(["Cliente", "Pedido", "Motivo"], rows)
        + _affected_customers_attention(production_orders)
    )


def _answer_erp_query_orders(data: dict[str, Any]) -> str:
    orders = data.get("erp_query_orders", [])
    if not orders:
        return "No se encontraron pedidos ERP con los criterios solicitados."

    rows = []
    for order in orders:
        order_id = str(order["order_id"])
        customer_id = order.get("customer_id")
        customer_name = order.get("customer_name")
        if customer_id and customer_name:
            customer = f"{customer_id} - {customer_name}"
        elif customer_id:
            customer = str(customer_id)
        else:
            customer = "No informado"
        if order.get("erp_status"):
            erp_status = _title(erp_status_label(order["erp_status"]))
        else:
            erp_status = "No informado"
        if order.get("amount") is not None:
            amount = _money(order.get("amount"))
            if amount is not None:
                amount_text = f"{amount:.2f}"
            else:
                amount_text = "No informado"
        else:
            amount_text = "No informado"
        rows.append([order_id, customer, erp_status, amount_text])

    return (
        f"Se encontraron {len(rows)} pedidos ERP:\n\n"
        + _markdown_table(["Pedido", "Cliente", "Estado ERP", "Importe"], rows)
    )


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
        f"{len(orders)} pedidos ERP. Distribucion por estado de produccion: "
        f"{status_summary}."
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
        return f"Con los datos disponibles, el impacto economico del pedido referenciado es {lines[0]}."
    return (
        "Con los datos disponibles, el impacto economico total de los pedidos "
        f"referenciados es {total:.2f}.\n\n"
        + _markdown_table(
            ["Pedido", "Importe"],
            [line.split(": ", maxsplit=1) for line in lines],
        )
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


def _is_affected_customer_query(plan: ExecutionPlan, state: AgentState) -> bool:
    text = " ".join(
        [
            str(state.get("question") or ""),
            " ".join(plan.answer_requirements),
        ]
    ).lower()
    if "cliente" not in text and "clientes" not in text:
        return False
    return any(
        marker in text
        for marker in (
            "afectad",
            "cruza",
            "cruzar",
            "bloqueo",
            "bloqueos",
        )
    )


def _partial_answer(
    plan: ExecutionPlan,
    state: AgentState,
    data: dict[str, Any],
) -> str:
    missing_sources = _missing_sources(plan, state)
    available_parts = []

    erp_orders = data.get("erp_orders") or data.get("erp_query_orders") or []
    if erp_orders:
        available_parts.append(
            f"ERP devolvio {len(erp_orders)} pedido(s): {_join_order_ids(erp_orders)}"
        )

    production_orders = data.get("production_orders") or []
    if production_orders:
        available_parts.append(
            "Produccion devolvio "
            f"{len(production_orders)} pedido(s): {_join_order_ids(production_orders)}"
        )

    rag = data.get("rag") or {}
    if rag.get("status") == "completed":
        chunks_count = len(rag.get("chunks") or [])
        available_parts.append(
            f"Documentos devolvio {chunks_count} chunk(s) relevante(s)"
        )

    if not available_parts:
        available_text = "hay trazabilidad de ejecucion, pero faltan datos de negocio"
    else:
        available_text = "; ".join(available_parts)

    if missing_sources:
        missing_text = ", ".join(missing_sources)
        return (
            "Con los datos disponibles, la respuesta queda parcial: "
            f"{available_text}. Falta {missing_text} para completarla con "
            "fiabilidad."
        )
    failure_reason = str(state.get("failure_reason") or "faltan datos verificables")
    return f"Con los datos disponibles, la respuesta queda parcial: {available_text}. {failure_reason}"


def _affected_customers_prefix(production_orders: list[dict[str, Any]]) -> str:
    statuses = {
        order.get("production_status")
        for order in production_orders
        if isinstance(order, dict)
    }
    if statuses == {"blocked"}:
        return "Hay clientes afectados por bloqueos de produccion"
    if statuses == {"delayed"}:
        return "Hay clientes afectados por pedidos retrasados de produccion"
    return "Hay clientes afectados por incidencias de produccion"


def _missing_sources(plan: ExecutionPlan, state: AgentState) -> list[str]:
    sources = set(state.get("sources", []))
    return [source for source in plan.expected_sources if source not in sources]


def _join_order_ids(rows: list[dict[str, Any]]) -> str:
    order_ids = [
        str(row["order_id"])
        for row in rows
        if isinstance(row, dict) and row.get("order_id") is not None
    ]
    return ", ".join(order_ids) if order_ids else "sin IDs de pedido"


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(str(value) for value in row) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def _title(value: str) -> str:
    return value[:1].upper() + value[1:] if value else value


def _order_collection_label(orders: list[dict[str, Any]]) -> str:
    if all(order.get("erp_status") == "pending" for order in orders):
        return "pedidos pendientes"
    return "pedidos consultados"


def _orders_text(order_ids: list[str]) -> str:
    if len(order_ids) == 1:
        return f"el pedido {order_ids[0]}"
    return "los pedidos " + ", ".join(order_ids)


def _affected_customers_attention(production_orders: list[dict[str, Any]]) -> str:
    statuses = {
        order.get("production_status")
        for order in production_orders
        if isinstance(order, dict)
    }
    if statuses == {"blocked"}:
        detail = "resolver estos bloqueos"
    elif statuses == {"delayed"}:
        detail = "gestionar estos retrasos"
    else:
        detail = "resolver estos bloqueos o incidencias"
    return f"\n\nEl siguiente punto de atencion es {detail} desde produccion."


def _money(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _customer_name(customer: dict[str, Any]) -> str:
    return str(
        customer.get("company_name")
        or customer.get("customer_name")
        or customer.get("customer_id")
        or "cliente no informado"
    )
