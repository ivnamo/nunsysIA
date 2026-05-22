from typing import Any

from app.agents.planner import ExecutionPlan, PlanStep
from app.agents.state import AgentState
from app.core.tracing import SourceName, ToolCallTrace, ToolResult
from app.tools.erp_tool import (
    CustomerByOrderInput,
    ERPTool,
    OrderAmountInput,
    OrdersByMonthInput,
    PendingOrdersByCustomerInput,
)
from app.tools.memory_tool import MemoryRecallInput, MemoryTool
from app.tools.production_tool import (
    ProductionAPITool,
    ProductionOrderInput,
    ProductionOrdersByIdsInput,
    ProductionOrdersInput,
)
from app.tools.rag_tool import DocumentRAGInput, DocumentRAGTool


class ReasonerExecutorAgent:
    def __init__(
        self,
        erp_tool: ERPTool,
        production_tool: ProductionAPITool,
        rag_tool: DocumentRAGTool | None = None,
        memory_tool: MemoryTool | None = None,
    ) -> None:
        self._erp_tool = erp_tool
        self._production_tool = production_tool
        self._rag_tool = rag_tool
        self._memory_tool = memory_tool or MemoryTool()

    def __call__(self, state: AgentState) -> AgentState:
        plan = ExecutionPlan.model_validate(state.get("plan") or {})
        execution = _ExecutionContext()

        for step in plan.steps:
            self._execute_step(step, execution, state)

        return {
            **state,
            "tool_results": execution.tool_results,
            "tool_calls": execution.tool_calls,
            "sources": execution.sources,
            "reasoning": execution.reasoning,
            "fallbacks": _merge_fallbacks(
                state.get("fallbacks", []),
                execution.fallbacks,
            ),
            "data": execution.data,
            "status": "executing",
        }

    def _execute_step(
        self,
        step: PlanStep,
        execution: "_ExecutionContext",
        state: AgentState,
    ) -> None:
        if step.tool == "MemoryTool":
            self._execute_memory_step(step, execution, state)
            return

        if step.tool == "ERPTool":
            self._execute_erp_step(step, execution)
            return

        if step.tool == "ProductionAPITool":
            self._execute_production_step(step, execution)
            return

        if step.tool == "DocumentRAGTool":
            self._execute_rag_step(step, execution)
            return

        execution.add_skipped(
            tool=step.tool,
            action=step.action,
            source="Memoria",
            args=step.args,
            summary=f"{step.tool} no esta implementada en esta fase",
        )

    def _execute_memory_step(
        self,
        step: PlanStep,
        execution: "_ExecutionContext",
        state: AgentState,
    ) -> None:
        if step.action == "recall":
            try:
                max_turns = int(step.args.get("max_turns") or 5)
            except (TypeError, ValueError):
                max_turns = 5
            result = self._memory_tool.recall(
                MemoryRecallInput(
                    query=str(step.args.get("query") or state.get("question") or ""),
                    conversation_history=state.get("conversation_history", []),
                    max_turns=max_turns,
                )
            )
            execution.data["memory"] = result.data
            execution.add_result(
                result,
                "Consulta memoria conversacional",
                action=step.action,
            )
            return

        execution.add_skipped(
            tool="MemoryTool",
            action=step.action,
            source="Memoria",
            args=step.args,
            summary=f"Accion de memoria no soportada: {step.action}",
        )

    def _execute_erp_step(self, step: PlanStep, execution: "_ExecutionContext") -> None:
        if step.action == "get_pending_orders_by_customer":
            result = self._erp_tool.get_pending_orders_by_customer(
                PendingOrdersByCustomerInput.model_validate(step.args)
            )
            execution.data["erp_orders"] = result.data
            execution.add_result(
                result,
                "Consulta ERP de pedidos pendientes",
                action=step.action,
            )
            return

        if step.action == "get_orders_by_month":
            result = self._erp_tool.get_orders_by_month(
                OrdersByMonthInput.model_validate(step.args)
            )
            execution.data["erp_orders"] = result.data
            execution.data["period"] = {
                "year": step.args.get("year"),
                "month": step.args.get("month"),
            }
            execution.add_result(
                result,
                "Consulta ERP de pedidos por mes",
                action=step.action,
            )
            return

        if step.action == "calculate_order_amount":
            order_amounts = execution.data.setdefault("order_amounts", [])
            order_ids = _order_ids_from_step(step.args)
            if not order_ids:
                execution.add_skipped(
                    tool="ERPTool",
                    action=step.action,
                    source="ERP",
                    args=step.args,
                    summary="No hay pedidos referenciados para calcular importe",
                )
                return

            for order_id in order_ids:
                result = self._erp_tool.calculate_order_amount(
                    OrderAmountInput(order_id=order_id)
                )
                if result.data:
                    order_amounts.append(result.data)
                execution.add_result(
                    result,
                    f"Consulta ERP de importe para pedido {order_id}",
                    action=step.action,
                )
            return

        if step.action == "get_customers_for_production_orders":
            customers_by_order: dict[int, dict[str, Any] | None] = {}
            production_orders = execution.data.get("production_orders", [])
            for production_order in production_orders:
                order_id = int(production_order["order_id"])
                result = self._erp_tool.get_customer_by_order(
                    CustomerByOrderInput(order_id=order_id)
                )
                customers_by_order[order_id] = result.data
                execution.add_result(
                    result,
                    f"Consulta ERP de cliente para pedido {order_id}",
                    action=step.action,
                )
            execution.data["customers_by_order"] = customers_by_order
            return

        execution.add_skipped(
            tool="ERPTool",
            action=step.action,
            source="ERP",
            args=step.args,
            summary=f"Accion ERP no soportada: {step.action}",
        )

    def _execute_production_step(
        self,
        step: PlanStep,
        execution: "_ExecutionContext",
    ) -> None:
        if step.action == "list_orders":
            result = self._production_tool.list_orders(
                ProductionOrdersInput.model_validate(step.args)
            )
            execution.data["production_orders"] = _merge_order_rows(
                execution.data.get("production_orders"),
                result.data,
            )
            execution.add_result(
                result,
                "Consulta API de produccion por estado",
                action=step.action,
            )
            return

        if step.action == "get_status_for_order_ids":
            result = self._production_tool.get_status_for_order_ids(
                ProductionOrdersByIdsInput.model_validate(step.args)
            )
            execution.data["production_orders"] = _merge_order_rows(
                execution.data.get("production_orders"),
                result.data,
            )
            execution.add_result(
                result,
                "Consulta API de produccion para pedidos referenciados",
                action=step.action,
            )
            return

        if step.action == "get_status_for_erp_orders":
            production_by_order: dict[int, dict[str, Any] | None] = {}
            erp_orders = execution.data.get("erp_orders", [])
            if not erp_orders:
                execution.add_skipped(
                    tool="ProductionAPITool",
                    action=step.action,
                    source="Produccion",
                    args={},
                    summary="No hay pedidos ERP para consultar en produccion",
                )
                execution.data["production_by_order"] = production_by_order
                return

            for erp_order in erp_orders:
                order_id = int(erp_order["order_id"])
                result = self._production_tool.get_order_status(
                    ProductionOrderInput(order_id=order_id)
                )
                production_by_order[order_id] = result.data
                execution.add_result(
                    result,
                    f"Consulta API de produccion para pedido {order_id}",
                    action=step.action,
                )
            execution.data["production_by_order"] = production_by_order
            return

        execution.add_skipped(
            tool="ProductionAPITool",
            action=step.action,
            source="Produccion",
            args=step.args,
            summary=f"Accion de produccion no soportada: {step.action}",
        )

    def _execute_rag_step(self, step: PlanStep, execution: "_ExecutionContext") -> None:
        if self._rag_tool is None:
            execution.data["rag"] = {
                "answer": "No hay contexto documental suficiente para responder sin inventar.",
                "status": "insufficient_context",
                "chunks": [],
            }
            execution.add_skipped(
                tool="DocumentRAGTool",
                action=step.action,
                source="Documentos",
                args=step.args,
                summary="DocumentRAGTool no esta configurada en este grafo",
            )
            return

        if step.action == "query":
            result = self._rag_tool.query(DocumentRAGInput.model_validate(step.args))
            execution.data["rag"] = result.data
            execution.add_result(
                result,
                "Consulta RAG documental con chunks recuperados",
                action=step.action,
            )
            return

        execution.add_skipped(
            tool="DocumentRAGTool",
            action=step.action,
            source="Documentos",
            args=step.args,
            summary=f"Accion RAG no soportada: {step.action}",
        )


