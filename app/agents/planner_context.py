import re
from typing import Any

from app.agents.planner_models import ExecutionPlan, PlanStep
from app.agents.planner_utils import (
    extract_customer_id,
    normalize_order_ids,
    strip_accents,
)


def build_contextual_rule_based_plan(
    question: str,
    normalized: str,
    history: list[dict[str, Any]],
) -> ExecutionPlan | None:
    if not history:
        return None

    normalized_ascii = strip_accents(normalized)
    if not _looks_like_contextual_followup(normalized_ascii):
        return None

    facts = _conversation_facts(history)
    customer_id = facts.get("customer_id")
    order_ids = facts.get("order_ids", [])
    memory_step = PlanStep(
        step_id=1,
        tool="MemoryTool",
        action="recall",
        args={"query": question, "max_turns": 5},
    )

    if _is_economic_impact_followup(normalized_ascii) and order_ids:
        return ExecutionPlan(
            intent="erp",
            steps=[
                memory_step,
                PlanStep(
                    step_id=2,
                    tool="ERPTool",
                    action="calculate_order_amount",
                    args={"order_ids": order_ids},
                ),
            ],
            expected_sources=["Memoria", "ERP"],
            answer_requirements=[
                "Resolver la referencia con memoria y calcular importes ERP de los pedidos referenciados.",
            ],
        )

    if "penaliz" in normalized_ascii and order_ids:
        return ExecutionPlan(
            intent="mixed",
            steps=[
                memory_step,
                PlanStep(
                    step_id=2,
                    tool="ERPTool",
                    action="get_orders_by_month",
                    args={"year": 2026, "month": 5},
                ),
                PlanStep(
                    step_id=3,
                    tool="ProductionAPITool",
                    action="get_status_for_erp_orders",
                ),
                PlanStep(
                    step_id=4,
                    tool="DocumentRAGTool",
                    action="query",
                    args={
                        "query": (
                            "penalizaciones por retrasos no aplicacion bloqueo "
                            "produccion falta material falta capacidad averia linea"
                        ),
                        "top_k": 5,
                    },
                ),
            ],
            expected_sources=["Memoria", "ERP", "Produccion", "Documentos"],
            answer_requirements=[
                "Resolver la referencia con memoria y responder con fuentes actuales.",
            ],
        )

    if "bloquead" in normalized_ascii and order_ids:
        return ExecutionPlan(
            intent="erp_production",
            steps=[
                memory_step,
                PlanStep(
                    step_id=2,
                    tool="ProductionAPITool",
                    action="get_status_for_order_ids",
                    args={"order_ids": order_ids, "status": "blocked"},
                ),
                PlanStep(
                    step_id=3,
                    tool="ERPTool",
                    action="get_customers_for_production_orders",
                ),
            ],
            expected_sources=["Memoria", "Produccion", "ERP"],
            answer_requirements=[
                "Responder solo con los pedidos referenciados que esten bloqueados.",
            ],
        )

    if any(
        marker in normalized_ascii
        for marker in ("estado", "producci", "bloquead", "retrasad")
    ) and customer_id:
        return ExecutionPlan(
            intent="erp_production",
            steps=[
                memory_step,
                PlanStep(
                    step_id=2,
                    tool="ERPTool",
                    action="get_pending_orders_by_customer",
                    args={"customer_id": customer_id},
                ),
                PlanStep(
                    step_id=3,
                    tool="ProductionAPITool",
                    action="get_status_for_erp_orders",
                ),
            ],
            expected_sources=["Memoria", "ERP", "Produccion"],
            answer_requirements=[
                "Usar memoria solo para resolver el cliente y consultar datos actuales.",
            ],
        )

    if "pendient" in normalized_ascii and customer_id:
        return ExecutionPlan(
            intent="erp",
            steps=[
                memory_step,
                PlanStep(
                    step_id=2,
                    tool="ERPTool",
                    action="get_pending_orders_by_customer",
                    args={"customer_id": customer_id},
                ),
            ],
            expected_sources=["Memoria", "ERP"],
            answer_requirements=[
                "Usar memoria solo para resolver el cliente y consultar ERP.",
            ],
        )

    if _is_memory_summary_query(normalized_ascii):
        return ExecutionPlan(
            intent="conversation",
            steps=[memory_step],
            expected_sources=["Memoria"],
            answer_requirements=["Resumir de forma breve el historial disponible."],
        )

    return None


def build_contextual_unsupported_plan(
    normalized: str,
    history: list[dict[str, Any]],
) -> ExecutionPlan | None:
    normalized_ascii = strip_accents(normalized)
    if history or not _looks_like_contextual_followup(normalized_ascii):
        return None

    return ExecutionPlan(
        intent="unsupported",
        steps=[],
        expected_sources=[],
        answer_requirements=[
            "Explicar que la pregunta necesita contexto conversacional previo y pedir que se concrete el cliente o los pedidos.",
        ],
    )


def missing_customer_plan() -> ExecutionPlan:
    return ExecutionPlan(
        intent="unsupported",
        steps=[],
        expected_sources=[],
        answer_requirements=[
            "Explicar que la pregunta necesita un cliente concreto o contexto conversacional previo para consultar pedidos pendientes.",
        ],
    )


def _conversation_facts(history: list[dict[str, Any]]) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    latest_order_ids: list[int] = []

    for turn in reversed(history):
        turn_facts = turn.get("facts") if isinstance(turn, dict) else None
        if isinstance(turn_facts, dict):
            customer_id = turn_facts.get("customer_id")
            if (
                "customer_id" not in facts
                and isinstance(customer_id, str)
                and re.fullmatch(r"[A-Z]{5}", customer_id)
            ):
                facts["customer_id"] = customer_id

            if not latest_order_ids:
                latest_order_ids = normalize_order_ids(turn_facts.get("order_ids"))

        if "customer_id" not in facts:
            for field in ("question", "answer"):
                value = turn.get(field) if isinstance(turn, dict) else None
                if isinstance(value, str):
                    customer_id = extract_customer_id(value)
                    if customer_id:
                        facts["customer_id"] = customer_id
                        break

    if latest_order_ids:
        facts["order_ids"] = latest_order_ids
    return facts


def _looks_like_contextual_followup(normalized_ascii: str) -> bool:
    text = normalized_ascii.strip(" ?!\u00a1\u00bf")
    return text.startswith(("y ", "cuales", "que pasa", "entonces")) or any(
        marker in text
        for marker in (
            " esos",
            " esas",
            " ellos",
            " ellas",
            " anteriores",
            " anterior",
            " lo anterior",
            " la anterior",
            " ultima",
            " ultimo",
        )
    )


def _is_memory_summary_query(normalized_ascii: str) -> bool:
    return any(
        marker in normalized_ascii
        for marker in ("resume lo anterior", "resumen de lo anterior", "que hemos visto")
    )


def _is_economic_impact_followup(normalized_ascii: str) -> bool:
    return any(
        marker in normalized_ascii
        for marker in (
            "impacto economico",
            "importe",
            "importes",
            "coste",
            "costes",
            "costo",
            "costos",
            "valor",
            "economico",
        )
    )
