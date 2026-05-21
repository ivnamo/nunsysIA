from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any

from pydantic import ValidationError

from app.agents.final_answer_templates import (
    build_deterministic_answer,
    confidence_for_status,
)
from app.agents.final_grounding import (
    build_final_evidence_payload,
    sanitize_tool_call_traces,
    unsupported_critical_facts,
)
from app.agents.final_prompt import (
    FinalAnswerPayload,
    compact_json,
    extract_json_payload,
    final_answer_prompt,
    message_content,
    response_constraints,
)
from app.agents.planner import ExecutionPlan
from app.agents.state import AgentState
from app.core.llm import ChatModel
from app.core.traceability import (
    build_public_data_summary,
    sanitize_exception,
    sanitize_failure_reason,
    sanitize_reasoning,
)
from app.core.tracing import SourceName
from app.schemas.query import QueryResponse, QueryStatus


class FinalResponseBuilder:
    def __init__(
        self,
        chat_model: ChatModel | None = None,
        llm_timeout_seconds: float = 8.0,
    ) -> None:
        self._chat_model = chat_model
        self._llm_timeout_seconds = llm_timeout_seconds

    def __call__(self, state: AgentState) -> AgentState:
        plan = ExecutionPlan.model_validate(state.get("plan") or {})
        status = _query_status(state.get("status", "failed"))
        deterministic_answer = build_deterministic_answer(plan, state, status)
        answer, final_fallback = self._polish_answer_with_llm(
            plan=plan,
            state=state,
            status=status,
            deterministic_answer=deterministic_answer,
        )
        fallbacks = list(state.get("fallbacks", []))
        if final_fallback and final_fallback not in fallbacks:
            fallbacks.append(final_fallback)

        public_data = dict(state.get("data", {}))
        if state.get("replan_history"):
            public_data["replanning"] = state["replan_history"]

        response = QueryResponse(
            answer=answer,
            sources=_sources(state.get("sources", [])),
            reasoning=sanitize_reasoning(state.get("reasoning", [])),
            tool_calls=sanitize_tool_call_traces(state.get("tool_calls", [])),
            fallbacks=fallbacks,
            confidence=confidence_for_status(status),
            status=status,
            data=build_public_data_summary(public_data),
            failure_reason=sanitize_failure_reason(state.get("failure_reason")),
        )
        return {
            **state,
            "final_answer": answer,
            "fallbacks": fallbacks,
            "response": response,
        }

    def _polish_answer_with_llm(
        self,
        plan: ExecutionPlan,
        state: AgentState,
        status: QueryStatus,
        deterministic_answer: str,
    ) -> tuple[str, str | None]:
        if status not in {"completed", "partial_answer"}:
            return deterministic_answer, None

        if self._chat_model is None:
            return (
                deterministic_answer,
                "FALLBACK_FINAL_RESPONSE_DETERMINISTIC: LLM final no configurado; respuesta construida por reglas.",
            )

        data = state.get("data", {})
        if not data:
            return deterministic_answer, None

        public_summary = build_public_data_summary(data) or {}
        question = str(state.get("question") or "")
        constraints = response_constraints(question)
        evidence_payload = build_final_evidence_payload(
            question=question,
            plan=plan,
            state=state,
            public_summary=public_summary,
            deterministic_answer=deterministic_answer,
        )
        evidence_text = compact_json(evidence_payload)
        try:
            prompt = final_answer_prompt(
                question=question,
                intent=plan.intent,
                answer_requirements=plan.answer_requirements,
                constraints=constraints,
                evidence_text=evidence_text,
                deterministic_answer=deterministic_answer,
            )
            payload = self._invoke_structured_payload(prompt)
            if payload is None:
                response = self._invoke_chat_model(prompt)
                payload = FinalAnswerPayload.model_validate(
                    extract_json_payload(message_content(response))
                )
        except (ValidationError, ValueError, RuntimeError, TimeoutError) as exc:
            return (
                deterministic_answer,
                _final_response_fallback(
                    "LLM final fallo o no devolvio JSON valido",
                    sanitize_exception(exc),
                ),
            )
        except Exception as exc:
            return (
                deterministic_answer,
                _final_response_fallback("LLM final fallo", sanitize_exception(exc)),
            )

        candidate = " ".join(payload.answer.split())
        if len(candidate) > constraints["max_chars"]:
            return (
                deterministic_answer,
                _final_response_fallback("LLM final excedio la longitud permitida"),
            )
        unsupported_facts = unsupported_critical_facts(candidate, evidence_text)
        if unsupported_facts:
            return (
                deterministic_answer,
                _final_response_fallback(
                    "LLM final no paso validacion de evidencias",
                    ", ".join(unsupported_facts[:5]),
                ),
            )
        return candidate, None

    def _invoke_chat_model(self, prompt: str) -> Any:
        if self._chat_model is None:
            raise RuntimeError("Final response LLM no configurado.")

        return self._invoke_model(self._chat_model, prompt)

    def _invoke_structured_payload(self, prompt: str) -> FinalAnswerPayload | None:
        if self._chat_model is None:
            raise RuntimeError("Final response LLM no configurado.")

        structured_output = getattr(self._chat_model, "with_structured_output", None)
        if not callable(structured_output):
            return None

        structured_model = structured_output(FinalAnswerPayload)
        response = self._invoke_model(structured_model, prompt)
        return FinalAnswerPayload.model_validate(response)

    def _invoke_model(self, model: Any, prompt: str) -> Any:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(model.invoke, prompt)
        try:
            return future.result(timeout=self._llm_timeout_seconds)
        except FutureTimeoutError as exc:
            future.cancel()
            raise TimeoutError("Final response LLM timeout.") from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)


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


def _final_response_fallback(reason: str, detail: str | None = None) -> str:
    if detail:
        return (
            "FALLBACK_FINAL_RESPONSE_DETERMINISTIC: "
            f"{reason} ({detail}); respuesta construida por reglas."
        )
    return (
        "FALLBACK_FINAL_RESPONSE_DETERMINISTIC: "
        f"{reason}; respuesta construida por reglas."
    )


def _sources(values: list[str]) -> list[SourceName]:
    allowed = {"ERP", "Produccion", "Documentos", "Memoria"}
    return [value for value in values if value in allowed]
