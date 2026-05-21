from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any

from app.agents.planner_models import ExecutionPlan
from app.agents.planner_normalization import normalize_plan
from app.agents.planner_utils import (
    compact_history_for_prompt,
    extract_json_payload,
    message_content,
)
from app.agents.state import AgentState
from app.core.llm import ChatModel
from app.core.traceability import sanitize_exception


def build_llm_plan(
    chat_model: ChatModel,
    llm_timeout_seconds: float,
    question: str,
    state: AgentState,
) -> tuple[ExecutionPlan | None, str | None]:
    try:
        response = _invoke_chat_model(
            chat_model=chat_model,
            llm_timeout_seconds=llm_timeout_seconds,
            prompt=planner_prompt(question, state),
        )
        payload = extract_json_payload(message_content(response))
        plan = ExecutionPlan.model_validate(payload)
        normalized_plan = normalize_plan(plan, question)
        if normalized_plan is None:
            return None, "plan no valido o accion no permitida"
        return normalized_plan, None
    except Exception as exc:
        return None, sanitize_exception(exc)


def planner_fallback(error: str | None) -> str:
    if error:
        return (
            "FALLBACK_PLANNER_RULE_BASED: LLM planner fallo "
            f"({error}); plan creado por reglas."
        )
    return (
        "FALLBACK_PLANNER_RULE_BASED: LLM planner no genero un plan valido; "
        "plan creado por reglas."
    )


def planner_prompt(question: str, state: AgentState) -> str:
    failure_reason = state.get("failure_reason") or "none"
    return f"""
You are the Planner Agent for a controlled business POC.
Return only valid JSON. Do not include markdown, explanations, or chain-of-thought.

Goal:
- Classify the user question.
- Build a serializable execution plan using only the allowed tools and actions.
- The executor has deterministic tools; never invent data.
- If the question is in domain but lacks a required customer, order, period or
  conversational reference, return clarification with no steps.
- If the question is outside ERP, production, RAG documents, or short conversation, return unsupported.

Allowed intents:
erp, production, erp_production, rag, mixed, conversation, clarification, unsupported

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
- Ambiguous pending orders without customer or context: clarification, no steps.
- Isolated follow-up without conversation history: clarification, no steps.
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
  "intent": "erp|production|erp_production|rag|mixed|conversation|clarification|unsupported",
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
Conversation history: {compact_history_for_prompt(state)}
User question: {question}
""".strip()


def _invoke_chat_model(
    chat_model: ChatModel,
    llm_timeout_seconds: float,
    prompt: str,
) -> Any:
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(chat_model.invoke, prompt)
    try:
        return future.result(timeout=llm_timeout_seconds)
    except FutureTimeoutError as exc:
        future.cancel()
        raise TimeoutError("Planner LLM timeout.") from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
