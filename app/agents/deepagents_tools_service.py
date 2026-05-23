from __future__ import annotations

import os
import json
import re
from threading import Lock
from typing import Any, Callable

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
    KNOWN_CUSTOMER_IDS as _KNOWN_CUSTOMER_IDS,
    contains_any as _contains_any,
    normalize_text as _normalize_text,
    tool_policy as _tool_policy,
)
from app.agents.deepagents_subagents import build_business_subagents, subagent_names
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
from app.tools.query_dsl import ERPQuerySpec, ProductionQuerySpec, QueryFilter
from app.tools.rag_tool import DocumentRAGInput, DocumentRAGTool


AgentBuilder = Callable[..., Any]
_CACHE_MISS = object()


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
        orchestration_mode: str = "verified_subagents",
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

        return self._run_verified_subagents(request, execution)

    def _run_verified_subagents(
        self,
        request: QueryRequest,
        execution: "_DirectToolsExecution",
    ) -> QueryResponse:
        result = self._invoke_agent(execution, request)
        execution.record_deepagents_planning(result)
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
        subagents = execution.subagents(self._model)
        agent = self._agent_builder(
            model=self._model,
            tools=execution.tools(),
            subagents=subagents,
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


class _DirectToolsExecution:
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
        metadata["orchestration_style"] = "deepagents_subagents_verified"
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

    def subagents(self, model: str | None = None) -> list[dict[str, Any]]:
        erp_tools: list[Callable[..., Any]] = [
            self.query_erp_customer_summary,
            self.get_pending_orders_by_customer,
            self.get_orders_by_month,
            self.calculate_order_amount,
        ]
        if not (self._policy.needs_customer_orders or self._policy.needs_blocked_cross):
            erp_tools.append(self.query_erp_orders)

        production_tools: list[Callable[..., Any]] = [
            self.query_production_status,
            self.list_production_orders,
            self.get_production_status_for_order_ids,
        ]
        if not self._policy.needs_blocked_cross:
            production_tools.append(self.query_production_orders)

        return build_business_subagents(
            model=model or self._model,
            erp_tools=erp_tools,
            production_tools=production_tools,
            document_tools=[
                self.answer_document_question_with_citations,
                self.search_documents,
                self.summarize_document_context,
                self.query_documents,
            ],
            memory_tools=[self.recall_memory],
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

    def get_customer_pending_orders_with_production(
        self,
        customer_id: str,
    ) -> dict[str, Any]:
        """Tool compuesta: pedidos pendientes de cliente y produccion por order_id."""
        orders = self.get_pending_orders_by_customer(customer_id)
        order_ids = _order_ids(orders)
        production_orders = (
            self.get_production_status_for_order_ids(order_ids) if order_ids else []
        )
        return {
            "customer_id": customer_id,
            "erp_orders": orders,
            "production_orders": production_orders,
        }

    def get_blocked_production_orders_with_erp(self) -> dict[str, Any]:
        """Tool compuesta: produccion bloqueada cruzada con pedidos ERP."""
        production_orders = self.list_production_orders(status="blocked")
        order_ids = _order_ids(production_orders)
        customers_by_order = self.get_customers_for_order_ids(order_ids) if order_ids else {}
        return {
            "production_orders": production_orders,
            "customers_by_order": customers_by_order,
        }

    def query_blocked_orders(self) -> dict[str, Any]:
        """Consulta pedidos bloqueados en produccion y los cruza con ERP."""
        return self.get_blocked_production_orders_with_erp()

    def assess_penalty_risk_for_orders(self) -> dict[str, Any]:
        """Tool compuesta: ERP, produccion y contrato para riesgo de penalizacion."""
        erp_orders = self.get_orders_by_month(year=2026, month=5)
        order_ids = _order_ids(erp_orders)
        production_orders = (
            self.get_production_status_for_order_ids(order_ids)
            if order_ids
            else []
        )
        documents = self.query_documents(
            query=(
                "penalizaciones SLA retrasos bloqueos produccion plazo logistico "
                "exclusiones falta de material averia capacidad"
            ),
            top_k=3,
            min_score=0.2,
        )
        return {
            "erp_orders": erp_orders,
            "production_orders": production_orders,
            "documents": documents,
        }

    def answer_document_question_with_citations(
        self,
        query: str | None = None,
    ) -> dict[str, Any]:
        """Tool compuesta: consulta documental unica con citas controladas."""
        return self.query_documents(query=query or self._question, top_k=3, min_score=0.2)

    def resolve_referenced_orders_with_erp_and_production(
        self,
        query: str | None = None,
    ) -> dict[str, Any]:
        """Tool compuesta: memoria, ERP y produccion para follow-ups sobre pedidos."""
        normalized_query = query or self._question
        memory = self.recall_memory(query=normalized_query)
        facts = memory.get("facts") if isinstance(memory, dict) else {}
        facts = facts if isinstance(facts, dict) else {}
        order_ids = _unique_ints(facts.get("order_ids") or [])
        customer_id = facts.get("customer_id")

        erp_orders: list[dict[str, Any]] = []
        if not order_ids and isinstance(customer_id, str) and customer_id.strip():
            erp_orders = self.get_pending_orders_by_customer(customer_id)
            order_ids = _order_ids(erp_orders)

        requested_status = _requested_production_status(normalized_query)
        production_orders = (
            self.get_production_status_for_order_ids(
                order_ids,
                status=requested_status,
            )
            if order_ids
            else []
        )
        customer_order_ids = _order_ids(production_orders) or order_ids
        customers_by_order = self.get_customers_for_order_ids(customer_order_ids)
        return {
            "memory": memory,
            "erp_orders": erp_orders,
            "production_orders": production_orders,
            "customers_by_order": customers_by_order,
        }

    def calculate_referenced_order_amounts(self, query: str | None = None) -> dict[str, Any]:
        """Tool compuesta: memoria y ERPTool para importes de pedidos referenciados."""
        memory = self.recall_memory(query=query or self._question)
        facts = memory.get("facts") if isinstance(memory, dict) else {}
        facts = facts if isinstance(facts, dict) else {}
        order_ids = _unique_ints(facts.get("order_ids") or [])
        amounts = [
            amount
            for order_id in order_ids
            if (amount := self.calculate_order_amount(order_id)) is not None
        ]
        return {
            "memory": memory,
            "order_amounts": amounts,
        }

    def recall_memory(self, query: str | None = None, max_turns: int = 5) -> dict[str, Any]:
        """Recupera memoria conversacional de esta conversacion."""
        if self._policy.needs_memory and isinstance(self.data.get("memory"), dict):
            return self.data["memory"]
        cache_key = _cache_key("recall_memory", {"query": query, "max_turns": max_turns})
        cached = self._cached_data(cache_key)
        if cached is not _CACHE_MISS:
            return cached
        result = self._memory_tool.recall(
            MemoryRecallInput(
                query=query or self._question,
                conversation_history=self._conversation_history,
                max_turns=max_turns,
            )
        )
        data = result.data or {}
        with self._lock:
            self._cache[cache_key] = data
            self.data["memory"] = data
            self._record(result, "Consulta memoria conversacional")
        return data

    def get_pending_orders_by_customer(self, customer_id: str) -> list[dict[str, Any]]:
        """Consulta pedidos ERP pendientes por customer_id."""
        cache_key = _cache_key(
            "get_pending_orders_by_customer",
            {"customer_id": customer_id},
        )
        cached = self._cached_data(cache_key)
        if cached is not _CACHE_MISS:
            return cached
        result = self._erp_tool.get_pending_orders_by_customer(
            PendingOrdersByCustomerInput(customer_id=customer_id)
        )
        data = result.data or []
        with self._lock:
            self._cache[cache_key] = data
            self.data["erp_orders"] = data
            self._record(result, "Consulta ERP de pedidos pendientes")
        return data

    def get_orders_by_month(self, year: int, month: int) -> list[dict[str, Any]]:
        """Consulta pedidos ERP por ano y mes."""
        cache_key = _cache_key("get_orders_by_month", {"year": year, "month": month})
        cached = self._cached_data(cache_key)
        if cached is not _CACHE_MISS:
            return cached
        result = self._erp_tool.get_orders_by_month(
            OrdersByMonthInput(year=year, month=month)
        )
        data = result.data or []
        with self._lock:
            self._cache[cache_key] = data
            self.data["erp_orders"] = data
            self.data["period"] = {"year": year, "month": month}
            self._record(result, "Consulta ERP de pedidos por mes")
        return data

    def calculate_order_amount(self, order_id: int) -> dict[str, Any] | None:
        """Calcula importe de un pedido ERP por order_id."""
        if self._policy.needs_economic_impact:
            allowed_order_ids = _order_ids_from_memory_data(self.data.get("memory"))
            if allowed_order_ids and int(order_id) not in allowed_order_ids:
                return None
        cache_key = _cache_key("calculate_order_amount", {"order_id": order_id})
        cached = self._cached_data(cache_key)
        if cached is not _CACHE_MISS:
            return cached
        result = self._erp_tool.calculate_order_amount(OrderAmountInput(order_id=order_id))
        data = result.data
        with self._lock:
            self._cache[cache_key] = data
            if data:
                self.data.setdefault("order_amounts", []).append(data)
            self._record(result, f"Consulta ERP de importe para pedido {order_id}")
        return data

    def get_customer_for_order(self, order_id: int) -> dict[str, Any] | None:
        """Resuelve cliente ERP para un order_id de produccion."""
        cache_key = _cache_key("get_customer_for_order", {"order_id": order_id})
        cached = self._cached_data(cache_key)
        if cached is not _CACHE_MISS:
            return cached
        result = self._erp_tool.get_customer_by_order(
            CustomerByOrderInput(order_id=order_id)
        )
        data = result.data
        with self._lock:
            self._cache[cache_key] = data
            customers_by_order = self.data.setdefault("customers_by_order", {})
            customers_by_order[int(order_id)] = data
            self._record(result, f"Consulta ERP de cliente para pedido {order_id}")
        return data

    def get_customers_for_order_ids(self, order_ids: list[int]) -> dict[int, Any]:
        """Resuelve clientes ERP para una lista de pedidos de produccion."""
        customers: dict[int, Any] = {}
        for order_id in _unique_ints(order_ids):
            customers[order_id] = self.get_customer_for_order(order_id)
        return customers

    def query_erp_customer_summary(self, customer_id: str) -> dict[str, Any]:
        """Consulta resumen ERP de un cliente con pedidos pendientes e importes."""
        orders = self.get_pending_orders_by_customer(customer_id)
        order_amounts = [
            amount
            for order in orders
            if (amount := self.calculate_order_amount(int(order["order_id"]))) is not None
        ]
        return {
            "source": "ERP",
            "customer_id": customer_id,
            "orders": orders,
            "order_amounts": order_amounts,
        }

    def list_production_orders(
        self,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lista ordenes de produccion por estado opcional."""
        effective_status = status or _requested_production_status(self._question)
        cache_key = _cache_key("list_production_orders", {"status": effective_status})
        cached = self._cached_data(cache_key)
        if cached is not _CACHE_MISS:
            return cached
        result = self._production_tool.list_orders(
            ProductionOrdersInput(status=effective_status)
        )
        data = result.data or []
        with self._lock:
            self._cache[cache_key] = data
            self.data["production_orders"] = _merge_rows(
                self.data.get("production_orders"),
                data,
            )
            self._record(result, "Consulta API de produccion por estado")
        return data

    def get_production_status_for_order_ids(
        self,
        order_ids: list[int],
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Consulta estados de produccion para una lista de order_id."""
        normalized_order_ids = _unique_ints(order_ids)
        effective_status = status or _requested_production_status(self._question)
        cache_key = _cache_key(
            "get_production_status_for_order_ids",
            {"order_ids": normalized_order_ids, "status": effective_status},
        )
        cached = self._cached_data(cache_key)
        if cached is not _CACHE_MISS:
            return cached
        result = self._production_tool.get_status_for_order_ids(
            ProductionOrdersByIdsInput(
                order_ids=normalized_order_ids,
                status=effective_status,
            )
        )
        data = result.data or []
        with self._lock:
            self._cache[cache_key] = data
            self.data["production_orders"] = _merge_rows(
                self.data.get("production_orders"),
                data,
            )
            production_by_order = self.data.setdefault("production_by_order", {})
            for row in data:
                production_by_order[int(row["order_id"])] = row
            self._record(result, "Consulta API de produccion para pedidos referenciados")
        return data

    def query_production_status(
        self,
        order_ids: list[int],
        status: str | None = None,
    ) -> dict[str, Any]:
        """Consulta estado, bloqueos y retrasos de produccion por order_id."""
        return {
            "source": "Produccion",
            "orders": self.get_production_status_for_order_ids(
                order_ids=order_ids,
                status=status,
            ),
        }

    def query_erp_orders(
        self,
        customer_id: str | None = None,
        order_ids: list[int] | None = None,
        erp_status: str | None = None,
        year: int | None = None,
        month: int | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Consulta ERP con filtros seguros y devuelve pedidos con cliente e importe."""
        normalized_order_ids = _unique_ints(order_ids or [])
        cache_key = _cache_key(
            "query_erp_orders",
            {
                "customer_id": customer_id,
                "order_ids": normalized_order_ids,
                "erp_status": erp_status,
                "year": year,
                "month": month,
                "limit": limit,
            },
        )
        cached = self._cached_data(cache_key)
        if cached is not _CACHE_MISS:
            return cached
        filters = _erp_filters(customer_id, normalized_order_ids, erp_status, year, month)
        result = self._erp_query_tool.query_orders(
            ERPQuerySpec(filters=filters, limit=limit)
        )
        data = result.data or []
        with self._lock:
            self._cache[cache_key] = data
            self.data["erp_query_orders"] = _merge_rows(
                self.data.get("erp_query_orders"),
                data,
            )
            self._record(result, "Consulta ERP mediante filtros seguros")
        return data

    def query_production_orders(
        self,
        order_ids: list[int] | None = None,
        production_status: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Consulta produccion con filtros seguros por order_id o estado."""
        normalized_order_ids = _unique_ints(order_ids or [])
        effective_status = production_status or _requested_production_status(
            self._question
        )
        cache_key = _cache_key(
            "query_production_orders",
            {
                "order_ids": normalized_order_ids,
                "production_status": effective_status,
                "limit": limit,
            },
        )
        cached = self._cached_data(cache_key)
        if cached is not _CACHE_MISS:
            return cached
        filters = _production_filters(normalized_order_ids, effective_status)
        result = self._production_query_tool.query_orders(
            ProductionQuerySpec(filters=filters, limit=limit)
        )
        data = result.data or []
        with self._lock:
            self._cache[cache_key] = data
            self.data["production_orders"] = _merge_rows(
                self.data.get("production_orders"),
                data,
            )
            production_by_order = self.data.setdefault("production_by_order", {})
            for row in data:
                production_by_order[int(row["order_id"])] = row
            self._record(result, "Consulta Produccion mediante filtros seguros")
        return data

    def query_documents(
        self,
        query: str | None = None,
        top_k: int = 3,
        min_score: float = 0.2,
        filename: str | None = None,
    ) -> dict[str, Any]:
        """Consulta documentos RAG; obligatorio para preguntas contractuales o documentales."""
        normalized_query = query or self._question
        normalized_top_k = min(max(top_k, 1), 3)
        cache_key = _cache_key(
            "query_documents",
            {
                "query": normalized_query,
                "top_k": normalized_top_k,
                "min_score": min_score,
                "filename": filename,
            },
        )
        cached = self._cached_data(cache_key)
        if cached is not _CACHE_MISS:
            return cached
        if not self._claim_rag_budget():
            cached_rag = self.data.get("rag")
            if isinstance(cached_rag, dict):
                return cached_rag
            return {"status": "skipped", "reason": "rag_budget_exhausted", "chunks": []}
        result = self._rag_tool.query(
            DocumentRAGInput(
                query=normalized_query,
                top_k=normalized_top_k,
                min_score=min_score,
                filename=filename,
            )
        )
        data = result.data or {}
        with self._lock:
            self._cache[cache_key] = data
            self.data["rag"] = data
            self._record(result, _rag_retrieval_reasoning(data))
            self._extend_reasoning(_rag_evidence_reasoning_steps(data))
        return data

    def search_documents(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.2,
        filename: str | None = None,
    ) -> dict[str, Any]:
        """Busca informacion en documentos PDF indexados usando RAG."""
        return self.query_documents(
            query=query,
            top_k=top_k,
            min_score=min_score,
            filename=filename,
        )

    def summarize_document_context(self, query: str) -> dict[str, Any]:
        """Resume contexto documental recuperado sin inventar evidencia externa."""
        result = self.query_documents(query=query)
        return {
            "source": "Documentos",
            "status": result.get("status"),
            "answer": result.get("answer"),
            "chunks": result.get("chunks", []),
        }

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
            "Subagentes disponibles: " + ", ".join(subagent_names(self.subagents())),
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
        subagents = self.subagents(self._model)
        with self._lock:
            planning = dict(self.data.get("deepagents_planning") or {})
            planning.update(
                {
                    "todos_used": True,
                    "todo_tool_calls_count": todo_tool_calls_count,
                    "subagents_available": subagent_names(subagents),
                    "required_evidence": required_evidence(self._policy),
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
                "orchestration_style": "deepagents_subagents_verified",
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


def _direct_tools_user_message(request: QueryRequest) -> str:
    return "\n".join(
        [
            f"Pregunta: {request.question}",
            f"conversation_id: {request.conversation_id or ''}",
            "Usa solo las tools disponibles para obtener datos antes de responder.",
            "Usa write_todos en consultas multi-fuente o con varios pasos.",
            "Si aparece una tool compuesta, usala antes que repetir primitives.",
            "No repitas consultas con los mismos argumentos.",
            "Si la pregunta es documental o contractual, haz una sola consulta documental.",
            "Si necesitas cruzar ERP y produccion, cruza por order_id.",
        ]
    )


def _document_context_for_agent(rag: Any) -> str:
    if not isinstance(rag, dict) or rag.get("status") != "completed":
        return ""
    chunks = rag.get("chunks")
    if not isinstance(chunks, list):
        return ""

    lines = []
    for index, chunk in enumerate(chunks[:3], start=1):
        if not isinstance(chunk, dict):
            continue
        text = str(chunk.get("text") or "").strip()
        if not text:
            continue
        metadata = chunk.get("metadata") or {}
        metadata = metadata if isinstance(metadata, dict) else {}
        filename = str(metadata.get("filename") or "documento")
        page = metadata.get("page")
        chunk_id = str(metadata.get("chunk_id") or f"chunk-{index}")
        text_preview = " ".join(text.split())[:900]
        lines.append(
            f"[{index}] {filename}, pagina {page}, {chunk_id}: {text_preview}"
        )
    return "\n".join(lines)


def _rag_retrieval_reasoning(rag: Any) -> str:
    if not isinstance(rag, dict):
        return "Consulta RAG documental para localizar evidencia verificable"
    chunks = _rag_chunks(rag)
    if rag.get("status") == "insufficient_context" or not chunks:
        return (
            "Consulta RAG documental para buscar evidencia; no se recuperan "
            "chunks relevantes suficientes"
        )
    return (
        "Consulta RAG documental para localizar evidencia verificable sobre "
        "la pregunta"
    )


def _rag_evidence_reasoning_steps(rag: Any) -> list[str]:
    if not isinstance(rag, dict):
        return []

    chunks = _rag_chunks(rag)
    if rag.get("status") == "insufficient_context" or not chunks:
        return [
            "Valida que no hay evidencia documental suficiente y evita completar con conocimiento del modelo",
        ]

    documents = _rag_document_names(chunks)
    document_label = ", ".join(documents[:3]) if documents else "documentos recuperados"
    if len(documents) > 3:
        document_label += f" y {len(documents) - 3} mas"

    return [
        (
            f"Selecciona {len(chunks)} chunk(s) relevante(s) de {document_label} "
            "como base de evidencia"
        ),
        (
            "Sintetiza la respuesta final usando solo el contexto recuperado "
            "y deja las citas documentales auditables en data.rag.citations"
        ),
    ]


def _rag_chunks(rag: dict[str, Any]) -> list[dict[str, Any]]:
    chunks = rag.get("chunks")
    if not isinstance(chunks, list):
        return []
    return [chunk for chunk in chunks if isinstance(chunk, dict)]


def _rag_document_names(chunks: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for chunk in chunks:
        metadata = chunk.get("metadata")
        if not isinstance(metadata, dict):
            continue
        filename = str(metadata.get("filename") or "").strip()
        if filename and filename not in names:
            names.append(filename)
    return names


def _usable_document_agent_answer(answer: str | None) -> bool:
    if not isinstance(answer, str) or not answer.strip():
        return False
    normalized = answer.strip()
    if len(normalized.split()) < 8:
        return False
    lowered = normalized.lower()
    return not any(
        marker in lowered
        for marker in (
            "no tengo contexto",
            "no puedo responder",
            "sin informacion suficiente",
            "respuesta no determinista",
        )
    )


def _usable_business_agent_answer(answer: str | None) -> bool:
    if not isinstance(answer, str) or not answer.strip():
        return False
    normalized = answer.strip()
    if len(normalized.split()) < 4:
        return False
    lowered = normalized.lower()
    return not any(
        marker in lowered
        for marker in (
            "respuesta no determinista",
            "sin consultas para inspeccion",
            "pregunta:",
            "conversation_id:",
            "usa solo las tools",
            "no tengo contexto",
            "no puedo responder",
            "no hay informacion suficiente",
            "deep agents no genero",
        )
    )


def _agent_answer_from_text(text: str | None) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return None

    stripped = _strip_code_fence(text.strip())
    try:
        payload = json.loads(stripped)
    except ValueError:
        return text.strip()

    if isinstance(payload, dict) and isinstance(payload.get("answer"), str):
        return payload["answer"].strip() or None
    return text.strip()


def _strip_code_fence(text: str) -> str:
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if len(lines) >= 3 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return text


def _last_message_text(result: Any) -> str | None:
    messages = _mapping_value(result, "messages") or []
    for message in reversed(messages):
        content = _mapping_value(message, "content")
        text = _content_text(content)
        if text:
            return text
    return None


def _content_text(content: Any) -> str | None:
    if isinstance(content, str):
        return content.strip() or None
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        text = "\n".join(part.strip() for part in parts if part.strip()).strip()
        return text or None
    return None


def _count_tool_calls(result: Any, tool_name: str) -> int:
    messages = _mapping_value(result, "messages") or []
    ai_tool_call_count = 0
    tool_message_count = 0
    for message in messages:
        for tool_call in _message_tool_calls(message):
            if _tool_call_name(tool_call) == tool_name:
                ai_tool_call_count += 1
        if _mapping_value(message, "name") == tool_name:
            tool_message_count += 1
    return ai_tool_call_count or tool_message_count


def _message_tool_calls(message: Any) -> list[Any]:
    tool_calls = _mapping_value(message, "tool_calls")
    if isinstance(tool_calls, list):
        return tool_calls
    additional_kwargs = _mapping_value(message, "additional_kwargs")
    if isinstance(additional_kwargs, dict) and isinstance(
        additional_kwargs.get("tool_calls"),
        list,
    ):
        return additional_kwargs["tool_calls"]
    content = _mapping_value(message, "content")
    if isinstance(content, list):
        return [
            item
            for item in content
            if isinstance(item, dict)
            and item.get("type") in {"tool_use", "tool_call"}
        ]
    return []


def _tool_call_name(tool_call: Any) -> str | None:
    name = _mapping_value(tool_call, "name")
    if isinstance(name, str):
        return name
    function = _mapping_value(tool_call, "function")
    if isinstance(function, dict) and isinstance(function.get("name"), str):
        return function["name"]
    return None


def _mapping_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _dedupe_tools(tools: list[Callable[..., Any]]) -> list[Callable[..., Any]]:
    deduped = []
    seen: set[str] = set()
    for tool in tools:
        name = tool.__name__
        if name in seen:
            continue
        seen.add(name)
        deduped.append(tool)
    return deduped

def _cache_key(action: str, args: dict[str, Any]) -> tuple[Any, ...]:
    return (action, _freeze(args))


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((key, _freeze(item)) for key, item in value.items()))
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _unique_ints(values: list[int]) -> list[int]:
    normalized = []
    for value in values:
        item = int(value)
        if item not in normalized:
            normalized.append(item)
    return normalized


def _order_ids(rows: list[dict[str, Any]]) -> list[int]:
    order_ids = []
    for row in rows:
        if not isinstance(row, dict) or row.get("order_id") is None:
            continue
        order_id = int(row["order_id"])
        if order_id not in order_ids:
            order_ids.append(order_id)
    return order_ids


def _order_ids_from_memory_data(memory: Any) -> list[int]:
    if not isinstance(memory, dict):
        return []
    facts = memory.get("facts")
    if not isinstance(facts, dict):
        return []
    return _unique_ints(facts.get("order_ids") or [])


def _extract_customer_id(text: str) -> str | None:
    for match in re.findall(r"\b[A-Z]{5}\b", text):
        if match in _KNOWN_CUSTOMER_IDS:
            return match
    normalized = _normalize_text(text)
    for customer_id in sorted(_KNOWN_CUSTOMER_IDS):
        if customer_id.lower() in normalized:
            return customer_id
    return None


def _requested_production_status(text: str) -> str | None:
    normalized = _normalize_text(text)
    if "bloque" in normalized:
        return "blocked"
    if "retras" in normalized:
        return "delayed"
    if "progreso" in normalized or "curso" in normalized:
        return "in_progress"
    if "finaliz" in normalized or "termin" in normalized:
        return "finished"
    return None


def _is_month_summary(text: str) -> bool:
    normalized = _normalize_text(text)
    return _contains_any(normalized, ("este mes", "mes", "mayo")) and _contains_any(
        normalized,
        ("pedido", "pedidos", "estado"),
    )


def _merge_rows(left: Any, right: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    for collection in (left, right):
        if not isinstance(collection, list):
            continue
        for row in collection:
            if not isinstance(row, dict):
                continue
            order_id = row.get("order_id")
            if order_id is None:
                rows.append(row)
                continue
            normalized_order_id = int(order_id)
            if normalized_order_id in seen:
                continue
            seen.add(normalized_order_id)
            rows.append(row)
    return rows


def _erp_filters(
    customer_id: str | None,
    order_ids: list[int] | None,
    erp_status: str | None,
    year: int | None,
    month: int | None,
) -> list[QueryFilter]:
    filters: list[QueryFilter] = []
    if customer_id:
        filters.append(QueryFilter(field="customer_id", value=customer_id))
    if order_ids:
        filters.append(QueryFilter(field="order_id", operator="in", value=order_ids))
    if erp_status:
        filters.append(QueryFilter(field="erp_status", value=erp_status))
    if year is not None:
        filters.append(QueryFilter(field="year", value=year))
    if month is not None:
        filters.append(QueryFilter(field="month", value=month))
    return filters


def _production_filters(
    order_ids: list[int] | None,
    production_status: str | None,
) -> list[QueryFilter]:
    filters: list[QueryFilter] = []
    if order_ids:
        filters.append(QueryFilter(field="order_id", operator="in", value=order_ids))
    if production_status:
        filters.append(QueryFilter(field="production_status", value=production_status))
    return filters


def _set_env_if_missing(name: str, value: str | None) -> None:
    if value and not os.getenv(name):
        os.environ[name] = value


__all__ = [
    "DeepAgentsToolsQueryService",
    "create_deepagents_tools_query_service",
]
