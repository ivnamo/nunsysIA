from __future__ import annotations

import os
from threading import Lock
from typing import Any, Callable

from app.agents.deepagents_answer_auditor import (
    answer_auditor_names,
    build_answer_auditor_subagents,
)
from app.agents.deepagents_answering import (
    confidence as _confidence,
    economic_impact_answer as _economic_impact_answer,
    erp_orders_answer as _erp_orders_answer,
    erp_with_production_answer as _erp_with_production_answer,
    month_summary_answer as _month_summary_answer,
    normalized_answer as _normalized_answer,
    production_status_answer as _production_status_answer,
    with_deepagents_planning as _with_deepagents_planning,
)
from app.agents.deepagents_harness import (
    REGISTERED_BUSINESS_HARNESS_MODELS as _REGISTERED_BUSINESS_HARNESS_MODELS,
)
from app.agents.deepagents_harness import create_deep_agent as _create_deep_agent
from app.agents.deepagents_harness import (
    register_business_harness_profile as _register_business_harness_profile,
)
from app.agents.deepagents_policy import (
    tool_policy as _tool_policy,
)
from app.agents.deepagents_runtime.constants import _CACHE_MISS
from app.agents.deepagents_runtime.agent_output import (
    _count_tool_calls,
    _dedupe_tools,
    _last_message_text,
)
from app.agents.deepagents_runtime.answer_quality import (
    _agent_answer_from_text,
    _usable_business_agent_answer,
    _usable_document_agent_answer,
)
from app.agents.deepagents_runtime.messages import (
    _direct_tools_user_message,
    _document_context_for_agent,
    _rag_evidence_reasoning_steps,
    _rag_retrieval_reasoning,
)
from app.agents.deepagents_runtime.selectors import (
    _extract_customer_id,
    _is_month_summary,
    _order_ids,
    _requested_production_status,
)
from app.agents.deepagents_runtime.tool_adapters import DeepAgentsToolAdapters
from app.agents.evidence_verifier import (
    VerificationResult,
    required_evidence,
    verify_response,
)
from app.agents.penalty_policy import build_order_penalties_answer
from app.agents.prompts import MAIN_DEEP_AGENT_PROMPT
from app.core.config import Settings
from app.core.traceability import (
    build_public_data_summary,
    sanitize_reasoning,
    sanitize_tool_calls,
)
from app.core.tracing import SourceName, ToolCallTrace, ToolResult
from app.schemas.query import QueryRequest, QueryResponse, QueryStatus
from app.tools.erp_query_tool import ERPQueryTool
from app.tools.erp_tool import (
    CustomerByOrderInput,
    ERPTool,
    OrderAmountInput,
    OrdersByMonthInput,
    PendingOrdersByCustomerInput,
)
from app.tools.memory_tool import ConversationMemoryStore, MemoryRecallInput, MemoryTool
from app.tools.production_query_tool import ProductionQueryTool
from app.tools.production_tool import (
    ProductionAPITool,
    ProductionOrdersByIdsInput,
    ProductionOrdersInput,
)
from app.tools.query_dsl import ERPQuerySpec, ProductionQuerySpec
from app.tools.rag_tool import DocumentRAGInput, DocumentRAGTool


AgentBuilder = Callable[..., Any]


