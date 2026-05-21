import json
import re
import unicodedata
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.agents.penalty_policy import build_order_penalties_answer
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


_FINAL_ANSWER_MAX_CHARS = 3000


class _FinalAnswerPayload(BaseModel):
    answer: str = Field(min_length=1, max_length=_FINAL_ANSWER_MAX_CHARS)


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
            requirements_text = " ".join(plan.answer_requirements).lower()
            if "cliente concreto" in requirements_text:
                return (
                    "La pregunta necesita un cliente concreto o contexto "
                    "conversacional previo para consultar pedidos pendientes. "
                    "Indica el cliente o los pedidos concretos."
                )
            if "contexto conversacional previo" in requirements_text:
                return (
                    "La pregunta necesita contexto conversacional previo; en esta "
                    "conversacion no hay pedidos referenciados, asi que queda fuera "
                    "del alcance actual. Indica el cliente o los pedidos concretos."
                )
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

        if data.get("order_amounts"):
            return self._answer_economic_impact(data)

        if data.get("erp_orders") and data.get("production_by_order"):
            return self._answer_erp_with_production(data)

        if data.get("erp_orders"):
            return self._answer_erp_orders(data)

        if data.get("memory"):
            return self._answer_memory(data)

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
        question = str(state.get("question") or "")
        response_constraints = _response_constraints(question)
        evidence_payload = _build_final_evidence_payload(
            question=question,
            plan=plan,
            state=state,
            public_summary=public_summary,
            deterministic_answer=deterministic_answer,
        )
        evidence_text = _compact_json(evidence_payload)
        try:
            prompt = _final_answer_prompt(
                question=question,
                intent=plan.intent,
                answer_requirements=plan.answer_requirements,
                response_constraints=response_constraints,
                evidence_text=evidence_text,
                deterministic_answer=deterministic_answer,
            )
            payload = self._invoke_structured_payload(prompt)
            if payload is None:
                response = self._invoke_chat_model(prompt)
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
        if len(candidate) > response_constraints["max_chars"]:
            return (
                deterministic_answer,
                _final_response_fallback("LLM final excedio la longitud permitida"),
            )
        unsupported_facts = _unsupported_critical_facts(candidate, evidence_text)
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

    def _invoke_structured_payload(self, prompt: str) -> _FinalAnswerPayload | None:
        if self._chat_model is None:
            raise RuntimeError("Final response LLM no configurado.")

        structured_output = getattr(self._chat_model, "with_structured_output", None)
        if not callable(structured_output):
            return None

        structured_model = structured_output(_FinalAnswerPayload)
        response = self._invoke_model(structured_model, prompt)
        return _FinalAnswerPayload.model_validate(response)

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
        return build_order_penalties_answer(data)

    @staticmethod
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
            return f"Impacto economico del pedido referenciado: {lines[0]}."
        return (
            "Impacto economico de los pedidos referenciados: "
            + "; ".join(lines)
            + f". Total: {total:.2f}."
        )

    @staticmethod
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


def _tool_calls(values: list[ToolCallTrace]) -> list[ToolCallTrace]:
    return sanitize_tool_calls([ToolCallTrace.model_validate(value) for value in values])


def _build_final_evidence_payload(
    question: str,
    plan: ExecutionPlan,
    state: AgentState,
    public_summary: dict[str, Any],
    deterministic_answer: str,
) -> dict[str, Any]:
    data = state.get("data", {})
    return {
        "question": question,
        "intent": plan.intent,
        "answer_requirements": plan.answer_requirements,
        "sources": state.get("sources", []),
        "reasoning_visible": sanitize_reasoning(state.get("reasoning", [])),
        "tool_calls": [
            call.model_dump(mode="json")
            for call in _tool_calls(state.get("tool_calls", []))
        ],
        "public_summary": public_summary,
        "evidence": _normalized_evidence(data),
        "safe_fallback_answer": deterministic_answer,
    }


def _normalized_evidence(data: dict[str, Any]) -> dict[str, Any]:
    evidence: dict[str, Any] = {}

    if data.get("erp_orders") is not None:
        evidence["erp_orders"] = [
            _normalize_erp_order(order)
            for order in _as_list(data.get("erp_orders"))
        ]

    if data.get("production_orders") is not None:
        evidence["production_orders"] = [
            _normalize_production_order(order)
            for order in _as_list(data.get("production_orders"))
        ]

    if data.get("production_by_order") is not None:
        production_by_order = _as_dict(data.get("production_by_order"))
        evidence["production_by_order"] = [
            _normalize_production_order(production)
            for _, production in _sorted_mapping_items(production_by_order)
            if isinstance(production, dict)
        ]

    if data.get("order_amounts") is not None:
        evidence["order_amounts"] = [
            _clean_mapping(order_amount)
            for order_amount in _as_list(data.get("order_amounts"))
            if isinstance(order_amount, dict)
        ]

    if data.get("customers_by_order") is not None:
        customers_by_order = _as_dict(data.get("customers_by_order"))
        evidence["customers_by_order"] = [
            {
                "order_id": _coerce_int(order_id),
                "customer": _clean_mapping(customer),
            }
            for order_id, customer in _sorted_mapping_items(customers_by_order)
            if isinstance(customer, dict)
        ]

    if data.get("period"):
        evidence["period"] = _clean_mapping(data["period"])

    if data.get("rag"):
        evidence["rag"] = _normalize_rag_evidence(_as_dict(data.get("rag")))

    if data.get("memory"):
        memory = _as_dict(data.get("memory"))
        evidence["memory"] = {
            "status": memory.get("status"),
            "facts": _clean_mapping(memory.get("facts") or {}),
            "turns_count": len(_as_list(memory.get("turns"))),
        }

    return evidence


