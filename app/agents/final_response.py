import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import date
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.agents.planner import ExecutionPlan
from app.agents.state import AgentState
from app.core.llm import ChatModel
from app.core.tracing import SourceName, ToolCallTrace
from app.core.traceability import (
    build_public_data_summary,
    sanitize_exception,
    sanitize_failure_reason,
    sanitize_reasoning,
    sanitize_tool_calls,
)
from app.schemas.query import QueryResponse, QueryStatus


class _FinalAnswerPayload(BaseModel):
    answer: str = Field(min_length=1, max_length=1200)


_ERP_STATUS_LABELS = {
    "pending": "pendiente",
    "completed": "completado",
    "cancelled": "cancelado",
}

_PRODUCTION_STATUS_LABELS = {
    "blocked": "bloqueado",
    "delayed": "retrasado",
    "finished": "finalizado",
    "in_progress": "en curso",
}


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
        deterministic_answer = self._build_answer(plan, state, status)
        answer, final_fallback = self._polish_answer_with_llm(
            plan=plan,
            state=state,
            status=status,
            deterministic_answer=deterministic_answer,
        )
        fallbacks = list(state.get("fallbacks", []))
        if final_fallback and final_fallback not in fallbacks:
            fallbacks.append(final_fallback)
        response = QueryResponse(
            answer=answer,
            sources=_sources(state.get("sources", [])),
            reasoning=sanitize_reasoning(state.get("reasoning", [])),
            tool_calls=_tool_calls(state.get("tool_calls", [])),
            fallbacks=fallbacks,
            confidence=self._confidence(status),
            status=status,
            data=build_public_data_summary(state.get("data", {})),
            failure_reason=sanitize_failure_reason(state.get("failure_reason")),
        )
        return {
            **state,
            "final_answer": answer,
            "fallbacks": fallbacks,
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
        if _is_order_penalty_plan(plan, state) and data.get("erp_orders") and data.get(
            "production_by_order"
        ):
            return self._answer_order_penalties(data)

        if data.get("rag"):
            return data["rag"]["answer"]

        if data.get("production_orders"):
            return self._answer_production_orders(data)

        if data.get("period"):
            return self._answer_monthly_summary(data)

        if data.get("erp_orders") and data.get("production_by_order"):
            return self._answer_erp_with_production(data)

        if data.get("erp_orders"):
            return self._answer_erp_orders(data)

        if status == "partial_answer":
            return "La consulta produjo una respuesta parcial; revisa la traza para ver fuentes faltantes."

        return "La consulta se completo, pero no se encontraron datos relevantes."

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
        evidence_text = _compact_json(
            {
                "question": state.get("question"),
                "intent": plan.intent,
                "sources": state.get("sources", []),
                "reasoning": sanitize_reasoning(state.get("reasoning", [])),
                "data": data,
                "public_summary": public_summary,
                "fallback_answer": deterministic_answer,
            }
        )
        try:
            response = self._invoke_chat_model(
                _final_answer_prompt(
                    evidence_text=evidence_text,
                    deterministic_answer=deterministic_answer,
                )
            )
            payload = _FinalAnswerPayload.model_validate(
                _extract_json_payload(_message_content(response))
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
        if not _is_grounded_answer(candidate, evidence_text):
            return (
                deterministic_answer,
                _final_response_fallback("LLM final no paso validacion de evidencias"),
            )
        return candidate, None

    def _invoke_chat_model(self, prompt: str) -> Any:
        if self._chat_model is None:
            raise RuntimeError("Final response LLM no configurado.")

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self._chat_model.invoke, prompt)
        try:
            return future.result(timeout=self._llm_timeout_seconds)
        except FutureTimeoutError as exc:
            future.cancel()
            raise TimeoutError("Final response LLM timeout.") from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

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
                detail = _production_status_label(production["production_status"])
                reason = production.get("blocked_reason") or production.get("delay_reason")
                if reason:
                    detail = f"{detail} ({reason})"
            else:
                detail = "sin informacion de produccion"

            erp_status = _erp_status_label(order["erp_status"])
            lines.append(f"{order_id}: ERP {erp_status}, produccion {detail}")

        customer = orders[0]["customer_id"]
        return f"Pedidos del cliente {customer}: " + "; ".join(lines) + "."

    @staticmethod
    def _answer_production_orders(data: dict[str, Any]) -> str:
        production_orders = data.get("production_orders", [])
        customers_by_order = data.get("customers_by_order", {})
        if not production_orders:
            return "No se encontraron pedidos de produccion con los criterios solicitados."

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
            status = _production_status_label(production_order["production_status"])
            reason = (
                production_order.get("blocked_reason")
                or production_order.get("delay_reason")
                or "sin motivo informado"
            )
            lines.append(f"{order_id} ({customer_label}): {status}, {reason}")

        raw_statuses = {order["production_status"] for order in production_orders}
        if raw_statuses == {"blocked"}:
            prefix = "Pedidos bloqueados en produccion"
        elif raw_statuses == {"delayed"}:
            prefix = "Pedidos retrasados en produccion"
        else:
            prefix = "Pedidos de produccion"
        return prefix + ": " + "; ".join(lines) + "."

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
            status = _production_status_label(production["production_status"]) if production else "sin datos"
            statuses[status] += 1

        status_summary = ", ".join(
            f"{status}: {count}" for status, count in sorted(statuses.items())
        )
        return (
            f"En {period.get('year')}-{int(period.get('month')):02d} hay "
            f"{len(orders)} pedidos ERP. Estados de produccion: {status_summary}."
        )

    @staticmethod
    def _answer_order_penalties(data: dict[str, Any]) -> str:
        orders = data.get("erp_orders", [])
        production_by_order = data.get("production_by_order", {})
        if not orders:
            return "No se encontraron pedidos ERP para estimar penalizaciones."

        lines = []
        for order in orders:
            order_id = order["order_id"]
            production = production_by_order.get(order_id)
            if production is None:
                production = production_by_order.get(str(order_id))

            customer = order.get("customer_name") or order.get("customer_id")
            status = (
                _production_status_label(production["production_status"])
                if production
                else "sin informacion de produccion"
            )
            reason = None
            if production:
                reason = production.get("blocked_reason") or production.get("delay_reason")
            status_detail = f"{status} ({reason})" if reason else status
            penalty = _penalty_assessment(order, production)
            lines.append(f"{order_id} ({customer}): {status_detail}; {penalty}")

        return "Penalizaciones estimadas por pedido: " + "; ".join(lines) + "."

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


def _erp_status_label(status: str) -> str:
    return _ERP_STATUS_LABELS.get(status, status)


def _production_status_label(status: str) -> str:
    return _PRODUCTION_STATUS_LABELS.get(status, status)


def _sources(values: list[str]) -> list[SourceName]:
    allowed = {"ERP", "Produccion", "Documentos", "Memoria"}
    return [value for value in values if value in allowed]


def _is_order_penalty_plan(plan: ExecutionPlan, state: AgentState) -> bool:
    if plan.intent != "mixed":
        return False
    question = str(state.get("question") or "").lower()
    return "penaliz" in question and ("pedido" in question or "order" in question)


def _penalty_assessment(
    order: dict[str, Any],
    production: dict[str, Any] | None,
) -> str:
    if production is None:
        return "no calculable porque falta estado de produccion"

    status = str(production.get("production_status") or "")
    reason = str(production.get("blocked_reason") or production.get("delay_reason") or "")

    if status == "blocked" or _is_penalty_exclusion_reason(reason):
        return "sin penalizacion aplicable segun la evidencia actual por exclusion documental"

    required_date = _parse_date(order.get("required_date"))
    shipped_date = _parse_date(order.get("shipped_date"))

    if shipped_date and required_date:
        if shipped_date <= required_date:
            return "sin penalizacion aplicable porque consta enviado antes del plazo requerido"
        return (
            "requiere calcular dias laborables de retraso e imputabilidad logistica "
            "antes de aplicar 2%, 5% o 3% si era urgente"
        )

    if status == "delayed":
        return (
            "pendiente de fecha real de entrega e imputabilidad; no se puede aplicar "
            "penalizacion todavia"
        )

    return "sin penalizacion aplicable con la evidencia actual"


def _is_penalty_exclusion_reason(reason: str) -> bool:
    normalized = reason.lower()
    return any(
        marker in normalized
        for marker in (
            "falta de material",
            "falta de capacidad",
            "averia",
            "bloqueo",
            "cambio de prioridad",
        )
    )


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _tool_calls(values: list[ToolCallTrace]) -> list[ToolCallTrace]:
    return sanitize_tool_calls([ToolCallTrace.model_validate(value) for value in values])


def _final_answer_prompt(evidence_text: str, deterministic_answer: str) -> str:
    return f"""
You are the final response writer for a business agentic POC.
Return only valid JSON. Do not include markdown.

Task:
- Rewrite the fallback answer in natural Spanish for a business user.
- Use only the evidence provided below.
- Do not add customers, order IDs, amounts, dates, percentages, document facts, reasons or statuses that are not present in the evidence.
- Do not expose hidden reasoning or chain-of-thought.
- Keep the answer concise and auditable.
- Translate technical statuses when useful:
  pending = pendiente
  in_progress = en curso
  blocked = bloqueado
  delayed = retrasado
  finished = finalizado

If you cannot improve the fallback answer safely, return the fallback answer exactly.

Output schema:
{{"answer": "texto final"}}

Fallback answer:
{deterministic_answer}

Evidence:
{evidence_text}
""".strip()


def _message_content(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    return str(content)


def _extract_json_payload(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError("Final response LLM did not include JSON.")
    payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("Final response JSON must be an object.")
    return payload


def _compact_json(value: Any, max_length: int = 9000) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str)
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."


def _is_grounded_answer(answer: str, evidence_text: str) -> bool:
    evidence_tokens = _strict_tokens(evidence_text)
    answer_tokens = _strict_tokens(answer)
    return answer_tokens <= evidence_tokens


def _strict_tokens(text: str) -> set[str]:
    tokens = set(re.findall(r"\b[A-Z]{3,}\b", text))
    tokens.update(re.findall(r"\b\d+(?:[.,]\d+)?%?\b", text))
    return tokens