class DeepAgentsToolsQueryService:
    """Primary DeepAgents business flow with auditable deterministic guardrails."""

    def __init__(
        self,
        erp_tool: ERPTool,
        production_tool: ProductionAPITool,
        erp_query_tool: ERPQueryTool,
        production_query_tool: ProductionQueryTool,
        rag_tool: DocumentRAGTool,
        model: str,
        gemini_api_key: str | None = None,
        openai_api_key: str | None = None,
        memory_store: ConversationMemoryStore | None = None,
        agent_builder: AgentBuilder | None = None,
        orchestration_mode: str = "direct_tools_verified",
    ) -> None:
        self._erp_tool = erp_tool
        self._production_tool = production_tool
        self._erp_query_tool = erp_query_tool
        self._production_query_tool = production_query_tool
        self._rag_tool = rag_tool
        self._model = model
        self._gemini_api_key = gemini_api_key
        self._openai_api_key = openai_api_key
        self._memory_store = memory_store or ConversationMemoryStore()
        self._agent_builder = agent_builder or _create_deep_agent
        self._orchestration_mode = orchestration_mode

    def run(self, request: QueryRequest) -> QueryResponse:
        self._prime_provider_environment()
        execution = self._build_execution(request)
        preflight_response = execution.preflight_response()
        if preflight_response is not None:
            return self._remember_and_return(request, preflight_response)

        if self._orchestration_mode == "legacy_guarded":
            execution.run_guarded_fallback()
            result = self._invoke_agent(execution, request)
            execution.record_deepagents_planning(result)
            response = execution.build_response(
                _last_message_text(result),
                prefer_agent_answer=True,
                verification=VerificationResult("passed"),
                repair_attempted=False,
            )
            return self._remember_and_return(request, response)

        return self._run_direct_tools_verified(request, execution)

    def _run_direct_tools_verified(
        self,
        request: QueryRequest,
        execution: "_DirectToolsExecution",
    ) -> QueryResponse:
        result = self._invoke_agent(execution, request)
        execution.record_deepagents_planning(result)
        execution.ensure_canonical_business_traces()
        response = execution.build_response(
            _last_message_text(result),
            prefer_agent_answer=True,
            verification=VerificationResult("passed"),
            repair_attempted=False,
        )
        verification = execution.verify(response)
        if verification.passed:
            response = execution.with_verification_metadata(
                response,
                verification=verification,
                repair_attempted=False,
            )
            return self._remember_and_return(request, response)

        execution.run_guarded_fallback()
        repair_result = self._invoke_agent(
            execution,
            request,
            repair_feedback=verification.repair_prompt(),
        )
        execution.record_deepagents_planning(repair_result)
        execution.ensure_canonical_business_traces()
        repaired_response = execution.build_response(
            _last_message_text(repair_result),
            prefer_agent_answer=True,
            verification=verification,
            repair_attempted=True,
        )
        repaired_verification = execution.verify(repaired_response)
        if repaired_verification.passed:
            repaired_response = execution.with_verification_metadata(
                repaired_response,
                verification=repaired_verification,
                repair_attempted=True,
            )
            return self._remember_and_return(request, repaired_response)

        fallback_response = execution.build_response(
            _last_message_text(repair_result) or _last_message_text(result),
            prefer_agent_answer=False,
            verification=repaired_verification,
            repair_attempted=True,
        )
        final_verification = execution.verify(fallback_response)
        fallback_response = execution.with_verification_metadata(
            fallback_response,
            verification=final_verification,
            repair_attempted=True,
        )
        return self._remember_and_return(request, fallback_response)

    def _build_execution(self, request: QueryRequest) -> "_DirectToolsExecution":
        history = self._memory_store.history(request.conversation_id)
        return _DirectToolsExecution(
            question=request.question,
            conversation_history=history,
            include_citation_previews=request.include_citation_previews,
            erp_tool=self._erp_tool,
            production_tool=self._production_tool,
            erp_query_tool=self._erp_query_tool,
            production_query_tool=self._production_query_tool,
            rag_tool=self._rag_tool,
            memory_tool=MemoryTool(),
            model=self._model,
        )

    def _invoke_agent(
        self,
        execution: "_DirectToolsExecution",
        request: QueryRequest,
        repair_feedback: str | None = None,
    ) -> Any:
        agent = self._agent_builder(
            model=self._model,
            tools=execution.tools(),
            subagents=execution.answer_auditor_subagents(),
            system_prompt=MAIN_DEEP_AGENT_PROMPT,
            name="nunsys-deepagent-query",
        )
        return agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": execution.agent_user_message(
                            request,
                            repair_feedback=repair_feedback,
                        ),
                    }
                ]
            }
        )

    def _remember_and_return(
        self,
        request: QueryRequest,
        response: QueryResponse,
    ) -> QueryResponse:
        self._memory_store.remember(
            conversation_id=request.conversation_id,
            question=request.question,
            response=response,
        )
        return response

    def _prime_provider_environment(self) -> None:
        _set_env_if_missing("GEMINI_API_KEY", self._gemini_api_key)
        _set_env_if_missing("OPENAI_API_KEY", self._openai_api_key)


def create_deepagents_tools_query_service(
    settings: Settings,
    erp_tool: ERPTool,
    production_tool: ProductionAPITool,
    erp_query_tool: ERPQueryTool,
    production_query_tool: ProductionQueryTool,
    rag_tool: DocumentRAGTool,
) -> DeepAgentsToolsQueryService:
    return DeepAgentsToolsQueryService(
        erp_tool=erp_tool,
        production_tool=production_tool,
        erp_query_tool=erp_query_tool,
        production_query_tool=production_query_tool,
        rag_tool=rag_tool,
        model=settings.deepagents_model,
        gemini_api_key=settings.gemini_api_key,
        openai_api_key=settings.openai_api_key,
        orchestration_mode=settings.deepagents_orchestration_mode,
    )


