import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.agents.state import AgentIntent, AgentState
from app.core.llm import ChatModel
from app.core.traceability import sanitize_exception


PlanTool = Literal["ERPTool", "ProductionAPITool", "DocumentRAGTool", "MemoryTool"]

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
    "DocumentRAGTool": {"query"},
    "MemoryTool": {"recall"},
}
_ALLOWED_SOURCES = {"ERP", "Produccion", "Documentos", "Memoria"}
_PRODUCTION_STATUSES = {"in_progress", "blocked", "delayed", "finished"}


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
        contextual_unsupported_plan = _build_contextual_unsupported_plan(
            normalized=normalized,
            history=state.get("conversation_history", []),
        )
        if contextual_unsupported_plan is not None:
            return contextual_unsupported_plan, None

        contextual_plan = _build_contextual_rule_based_plan(
            question=question,
            normalized=normalized,
            history=state.get("conversation_history", []),
        )
        if contextual_plan is not None:
            return contextual_plan, None

        if _is_order_penalty_query(normalized):
            return self._build_rule_based_plan(question, normalized, state), None

        if self._chat_model is None:
            return (
                self._build_rule_based_plan(question, normalized, state),
                "FALLBACK_PLANNER_RULE_BASED: LLM planner no configurado; plan creado por reglas.",
            )

        llm_plan, llm_error = self._build_llm_plan(question, state)
        if llm_plan is not None:
            return llm_plan, None

        return (
            self._build_rule_based_plan(question, normalized, state),
            _planner_fallback(llm_error),
        )

    def _build_llm_plan(
        self,
        question: str,
        state: AgentState,
    ) -> tuple[ExecutionPlan | None, str | None]:
        try:
            response = self._invoke_chat_model(self._planner_prompt(question, state))
            payload = _extract_json_payload(_message_content(response))
            plan = ExecutionPlan.model_validate(payload)
            normalized_plan = self._normalize_plan(plan, question)
            if normalized_plan is None:
                return None, "plan no valido o accion no permitida"
            return normalized_plan, None
        except Exception as exc:
            return None, sanitize_exception(exc)

    def _normalize_plan(
        self,
        plan: ExecutionPlan,
        question: str,
    ) -> ExecutionPlan | None:
        if plan.intent == "unsupported":
            return ExecutionPlan(
                intent="unsupported",
                steps=[],
                expected_sources=[],
                answer_requirements=plan.answer_requirements
                or ["Explicar que la pregunta esta fuera del alcance actual."],
            )

        normalized_steps = []
        for index, step in enumerate(plan.steps, start=1):
            if not _is_allowed_step(step):
                return None
            normalized_steps.append(
                PlanStep(
                    step_id=index,
                    tool=step.tool,
                    action=step.action,
                    args=_normalize_step_args(step, question),
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

    @staticmethod
    def _planner_prompt(question: str, state: AgentState) -> str:
        failure_reason = state.get("failure_reason") or "none"
        return f"""
You are the Planner Agent for a controlled business POC.
Return only valid JSON. Do not include markdown, explanations, or chain-of-thought.

Goal:
- Classify the user question.
- Build a serializable execution plan using only the allowed tools and actions.
- The executor has deterministic tools; never invent data.
- If the question is outside ERP, production, RAG documents, or short conversation, return unsupported.

Allowed intents:
erp, production, erp_production, rag, mixed, conversation, unsupported

Allowed tool actions:
- ERPTool.get_pending_orders_by_customer(args: {{"customer_id": "ALFKI"}})
- ERPTool.get_orders_by_month(args: {{"year": 2026, "month": 5}})
- ERPTool.get_customers_for_production_orders(args: {{}})
- ERPTool.calculate_order_amount(args: {{"order_ids": [10248, 10252]}})
- ProductionAPITool.list_orders(args: {{"status": "blocked|delayed|in_progress|finished"}})
- ProductionAPITool.get_status_for_erp_orders(args: {{}})
- ProductionAPITool.get_status_for_order_ids(args: {{"order_ids": [10248, 10252], "status": "blocked|delayed|in_progress|finished|null"}})
- DocumentRAGTool.query(args: {{"query": "<question>", "top_k": 5}})
- MemoryTool.recall(args: {{"query": "<question>", "max_turns": 5}})

Memory rules:
- Use MemoryTool only to resolve short conversational references.
- Do not treat memory as a source of business truth; after resolving references, use ERP, Produccion or Documentos tools for current facts.
- For pure conversation summaries, MemoryTool can be the only tool.

Source names:
ERP, Produccion, Documentos, Memoria

Business examples:
- Pending orders for a customer: ERPTool.get_pending_orders_by_customer.
- Pending orders plus production status: ERP first, then ProductionAPITool.get_status_for_erp_orders.
- Blocked orders and reason: ProductionAPITool.list_orders(status=blocked), then ERPTool.get_customers_for_production_orders.
- Delayed orders and affected customers: ProductionAPITool.list_orders(status=delayed), then ERPTool.get_customers_for_production_orders.
- This month summary: ERPTool.get_orders_by_month(year=2026, month=5), then ProductionAPITool.get_status_for_erp_orders.
- Penalties by order based on current order state: ERPTool.get_orders_by_month(year=2026, month=5), then ProductionAPITool.get_status_for_erp_orders, then DocumentRAGTool.query.
- Conversational blocked orders from previous order IDs: MemoryTool.recall, then ProductionAPITool.get_status_for_order_ids(status=blocked), then ERPTool.get_customers_for_production_orders.
- Conversational economic impact from previous order IDs: MemoryTool.recall, then ERPTool.calculate_order_amount.
- PDF, contract, delivery terms, penalties, clauses, documents: DocumentRAGTool.query.

Output schema:
{{
  "intent": "erp|production|erp_production|rag|mixed|conversation|unsupported",
  "steps": [
    {{
      "step_id": 1,
      "tool": "ERPTool|ProductionAPITool|DocumentRAGTool|MemoryTool",
      "action": "allowed_action",
      "args": {{}},
      "required": true
    }}
  ],
  "expected_sources": ["ERP"],
  "answer_requirements": ["short auditable requirement"]
}}

Previous failure reason: {failure_reason}
Conversation history: {_compact_history_for_prompt(state)}
User question: {question}
""".strip()

    def _invoke_chat_model(self, prompt: str) -> Any:
        if self._chat_model is None:
            raise RuntimeError("Planner LLM no configurado.")

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self._chat_model.invoke, prompt)
        try:
            return future.result(timeout=self._llm_timeout_seconds)
        except FutureTimeoutError as exc:
            future.cancel()
            raise TimeoutError("Planner LLM timeout.") from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _build_rule_based_plan(
        self,
        question: str,
        normalized: str,
        state: AgentState,
    ) -> ExecutionPlan:
        contextual_plan = _build_contextual_rule_based_plan(
            question=question,
            normalized=normalized,
            history=state.get("conversation_history", []),
        )
        if contextual_plan is not None:
            return contextual_plan

        if _is_order_penalty_query(normalized):
            return ExecutionPlan(
                intent="mixed",
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
                    PlanStep(
                        step_id=3,
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
                expected_sources=["ERP", "Produccion", "Documentos"],
                answer_requirements=[
                    "Devolver penalizacion aplicable por pedido usando ERP, produccion y normativa documental.",
                ],
            )

        if _is_document_query(normalized):
            return ExecutionPlan(
                intent="rag",
                steps=[
                    PlanStep(
                        step_id=1,
                        tool="DocumentRAGTool",
                        action="query",
                        args={"query": question, "top_k": 5},
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

        if "retrasad" in normalized or "demor" in normalized:
            return ExecutionPlan(
                intent="erp_production",
                steps=[
                    PlanStep(
                        step_id=1,
                        tool="ProductionAPITool",
                        action="list_orders",
                        args={"status": "delayed"},
                    ),
                    PlanStep(
                        step_id=2,
                        tool="ERPTool",
                        action="get_customers_for_production_orders",
                    ),
                ],
                expected_sources=["Produccion", "ERP"],
                answer_requirements=[
                    "Devolver pedidos retrasados, clientes afectados y motivo del retraso."
                ],
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
            if "producci" in normalized or "estado" in normalized:
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


def _build_contextual_rule_based_plan(
    question: str,
    normalized: str,
    history: list[dict[str, Any]],
) -> ExecutionPlan | None:
    if not history:
        return None

    normalized_ascii = _strip_accents(normalized)
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


def _build_contextual_unsupported_plan(
    normalized: str,
    history: list[dict[str, Any]],
) -> ExecutionPlan | None:
    normalized_ascii = _strip_accents(normalized)
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
                latest_order_ids = _normalize_order_ids(turn_facts.get("order_ids"))

        if "customer_id" not in facts:
            for field in ("question", "answer"):
                value = turn.get(field) if isinstance(turn, dict) else None
                if isinstance(value, str):
                    customer_id = PlannerAgent._extract_customer_id(value)
                    if customer_id:
                        facts["customer_id"] = customer_id
                        break

    if latest_order_ids:
        facts["order_ids"] = latest_order_ids
    return facts


def _looks_like_contextual_followup(normalized_ascii: str) -> bool:
    text = normalized_ascii.strip(" ?!¡¿")
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


def _compact_history_for_prompt(state: AgentState) -> str:
    compact_history = []
    for turn in state.get("conversation_history", [])[-5:]:
        if not isinstance(turn, dict):
            continue
        compact_history.append(
            {
                "question": _short_text(str(turn.get("question") or ""), 180),
                "answer": _short_text(str(turn.get("answer") or ""), 240),
                "facts": turn.get("facts") if isinstance(turn.get("facts"), dict) else {},
            }
        )
    return json.dumps(compact_history, ensure_ascii=True)


def _strip_accents(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFD", value)
        if unicodedata.category(character) != "Mn"
    )


def _short_text(value: str, max_length: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3].rstrip() + "..."


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
        raise ValueError("Planner LLM response did not include JSON.")
    payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("Planner LLM response JSON must be an object.")
    return payload


def _is_allowed_step(step: PlanStep) -> bool:
    return step.action in _ALLOWED_TOOL_ACTIONS.get(step.tool, set())


def _normalize_step_args(step: PlanStep, question: str) -> dict[str, Any]:
    if step.tool == "ERPTool" and step.action == "get_pending_orders_by_customer":
        customer_id = str(step.args.get("customer_id") or "").upper()
        if not re.fullmatch(r"[A-Z]{5}", customer_id):
            customer_id = PlannerAgent._extract_customer_id(question) or "ALFKI"
        return {"customer_id": customer_id}

    if step.tool == "ERPTool" and step.action == "get_orders_by_month":
        return {
            "year": _bounded_int(step.args.get("year"), default=2026, minimum=2000, maximum=2100),
            "month": _bounded_int(step.args.get("month"), default=5, minimum=1, maximum=12),
        }

    if step.tool == "ERPTool" and step.action == "calculate_order_amount":
        order_ids = _normalize_order_ids(step.args.get("order_ids"))
        if order_ids:
            return {"order_ids": order_ids}
        return {"order_id": _bounded_int(step.args.get("order_id"), default=0, minimum=0, maximum=999999)}

    if step.tool == "ProductionAPITool" and step.action == "list_orders":
        status = step.args.get("status")
        return {"status": status if status in _PRODUCTION_STATUSES else None}

    if step.tool == "ProductionAPITool" and step.action == "get_status_for_order_ids":
        status = step.args.get("status")
        return {
            "order_ids": _normalize_order_ids(step.args.get("order_ids")),
            "status": status if status in _PRODUCTION_STATUSES else None,
        }

    if step.tool == "DocumentRAGTool" and step.action == "query":
        args: dict[str, Any] = {
            "query": str(step.args.get("query") or question),
            "top_k": _bounded_int(step.args.get("top_k"), default=5, minimum=1, maximum=10),
        }
        if "min_score" in step.args:
            args["min_score"] = _bounded_float(
                step.args.get("min_score"),
                default=0.2,
                minimum=0,
                maximum=1,
            )
        return args

    if step.tool == "MemoryTool" and step.action == "recall":
        return {
            "query": str(step.args.get("query") or question),
            "max_turns": _bounded_int(
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
        "DocumentRAGTool": "Documentos",
        "MemoryTool": "Memoria",
    }.get(tool)


def _planner_fallback(error: str | None) -> str:
    if error:
        return (
            "FALLBACK_PLANNER_RULE_BASED: LLM planner fallo "
            f"({error}); plan creado por reglas."
        )
    return (
        "FALLBACK_PLANNER_RULE_BASED: LLM planner no genero un plan valido; "
        "plan creado por reglas."
    )


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def _bounded_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def _normalize_order_ids(value: Any) -> list[int]:
    values = value if isinstance(value, list) else [value]
    order_ids: list[int] = []
    for item in values:
        try:
            order_id = int(item)
        except (TypeError, ValueError):
            continue
        if order_id > 0 and order_id not in order_ids:
            order_ids.append(order_id)
    return order_ids


def _is_document_query(normalized: str) -> bool:
    return any(
        marker in normalized
        for marker in (
            "document",
            "pdf",
            "contrato",
            "plazo",
            "penalizacion",
            "penalizaci",
            "clausula",
            "entrega",
        )
    )


def _is_order_penalty_query(normalized: str) -> bool:
    if "penaliz" not in normalized:
        return False
    if "pedido" not in normalized and "order" not in normalized:
        return False
    return any(
        marker in normalized
        for marker in (
            "estado",
            "produccion",
            "cada uno",
            "cada pedido",
            "en cada uno",
        )
    )
