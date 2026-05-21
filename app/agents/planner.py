from app.agents.planner_context import (
    build_contextual_clarification_plan,
    build_contextual_rule_based_plan,
)
from app.agents.planner_llm import build_llm_plan, planner_fallback
from app.agents.planner_models import ExecutionPlan, PlanStep, PlanTool
from app.agents.planner_rules import build_rule_based_plan, is_order_penalty_query
from app.agents.planner_utils import extract_customer_id
from app.agents.state import AgentState
from app.core.llm import ChatModel

__all__ = ["ExecutionPlan", "PlanStep", "PlanTool", "PlannerAgent"]


class PlannerAgent:
    def __init__(
        self,
        chat_model: ChatModel | None = None,
        llm_timeout_seconds: float = 8.0,
    ) -> None:
        self._chat_model = chat_model
        self._llm_timeout_seconds = llm_timeout_seconds

    def __call__(self, state: AgentState) -> AgentState:
        question = state["question"]
        normalized = question.lower()
        plan, fallback = self._build_plan(question, normalized, state)
        fallbacks = list(state.get("fallbacks", []))
        if fallback and fallback not in fallbacks:
            fallbacks.append(fallback)
        return {
            **state,
            "intent": plan.intent,
            "plan": plan.model_dump(),
            "status": "planning",
            "attempts": state.get("attempts", 0),
            "fallbacks": fallbacks,
        }

    def _build_plan(
        self,
        question: str,
        normalized: str,
        state: AgentState,
    ) -> tuple[ExecutionPlan, str | None]:
        contextual_clarification_plan = build_contextual_clarification_plan(
            normalized=normalized,
            history=state.get("conversation_history", []),
        )
        if contextual_clarification_plan is not None:
            return contextual_clarification_plan, None

        contextual_plan = build_contextual_rule_based_plan(
            question=question,
            normalized=normalized,
            history=state.get("conversation_history", []),
        )
        if contextual_plan is not None:
            return contextual_plan, None

        if is_order_penalty_query(normalized):
            return build_rule_based_plan(question, normalized, state), None

        if self._chat_model is None:
            return (
                build_rule_based_plan(question, normalized, state),
                "FALLBACK_PLANNER_RULE_BASED: LLM planner no configurado; plan creado por reglas.",
            )

        llm_plan, llm_error = build_llm_plan(
            chat_model=self._chat_model,
            llm_timeout_seconds=self._llm_timeout_seconds,
            question=question,
            state=state,
        )
        if llm_plan is not None:
            return llm_plan, None

        return (
            build_rule_based_plan(question, normalized, state),
            planner_fallback(llm_error),
        )

    @staticmethod
    def _extract_customer_id(question: str) -> str | None:
        return extract_customer_id(question)