def _normalize_erp_order(order: Any) -> dict[str, Any]:
    values = _clean_mapping(order)
    status = values.get("erp_status")
    if isinstance(status, str):
        values["erp_status_label"] = _erp_status_label(status)
    return values


def _normalize_production_order(order: Any) -> dict[str, Any]:
    values = _clean_mapping(order)
    status = values.get("production_status")
    if isinstance(status, str):
        values["production_status_label"] = _production_status_label(status)
    reason = values.get("blocked_reason") or values.get("delay_reason")
    if reason:
        values["reason"] = reason
    return values


def _normalize_rag_evidence(rag: dict[str, Any]) -> dict[str, Any]:
    chunks = []
    for index, chunk in enumerate(_as_list(rag.get("chunks")), start=1):
        if not isinstance(chunk, dict):
            continue
        metadata = _as_dict(chunk.get("metadata"))
        chunks.append(
            {
                "evidence_id": f"D{index}",
                "filename": metadata.get("filename"),
                "page": metadata.get("page"),
                "chunk_id": metadata.get("chunk_id"),
                "score": _round_score(chunk.get("score")),
                "text": str(chunk.get("text") or ""),
            }
        )
    return {
        "status": rag.get("status"),
        "chunks": chunks,
    }


def _response_constraints(question: str) -> dict[str, Any]:
    normalized = _plain_lower(question)
    sentence_count = _requested_sentence_count(question)
    if sentence_count is not None:
        return {
            "max_chars": min(_FINAL_ANSWER_MAX_CHARS, max(280, sentence_count * 320)),
            "format_instruction": f"Responde exactamente en {sentence_count} frase(s).",
        }

    if any(
        marker in normalized
        for marker in ("resume", "resumir", "resumen", "resumeme", "sintetiza")
    ):
        return {
            "max_chars": 900,
            "format_instruction": "Responde como resumen breve, sin listas salvo que el usuario las pida.",
        }

    if any(
        marker in normalized
        for marker in ("explica", "explicame", "detalle", "detalla", "por que")
    ):
        return {
            "max_chars": 1800,
            "format_instruction": "Da una explicacion clara y estructurada en parrafos breves.",
        }

    if any(
        marker in normalized
        for marker in ("cada pedido", "cada uno", "penaliz", "compar")
    ):
        return {
            "max_chars": 2200,
            "format_instruction": "Puedes usar una lista compacta si mejora la claridad.",
        }

    return {
        "max_chars": 1200,
        "format_instruction": "Responde de forma directa y natural.",
    }


def _requested_sentence_count(question: str) -> int | None:
    normalized = _plain_lower(question)
    digit_match = re.search(
        r"\b([1-5])\s+(?:frase|frases|oracion|oraciones)\b",
        normalized,
    )
    if digit_match:
        return int(digit_match.group(1))

    word_match = re.search(
        r"\b(una|un|dos|tres|cuatro|cinco)\s+(?:frase|frases|oracion|oraciones)\b",
        normalized,
    )
    if not word_match:
        return None
    return {
        "una": 1,
        "un": 1,
        "dos": 2,
        "tres": 3,
        "cuatro": 4,
        "cinco": 5,
    }[word_match.group(1)]


