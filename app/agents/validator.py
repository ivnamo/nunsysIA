from app.agents.planner import ExecutionPlan
from app.agents.state import MAX_REPLANS, AgentState


class ValidatorNode:
    def __call__(self, state: AgentState) -> AgentState:
        plan = ExecutionPlan.model_validate(state.get("plan") or {})
        attempts = state.get("attempts", 0)

        if plan.intent == "unsupported":
            return {
                **state,
                "status": "unsupported",
                "validation_decision": "fail",
                "failure_reason": "La pregunta queda fuera del alcance de la POC actual.",
            }

        if plan.intent == "clarification":
            return {
                **state,
                "status": "needs_clarification",
                "validation_decision": "fail",
                "failure_reason": "Falta informacion concreta para responder sin inventar.",
            }

        tool_calls = state.get("tool_calls", [])
        failed_calls = [call for call in tool_calls if call.status == "error"]
        if failed_calls:
            return self._fail_or_replan(
                state,
                attempts,
                "Una o mas tools devolvieron error.",
                status="tool_error",
            )

        rag_result = state.get("data", {}).get("rag")
        if _requires_document_context(plan) and rag_result:
            if rag_result.get("status") == "insufficient_context":
                return {
                    **state,
                    "status": "insufficient_context",
                    "validation_decision": "fail",
                    "failure_reason": "No hay chunks documentales relevantes.",
                }
        if plan.intent == "rag" and rag_result:
            if rag_result.get("status") == "completed":
                return {
                    **state,
                    "status": "completed",
                    "validation_decision": "finish",
                    "failure_reason": None,
                }

        sources = set(state.get("sources", []))
        missing_sources = set(plan.expected_sources) - sources
        if missing_sources:
            return self._fail_or_replan(
                state,
                attempts,
                f"Faltan fuentes obligatorias: {', '.join(sorted(missing_sources))}.",
                status="partial_answer",
            )

        if plan.steps and not tool_calls:
            return self._fail_or_replan(
                state,
                attempts,
                "El plan tenia pasos pero no se registraron tool calls.",
                status="failed",
            )

        if plan.steps and not state.get("reasoning"):
            return self._fail_or_replan(
                state,
                attempts,
                "El plan tenia pasos pero no se registraron pasos visibles de trazabilidad.",
                status="failed",
            )

        return {
            **state,
            "status": "completed",
            "validation_decision": "finish",
            "failure_reason": None,
        }

    @staticmethod
    def _fail_or_replan(
        state: AgentState,
        attempts: int,
        failure_reason: str,
        status: str,
    ) -> AgentState:
        if attempts < MAX_REPLANS:
            return {
                **state,
                "attempts": attempts + 1,
                "status": status,
                "validation_decision": "replan",
                "failure_reason": failure_reason,
                "replan_history": _append_replan_event(
                    state=state,
                    attempts=attempts,
                    status=status,
                    failure_reason=failure_reason,
                ),
            }

        return {
            **state,
            "status": status,
            "validation_decision": "fail",
            "failure_reason": failure_reason,
        }


def _requires_document_context(plan: ExecutionPlan) -> bool:
    if "Documentos" in plan.expected_sources:
        return True
    return any(
        step.tool == "DocumentRAGTool" and step.required
        for step in plan.steps
    )


def _append_replan_event(
    state: AgentState,
    attempts: int,
    status: str,
    failure_reason: str,
) -> list[dict[str, object]]:
    history = list(state.get("replan_history", []))
    history.append(
        {
            "attempt": attempts + 1,
            "decision": "replan",
            "status": status,
            "failure_reason": failure_reason,
            "max_replans": MAX_REPLANS,
        }
    )
    return history
