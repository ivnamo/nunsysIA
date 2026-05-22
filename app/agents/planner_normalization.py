from typing import Any

from app.agents.planner_models import ExecutionPlan, PlanStep
from app.agents.planner_utils import (
    bounded_float,
    bounded_int,
    extract_customer_id,
    normalize_order_ids,
)
from app.tools.query_dsl import ERPQuerySpec, ProductionQuerySpec


_ALLOWED_TOOL_ACTIONS: dict[str, set[str]] = {
    "ERPTool": {
        "get_pending_orders_by_customer",
        "get_orders_by_month",
        "get_customers_for_production_orders",
        "calculate_order_amount",
    },
    "ProductionAPITool": {
        "list_orders",
        "get_status_for_erp_orders",
        "get_status_for_order_ids",
    },
    "ERPQueryTool": {"query_orders"},
    "ProductionQueryTool": {"query_orders"},
    "DocumentRAGTool": {"query"},
    "MemoryTool": {"recall"},
}
_ALLOWED_SOURCES = {"ERP", "Produccion", "Documentos", "Memoria"}
_PRODUCTION_STATUSES = {"in_progress", "blocked", "delayed", "finished"}
_ALLOWED_JOIN_FROM = {"erp_orders", "production_orders"}


def normalize_plan(plan: ExecutionPlan, question: str) -> ExecutionPlan | None:
    if plan.intent in {"unsupported", "clarification"}:
        default_requirement = (
            _default_clarification_requirement(question)
            if plan.intent == "clarification"
            else "Explicar que la pregunta esta fuera del alcance actual."
        )
        return ExecutionPlan(
            intent=plan.intent,
            steps=[],
            expected_sources=[],
            answer_requirements=plan.answer_requirements or [default_requirement],
        )

    normalized_steps = []
    for index, step in enumerate(plan.steps, start=1):
        if not _is_allowed_step(step):
            return None
        normalized_args = _normalize_step_args(step, question)
        if normalized_args is None:
            return None
        normalized_steps.append(
            PlanStep(
                step_id=index,
                tool=step.tool,
                action=step.action,
                args=normalized_args,
                required=step.required,
            )
        )

    if not normalized_steps:
        return None

    expected_sources = _expected_sources_for_steps(normalized_steps)
    requested_sources = [
        source for source in plan.expected_sources if source in _ALLOWED_SOURCES
    ]
    for source in requested_sources:
        if source not in expected_sources:
            expected_sources.append(source)

    return ExecutionPlan(
        intent=plan.intent,
        steps=normalized_steps,
        expected_sources=expected_sources,
        answer_requirements=plan.answer_requirements,
    )


def _is_allowed_step(step: PlanStep) -> bool:
    return step.action in _ALLOWED_TOOL_ACTIONS.get(step.tool, set())


def _normalize_step_args(step: PlanStep, question: str) -> dict[str, Any] | None:
    if step.tool == "ERPTool" and step.action == "get_pending_orders_by_customer":
        customer_id = str(step.args.get("customer_id") or "").upper()
        if not _is_customer_id(customer_id):
            customer_id = extract_customer_id(question)
        if customer_id is None:
            return None
        return {"customer_id": customer_id}

    if step.tool == "ERPTool" and step.action == "get_orders_by_month":
        return {
            "year": bounded_int(
                step.args.get("year"),
                default=2026,
                minimum=2000,
                maximum=2100,
            ),
            "month": bounded_int(
                step.args.get("month"),
                default=5,
                minimum=1,
                maximum=12,
            ),
        }

    if step.tool == "ERPTool" and step.action == "calculate_order_amount":
        order_ids = normalize_order_ids(step.args.get("order_ids"))
        if order_ids:
            return {"order_ids": order_ids}
        return {
            "order_id": bounded_int(
                step.args.get("order_id"),
                default=0,
                minimum=0,
                maximum=999999,
            )
        }

    if step.tool == "ProductionAPITool" and step.action == "list_orders":
        status = step.args.get("status")
        return {"status": status if status in _PRODUCTION_STATUSES else None}

    if step.tool == "ProductionAPITool" and step.action == "get_status_for_order_ids":
        status = step.args.get("status")
        return {
            "order_ids": normalize_order_ids(step.args.get("order_ids")),
            "status": status if status in _PRODUCTION_STATUSES else None,
        }

    if step.tool == "ERPQueryTool" and step.action == "query_orders":
        return _normalize_query_step_args(
            step.args,
            spec_model=ERPQuerySpec,
        )

    if step.tool == "ProductionQueryTool" and step.action == "query_orders":
        return _normalize_query_step_args(
            step.args,
            spec_model=ProductionQuerySpec,
        )

    if step.tool == "DocumentRAGTool" and step.action == "query":
        args: dict[str, Any] = {
            "query": str(step.args.get("query") or question),
            "top_k": bounded_int(
                step.args.get("top_k"),
                default=5,
                minimum=1,
                maximum=10,
            ),
        }
        if "min_score" in step.args:
            args["min_score"] = bounded_float(
                step.args.get("min_score"),
                default=0.2,
                minimum=0,
                maximum=1,
            )
        return args

    if step.tool == "MemoryTool" and step.action == "recall":
        return {
            "query": str(step.args.get("query") or question),
            "max_turns": bounded_int(
                step.args.get("max_turns"),
                default=5,
                minimum=1,
                maximum=5,
            ),
        }

    return {}


def _expected_sources_for_steps(steps: list[PlanStep]) -> list[str]:
    sources = []
    for step in steps:
        source = _source_for_tool(step.tool)
        if source and source not in sources:
            sources.append(source)
    return sources


def _source_for_tool(tool: str) -> str | None:
    return {
        "ERPTool": "ERP",
        "ProductionAPITool": "Produccion",
        "ERPQueryTool": "ERP",
        "ProductionQueryTool": "Produccion",
        "DocumentRAGTool": "Documentos",
        "MemoryTool": "Memoria",
    }.get(tool)


def _is_customer_id(value: str) -> bool:
    return len(value) == 5 and all("A" <= character <= "Z" for character in value)


def _default_clarification_requirement(question: str) -> str:
    normalized = question.lower()
    if "pedido" in normalized or "pendient" in normalized:
        return (
            "Pedir un cliente concreto o pedidos concretos para consultar "
            "pedidos sin inventar."
        )
    return "Pedir el dato concreto que falta para continuar."


def _normalize_query_step_args(
    args: dict[str, Any],
    spec_model: type[ERPQuerySpec] | type[ProductionQuerySpec],
) -> dict[str, Any] | None:
    raw_spec = args.get("spec") if isinstance(args.get("spec"), dict) else args
    try:
        spec = spec_model.model_validate(raw_spec)
    except Exception:
        return None

    normalized_args: dict[str, Any] = {"spec": spec.model_dump(mode="json")}
    join_from = args.get("join_from")
    if join_from is not None:
        if join_from not in _ALLOWED_JOIN_FROM:
            return None
        normalized_args["join_from"] = join_from
    return normalized_args
