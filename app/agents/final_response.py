from collections import Counter
from typing import Any

from app.agents.planner import ExecutionPlan
from app.agents.state import AgentState
from app.core.tracing import SourceName, ToolCallTrace
from app.schemas.query import QueryResponse, QueryStatus


class FinalResponseBuilder:
    def __call__(self, state: AgentState) -> AgentState:
        plan = ExecutionPlan.model_validate(state.get("plan") or {})
        status = _query_status(state.get("status", "failed"))
        answer = self._build_answer(plan, state, status)
        response = QueryResponse(
            answer=answer,
            sources=_sources(state.get("sources", [])),
            reasoning=state.get("reasoning", []),
            tool_calls=_tool_calls(state.get("tool_calls", [])),
            confidence=self._confidence(status),
            status=status,
            data=state.get("data", {}),
            failure_reason=state.get("failure_reason"),
        )
        return {
            **state,
            "final_answer": answer,
            "response": response,
        }

    def _build_answer(
        self,
        plan: ExecutionPlan,
        state: AgentState,
        status: QueryStatus,
    ) -> str:
        if status == "unsupported":
            return "La pregunta queda fuera del alcance de esta POC en su estado actual."

        if status == "insufficient_context":
            return "No hay contexto documental suficiente para responder sin inventar."

        if status in {"tool_error", "failed"}:
            return "No se pudo completar la consulta de forma fiable."

        data = state.get("data", {})
        if plan.intent == "erp_production" and data.get("production_orders"):
            return self._answer_blocked_orders(data)

        if data.get("period"):
            return self._answer_monthly_summary(data)

        if data.get("erp_orders") and data.get("production_by_order"):
            return self._answer_erp_with_production(data)

        if data.get("erp_orders"):
            return self._answer_erp_orders(data)

        if status == "partial_answer":
            return "La consulta produjo una respuesta parcial; revisa la traza para ver fuentes faltantes."

        return "La consulta se completo, pero no se encontraron datos relevantes."

    @staticmethod
    def _answer_erp_orders(data: dict[str, Any]) -> str:
        orders = data.get("erp_orders", [])
        if not orders:
            return "No se encontraron pedidos ERP con los criterios solicitados."

        customer = orders[0]["customer_id"]
        order_ids = ", ".join(str(order["order_id"]) for order in orders)
        return f"El cliente {customer} tiene {len(orders)} pedidos pendientes: {order_ids}."

    @staticmethod
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
                detail = production["production_status"]
                reason = production.get("blocked_reason") or production.get("delay_reason")
                if reason:
                    detail = f"{detail} ({reason})"
            else:
                detail = "sin informacion de produccion"

            lines.append(f"{order_id}: ERP {order['erp_status']}, produccion {detail}")

        customer = orders[0]["customer_id"]
        return f"Pedidos del cliente {customer}: " + "; ".join(lines) + "."

    @staticmethod
    def _answer_blocked_orders(data: dict[str, Any]) -> str:
        production_orders = data.get("production_orders", [])
        customers_by_order = data.get("customers_by_order", {})
        if not production_orders:
            return "No se encontraron pedidos bloqueados en produccion."

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
            reason = production_order.get("blocked_reason") or "sin motivo informado"
            lines.append(f"{order_id} ({customer_label}): {reason}")

        return "Pedidos bloqueados en produccion: " + "; ".join(lines) + "."

    @staticmethod
    def _answer_monthly_summary(data: dict[str, Any]) -> str:
        orders = data.get("erp_orders", [])
        production_by_order = data.get("production_by_order", {})
        period = data.get("period", {})
        statuses = Counter()

        for order in orders:
            production = production_by_order.get(order["order_id"])
            if production is None:
                production = production_by_order.get(str(order["order_id"]))
            statuses[production["production_status"] if production else "sin_datos"] += 1

        status_summary = ", ".join(
            f"{status}: {count}" for status, count in sorted(statuses.items())
        )
        return (
            f"En {period.get('year')}-{int(period.get('month')):02d} hay "
            f"{len(orders)} pedidos ERP. Estados de produccion: {status_summary}."
        )

    @staticmethod
    def _confidence(status: QueryStatus) -> float | None:
        if status == "completed":
            return 0.9
        if status in {"partial_answer", "insufficient_context"}:
            return 0.45
        return None


def _query_status(status: str) -> QueryStatus:
    allowed: set[QueryStatus] = {
        "completed",
        "partial_answer",
        "insufficient_context",
        "tool_error",
        "failed",
        "unsupported",
    }
    return status if status in allowed else "failed"


def _sources(values: list[str]) -> list[SourceName]:
    allowed = {"ERP", "Produccion", "Documentos", "Memoria"}
    return [value for value in values if value in allowed]


def _tool_calls(values: list[ToolCallTrace]) -> list[ToolCallTrace]:
    return [ToolCallTrace.model_validate(value) for value in values]
