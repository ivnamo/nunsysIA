import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.agents.state import AgentIntent, AgentState


PlanTool = Literal["ERPTool", "ProductionAPITool", "DocumentRAGTool", "MemoryTool"]


class PlanStep(BaseModel):
    step_id: int
    tool: PlanTool
    action: str
    args: dict[str, Any] = Field(default_factory=dict)
    required: bool = True


class ExecutionPlan(BaseModel):
    intent: AgentIntent
    steps: list[PlanStep]
    expected_sources: list[str]
    answer_requirements: list[str] = Field(default_factory=list)


class PlannerAgent:
    def __call__(self, state: AgentState) -> AgentState:
        question = state["question"]
        normalized = question.lower()
        plan = self._build_plan(question, normalized)
        return {
            **state,
            "intent": plan.intent,
            "plan": plan.model_dump(),
            "status": "planning",
            "attempts": state.get("attempts", 0),
        }

    def _build_plan(self, question: str, normalized: str) -> ExecutionPlan:
        if "document" in normalized or "pdf" in normalized or "contrato" in normalized:
            return ExecutionPlan(
                intent="rag",
                steps=[
                    PlanStep(
                        step_id=1,
                        tool="DocumentRAGTool",
                        action="query",
                        args={"query": question, "top_k": 3},
                    )
                ],
                expected_sources=["Documentos"],
                answer_requirements=["Responder solo con chunks documentales recuperados."],
            )

        if "bloquead" in normalized:
            return ExecutionPlan(
                intent="erp_production",
                steps=[
                    PlanStep(
                        step_id=1,
                        tool="ProductionAPITool",
                        action="list_orders",
                        args={"status": "blocked"},
                    ),
                    PlanStep(
                        step_id=2,
                        tool="ERPTool",
                        action="get_customers_for_production_orders",
                    ),
                ],
                expected_sources=["Produccion", "ERP"],
                answer_requirements=["Devolver pedido, cliente y motivo de bloqueo."],
            )

        if "mes" in normalized or "resumen" in normalized:
            return ExecutionPlan(
                intent="erp_production",
                steps=[
                    PlanStep(
                        step_id=1,
                        tool="ERPTool",
                        action="get_orders_by_month",
                        args={"year": 2026, "month": 5},
                    ),
                    PlanStep(
                        step_id=2,
                        tool="ProductionAPITool",
                        action="get_status_for_erp_orders",
                    ),
                ],
                expected_sources=["ERP", "Produccion"],
                answer_requirements=["Agrupar pedidos por estado de produccion."],
            )

        if "pendient" in normalized:
            customer_id = self._extract_customer_id(question) or "ALFKI"
            steps = [
                PlanStep(
                    step_id=1,
                    tool="ERPTool",
                    action="get_pending_orders_by_customer",
                    args={"customer_id": customer_id},
                )
            ]
            expected_sources = ["ERP"]
            if "produccion" in normalized or "producción" in normalized or "estado" in normalized:
                steps.append(
                    PlanStep(
                        step_id=2,
                        tool="ProductionAPITool",
                        action="get_status_for_erp_orders",
                    )
                )
                expected_sources.append("Produccion")
                intent: AgentIntent = "erp_production"
            else:
                intent = "erp"

            return ExecutionPlan(
                intent=intent,
                steps=steps,
                expected_sources=expected_sources,
                answer_requirements=["Devolver pedidos pendientes y datos disponibles."],
            )

        return ExecutionPlan(
            intent="unsupported",
            steps=[],
            expected_sources=[],
            answer_requirements=["Explicar que la pregunta esta fuera del alcance actual."],
        )

    @staticmethod
    def _extract_customer_id(question: str) -> str | None:
        matches = re.findall(r"\b[A-Z]{5}\b", question)
        return matches[0] if matches else None