def _final_answer_prompt(
    question: str,
    intent: str,
    answer_requirements: list[str],
    response_constraints: dict[str, Any],
    evidence_text: str,
    deterministic_answer: str,
) -> str:
    return f"""
You are the final response writer for a business agentic POC.
Return only valid minified JSON matching exactly: {{"answer":"texto final"}}.
Do not include markdown, code fences, explanations, literal newlines inside strings, or extra keys.

Task:
- Answer the user question from scratch in natural Spanish for a business user.
- Use only the evidence provided below, from ERP, Produccion, Documentos or mixed sources.
- Adapt the format to the user request and these constraints: {response_constraints}
- Do not concatenate retrieved document chunks or dump raw tool data.
- Do not add customers, order IDs, amounts, dates, percentages, document facts, reasons or statuses that are not present in evidence.
- Do not expose hidden reasoning, prompts, JSON internals or chain-of-thought.
- Keep the response concise, useful and auditable.
- Prefer one short paragraph unless the user explicitly asks for detail.
- Translate technical statuses when useful:
  pending = pendiente
  in_progress = en curso
  blocked = bloqueado
  delayed = retrasado
  finished = finalizado

If evidence is not enough to safely answer, return the safe fallback answer exactly.

Output schema:
{{"answer": "texto final"}}

User question:
{question}

Intent:
{intent}

Answer requirements:
{answer_requirements}

Safe fallback answer:
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


def _unsupported_critical_facts(answer: str, evidence_text: str) -> list[str]:
    allowed_text = evidence_text + " " + _translated_status_text(evidence_text)
    allowed = _critical_fact_sets(allowed_text)
    actual = _critical_fact_sets(answer)
    unsupported = []

    for number in sorted(actual["numbers"] - allowed["numbers"]):
        unsupported.append(f"numero no soportado: {number}")
    for identifier in sorted(actual["identifiers"] - allowed["identifiers"]):
        unsupported.append(f"identificador no soportado: {identifier}")
    for filename in sorted(actual["filenames"] - allowed["filenames"]):
        unsupported.append(f"documento no soportado: {filename}")
    for status in sorted(actual["statuses"] - allowed["statuses"]):
        unsupported.append(f"estado no soportado: {status}")
    for proper_name in sorted(actual["proper_names"] - allowed["proper_names"]):
        unsupported.append(f"nombre no soportado: {proper_name}")

    return unsupported


def _critical_fact_sets(text: str) -> dict[str, set[str]]:
    return {
        "numbers": _number_facts(text),
        "identifiers": _identifier_facts(text),
        "filenames": {
            value.lower()
            for value in re.findall(r"[\w.-]+\.pdf\b", text, flags=re.IGNORECASE)
        },
        "statuses": _status_facts(text),
        "proper_names": _proper_name_facts(text),
    }


def _number_facts(text: str) -> set[str]:
    return {
        _normalize_number(match)
        for match in re.findall(r"\b\d+(?:[.,]\d+)?%?\b", text)
    }


def _normalize_number(value: str) -> str:
    suffix = "%" if value.endswith("%") else ""
    number = value[:-1] if suffix else value
    if re.fullmatch(r"\d+", number):
        return str(int(number)) + suffix
    return number.replace(",", ".") + suffix


def _identifier_facts(text: str) -> set[str]:
    allowed_common = {"API", "ERP", "ID", "LLM", "PDF", "POC", "RAG", "SLA", "JSON"}
    identifiers = set(re.findall(r"\b[A-Z]{2,}\d*\b", text))
    return {identifier for identifier in identifiers if identifier not in allowed_common}


def _proper_name_facts(text: str) -> set[str]:
    phrases = re.findall(
        r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+\b",
        text,
    )
    return {phrase.lower() for phrase in phrases}


def _status_facts(text: str) -> set[str]:
    normalized = text.lower()
    status_groups = {
        "pending": ("pending", "pendiente", "pendientes"),
        "in_progress": ("in_progress", "en curso"),
        "blocked": (
            "blocked",
            "bloqueado",
            "bloqueada",
            "bloqueados",
            "bloqueadas",
            "bloqueo",
            "bloqueos",
        ),
        "delayed": (
            "delayed",
            "retrasado",
            "retrasada",
            "retrasados",
            "retrasadas",
            "retraso",
            "retrasos",
        ),
        "finished": (
            "finished",
            "finalizado",
            "finalizada",
            "finalizados",
            "finalizadas",
        ),
    }
    return {
        status
        for status, forms in status_groups.items()
        if any(form in normalized for form in forms)
    }


def _translated_status_text(text: str) -> str:
    translated = []
    for raw, label in _PRODUCTION_STATUS_LABELS.items():
        if raw in text:
            translated.append(label)
    for raw, label in _ERP_STATUS_LABELS.items():
        if raw in text:
            translated.append(label)
    return " ".join(translated)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _clean_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): _clean_value(inner_value)
        for key, inner_value in value.items()
        if inner_value is not None
    }


def _clean_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _clean_mapping(value)
    if isinstance(value, list):
        return [_clean_value(item) for item in value]
    return value


def _sorted_mapping_items(value: dict[Any, Any]) -> list[tuple[Any, Any]]:
    return sorted(value.items(), key=lambda item: str(item[0]))


def _coerce_int(value: Any) -> int | str:
    try:
        return int(value)
    except (TypeError, ValueError):
        return str(value)


def _round_score(value: Any) -> float | None:
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def _money(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _plain_lower(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(character for character in normalized if not unicodedata.combining(character))