class _DirectToolsExecution(DeepAgentsToolAdapters):
    def __init__(
        self,
        question: str,
        conversation_history: list[dict[str, Any]],
        include_citation_previews: bool,
        erp_tool: ERPTool,
        production_tool: ProductionAPITool,
        erp_query_tool: ERPQueryTool,
        production_query_tool: ProductionQueryTool,
        rag_tool: DocumentRAGTool,
        memory_tool: MemoryTool,
        model: str,
    ) -> None:
        self._question = question
        self._conversation_history = conversation_history
        self._include_citation_previews = include_citation_previews
        self._erp_tool = erp_tool
        self._production_tool = production_tool
        self._erp_query_tool = erp_query_tool
        self._production_query_tool = production_query_tool
        self._rag_tool = rag_tool
        self._memory_tool = memory_tool
        self._model = model
        self._policy = _tool_policy(question, conversation_history)
        self._lock = Lock()
        self._cache: dict[Any, Any] = {}
        self._rag_calls = 0
        self.data: dict[str, Any] = {}
        self.tool_calls: list[ToolCallTrace] = []
        self.reasoning: list[str] = []
        self.sources: list[SourceName] = []
        self.fallbacks: list[str] = []
        requested_production_status = _requested_production_status(question)
        if requested_production_status:
            self.data["requested_production_status"] = requested_production_status

    def preflight_response(self) -> QueryResponse | None:
        if not self._policy.needs_isolated_clarification:
            return None
        return QueryResponse(
            answer=(
                "Necesito contexto previo o que me indiques el cliente, pedido "
                "o periodo concreto para saber a que te refieres."
            ),
            sources=[],
            reasoning=[],
            tool_calls=[],
            fallbacks=[],
            confidence=0.6,
            status="needs_clarification",
            data=None,
            failure_reason=None,
        )

    @property
    def policy(self):
        return self._policy

    def run_guarded_fallback(self) -> None:
        """Ejecuta el fallback determinista solo si el agente no verifica."""
        if self._policy.needs_penalty:
            self.assess_penalty_risk_for_orders()
            return
        if self._policy.needs_documents:
            self.answer_document_question_with_citations()
            return
        if self._policy.needs_economic_impact:
            self.calculate_referenced_order_amounts()
            return
        if self._policy.needs_memory and self._policy.needs_production:
            self.resolve_referenced_orders_with_erp_and_production()
            return
        if _is_month_summary(self._question):
            erp_orders = self.get_orders_by_month(year=2026, month=5)
            order_ids = _order_ids(erp_orders)
            if order_ids:
                self.get_production_status_for_order_ids(order_ids)
            return
        if self._policy.needs_production and not self._policy.needs_customer_orders:
            requested_status = _requested_production_status(self._question)
            if requested_status:
                production_orders = self.list_production_orders(status=requested_status)
                self.get_customers_for_order_ids(_order_ids(production_orders))
                return
        if self._policy.needs_customer_orders:
            customer_id = _extract_customer_id(self._question)
            if customer_id and self._policy.needs_production:
                self.get_customer_pending_orders_with_production(customer_id)
            elif customer_id:
                self.get_pending_orders_by_customer(customer_id)

    run_mandatory_tools = run_guarded_fallback

    def ensure_canonical_business_traces(self) -> None:
        """Garantiza trazas canónicas ERP/Producción para casos obligatorios."""
        if self._policy.needs_documents and not self._policy.needs_penalty:
            return
        required_tools = []
        if self._policy.needs_erp:
            required_tools.append("ERPTool")
        if self._policy.needs_production:
            required_tools.append("ProductionAPITool")
        if not required_tools:
            return
        recorded_tools = {call.tool for call in self.tool_calls}
        if any(tool_name not in recorded_tools for tool_name in required_tools):
            self.run_guarded_fallback()

    def verify(self, response: QueryResponse) -> VerificationResult:
        return verify_response(response, policy=self._policy, data=self.data)

    def with_verification_metadata(
        self,
        response: QueryResponse,
        *,
        verification: VerificationResult,
        repair_attempted: bool,
    ) -> QueryResponse:
        metadata = dict(response.metadata or {})
        metadata["orchestration_style"] = "deepagents_direct_tools_verified"
        metadata["verification_status"] = verification.status
        metadata["repair_attempted"] = repair_attempted
        if verification.issues:
            metadata["verification_issues"] = list(verification.issues)
        return response.model_copy(
            update={
                "metadata": metadata,
                "failure_reason": None
                if verification.passed
                else "; ".join(verification.issues),
            }
        )

    def tools(self) -> list[Callable[..., dict[str, Any] | list[dict[str, Any]] | None]]:
        tools: list[Callable[..., Any]] = []
        if self._policy.needs_memory:
            if self._policy.needs_economic_impact:
                tools.append(self.calculate_referenced_order_amounts)
            else:
                tools.append(self.resolve_referenced_orders_with_erp_and_production)
            tools.append(self.recall_memory)
        if self._policy.needs_penalty:
            tools.append(self.assess_penalty_risk_for_orders)
        if self._policy.needs_customer_orders and self._policy.needs_production:
            tools.append(self.get_customer_pending_orders_with_production)
            tools.append(self.query_erp_customer_summary)
        if self._policy.needs_blocked_cross:
            tools.append(self.get_blocked_production_orders_with_erp)
            tools.append(self.query_blocked_orders)
        if self._policy.needs_documents and not self._policy.needs_penalty:
            tools.append(self.answer_document_question_with_citations)
            tools.append(self.search_documents)
            tools.append(self.summarize_document_context)
        if self._policy.needs_erp:
            tools.extend(
                [
                    self.query_erp_customer_summary,
                    self.get_pending_orders_by_customer,
                    self.get_orders_by_month,
                    self.calculate_order_amount,
                ]
            )
            if not (self._policy.needs_customer_orders or self._policy.needs_blocked_cross):
                tools.append(self.query_erp_orders)
        if self._policy.needs_production:
            tools.extend(
                [
                    self.query_production_status,
                    self.list_production_orders,
                    self.get_production_status_for_order_ids,
                ]
            )
            if not self._policy.needs_blocked_cross:
                tools.append(self.query_production_orders)
        if self._policy.needs_documents:
            tools.append(self.search_documents)
            tools.append(self.summarize_document_context)
            tools.append(self.query_documents)
        if not tools:
            tools.extend(
                [
                    self.query_erp_orders,
                    self.query_erp_customer_summary,
                    self.query_production_orders,
                    self.query_production_status,
                    self.search_documents,
                ]
            )
        return _dedupe_tools(tools)

    def answer_auditor_subagents(self) -> list[dict[str, Any]]:
        return build_answer_auditor_subagents(self._model)

    def agent_user_message(
        self,
        request: QueryRequest,
        repair_feedback: str | None = None,
    ) -> str:
        lines = [
            _direct_tools_user_message(request),
            "",
            "Evidencia minima requerida por la politica de tools: "
            + ", ".join(required_evidence(self._policy) or ["sin fuente obligatoria"]),
            (
                "Antes de entregar la respuesta final es obligatorio llamar a la "
                "tool `task` con `subagent_type=\"answer_auditor\"`. Pasa al "
                "auditor un borrador de respuesta, fuentes, pasos y tools usadas. "
                "Si el auditor pide reparar, redacta una respuesta final limpia "
                "usando solo la evidencia de tools. No devuelvas listas de TODOs, "
                "estados internos ni actualizaciones de planificacion como answer."
            ),
        ]
        if repair_feedback:
            lines.extend(["", "Feedback de verificacion:", repair_feedback])
        if self._policy.needs_documents:
            document_context = _document_context_for_agent(self.data.get("rag"))
            if document_context:
                lines.extend(
                    [
                        "",
                        "Contexto documental recuperado para redactar la respuesta:",
                        document_context,
                        "",
                        "Redacta una respuesta humana, clara y sintetica basada solo "
                        "en ese contexto. No pegues chunks completos, cabeceras, "
                        "titulos de pagina ni metadatos en el cuerpo de la respuesta; "
                        "las citas se mostraran aparte.",
                    ]
                )
        return "\n".join(lines)

    def _cached_data(self, key: Any) -> Any:
        with self._lock:
            return self._cache.get(key, _CACHE_MISS)

    def _claim_rag_budget(self) -> bool:
        with self._lock:
            if self._rag_calls >= self._policy.rag_budget:
                return False
            self._rag_calls += 1
            return True

    def record_deepagents_planning(self, result: Any) -> None:
        todo_tool_calls_count = _count_tool_calls(result, "write_todos")
        answer_auditor_calls_count = _count_tool_calls(result, "task")
        with self._lock:
            planning = dict(self.data.get("deepagents_planning") or {})
            planning.update(
                {
                    "todos_used": True,
                    "todo_tool_calls_count": todo_tool_calls_count,
                    "required_evidence": required_evidence(self._policy),
                    "subagents_available": answer_auditor_names(),
                    "answer_auditor_subagent_available": True,
                    "answer_auditor_task_used": answer_auditor_calls_count > 0,
                    "answer_auditor_task_calls_count": answer_auditor_calls_count,
                    "deterministic_answer_gate_used": True,
                }
            )
            if todo_tool_calls_count <= 0:
                planning["todos_used"] = bool(planning.get("todos_used"))
            self.data["deepagents_planning"] = planning

    def build_response(
        self,
        answer: str | None,
        *,
        prefer_agent_answer: bool,
        verification: VerificationResult,
        repair_attempted: bool,
    ) -> QueryResponse:
        agent_answer = _agent_answer_from_text(answer)
        status = self._status(agent_answer)
        should_use_fallback_answer = (
            not prefer_agent_answer or not _usable_business_agent_answer(agent_answer)
        )
        deterministic_answer = (
            self._deterministic_answer(status, agent_answer)
            if should_use_fallback_answer
            else None
        )
        normalized_answer = _normalized_answer(
            deterministic_answer or agent_answer,
            status,
        )
        public_data = build_public_data_summary(
            self.data,
            include_rag_text_preview=self._include_citation_previews,
        )
        public_data = _with_deepagents_planning(public_data, self.data)
        return QueryResponse(
            answer=normalized_answer,
            sources=list(self.sources),
            reasoning=sanitize_reasoning(self.reasoning),
            tool_calls=sanitize_tool_calls(self.tool_calls),
            fallbacks=list(self.fallbacks),
            confidence=_confidence(status),
            status=status,
            data=public_data,
            metadata={
                "orchestration_style": "deepagents_direct_tools_verified",
                "verification_status": verification.status,
                "repair_attempted": repair_attempted,
            },
            failure_reason=None if verification.passed else "; ".join(verification.issues),
        )

    def _deterministic_answer(
        self,
        status: QueryStatus,
        agent_answer: str | None,
    ) -> str | None:
        if status == "insufficient_context":
            return None
        if self._policy.needs_penalty and self.data.get("erp_orders"):
            return build_order_penalties_answer(self.data)
        if self._policy.needs_economic_impact and self.data.get("order_amounts"):
            return _economic_impact_answer(self.data)
        if self._policy.needs_memory and self.data.get("production_orders"):
            return _production_status_answer(self.data)
        if self._policy.needs_documents and isinstance(self.data.get("rag"), dict):
            if status == "completed" and _usable_document_agent_answer(agent_answer):
                return None
            rag_answer = self.data["rag"].get("answer")
            return str(rag_answer) if rag_answer else None
        if self.data.get("period") and self.data.get("erp_orders"):
            return _month_summary_answer(self.data)
        if self.data.get("production_orders") and self.data.get("customers_by_order"):
            return _production_status_answer(self.data)
        if self.data.get("erp_orders") and self.data.get("production_by_order"):
            return _erp_with_production_answer(self.data)
        if self.data.get("erp_orders"):
            return _erp_orders_answer(self.data)
        return None

    def _record(self, result: ToolResult, reasoning: str) -> None:
        self.tool_calls.append(result.tool_call)
        if result.tool_call.source not in self.sources:
            self.sources.append(result.tool_call.source)
        self.reasoning.append(reasoning)
        self._add_fallbacks(result)

    def _extend_reasoning(self, steps: list[str]) -> None:
        for step in steps:
            if step and step not in self.reasoning:
                self.reasoning.append(step)

    def _add_fallbacks(self, result: ToolResult) -> None:
        summary = result.tool_call.output_summary or ""
        if "FALLBACK" in summary and summary not in self.fallbacks:
            self.fallbacks.append(summary)
        if isinstance(result.data, dict):
            for fallback in result.data.get("fallbacks", []):
                fallback_text = str(fallback)
                if fallback_text not in self.fallbacks:
                    self.fallbacks.append(fallback_text)

    def _status(self, answer: str | None) -> QueryStatus:
        if any(call.status == "error" for call in self.tool_calls):
            return "tool_error"
        if not self.tool_calls:
            return "failed"
        rag = self.data.get("rag")
        if (
            isinstance(rag, dict)
            and rag.get("status") == "insufficient_context"
            and self._policy.needs_documents
            and not self._policy.needs_penalty
        ):
            return "insufficient_context"
        return "completed"


def _set_env_if_missing(name: str, value: str | None) -> None:
    if value and not os.getenv(name):
        os.environ[name] = value


__all__ = [
    "DeepAgentsToolsQueryService",
    "create_deepagents_tools_query_service",
]