class _ExecutionContext:
    def __init__(self) -> None:
        self.tool_results: list[dict[str, Any]] = []
        self.tool_calls: list[ToolCallTrace] = []
        self.sources: list[SourceName] = []
        self.reasoning: list[str] = []
        self.fallbacks: list[str] = []
        self.data: dict[str, Any] = {}

    def add_result(
        self,
        result: ToolResult,
        reasoning_step: str,
        action: str | None = None,
    ) -> None:
        self.tool_results.append(result.model_dump(mode="json"))
        tool_call = result.tool_call
        if action and tool_call.action is None:
            tool_call = tool_call.model_copy(update={"action": action})
        self.tool_calls.append(tool_call)
        self._add_source(tool_call.source)
        self._add_fallbacks_from_result(result)
        self.reasoning.append(reasoning_step)

    def add_skipped(
        self,
        tool: str,
        action: str | None,
        source: SourceName,
        args: dict[str, Any],
        summary: str,
    ) -> None:
        tool_call = ToolCallTrace(
            tool=tool,
            action=action,
            args=args,
            status="skipped",
            output_summary=summary,
            source=source,
        )
        self.tool_results.append(
            ToolResult(data=None, tool_call=tool_call).model_dump(mode="json")
        )
        self.tool_calls.append(tool_call)
        if "FALLBACK" in summary:
            self._add_fallback(summary)
        self.reasoning.append(summary)

    def _add_source(self, source: SourceName) -> None:
        if source not in self.sources:
            self.sources.append(source)

    def _add_fallbacks_from_result(self, result: ToolResult) -> None:
        if result.tool_call.output_summary and "FALLBACK" in result.tool_call.output_summary:
            self._add_fallback(result.tool_call.output_summary)

        if isinstance(result.data, dict):
            for fallback in result.data.get("fallbacks", []):
                self._add_fallback(str(fallback))

    def _add_fallback(self, fallback: str) -> None:
        if fallback not in self.fallbacks:
            self.fallbacks.append(fallback)


def _merge_fallbacks(left: list[str], right: list[str]) -> list[str]:
    fallbacks = []
    for fallback in [*left, *right]:
        if fallback not in fallbacks:
            fallbacks.append(fallback)
    return fallbacks


def _order_ids_from_step(args: dict[str, Any]) -> list[int]:
    values = args.get("order_ids")
    if values is None:
        values = [args.get("order_id")]
    if not isinstance(values, list):
        values = [values]

    order_ids: list[int] = []
    for value in values:
        try:
            order_id = int(value)
        except (TypeError, ValueError):
            continue
        if order_id > 0 and order_id not in order_ids:
            order_ids.append(order_id)
    return order_ids


def _merge_order_rows(
    existing: Any,
    incoming: Any,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_order_ids: set[int] = set()
    for source in (existing, incoming):
        if not isinstance(source, list):
            continue
        for row in source:
            if not isinstance(row, dict) or row.get("order_id") is None:
                continue
            order_id = int(row["order_id"])
            if order_id in seen_order_ids:
                continue
            seen_order_ids.add(order_id)
            rows.append(row)
    return rows
