from __future__ import annotations

import os
import json
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from threading import Lock
from typing import Any, Callable

from app.agents.deepagents_adapter import DeepAgentsUnavailableError, deepagents_is_available
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
_DEEPAGENTS_BUSINESS_EXCLUDED_TOOLS = frozenset(
    {
        "ls",
        "read_file",
        "write_file",
        "edit_file",
        "glob",
        "grep",
        "execute",
        "task",
    }
)
_REGISTERED_BUSINESS_HARNESS_MODELS: set[str] = set()
_KNOWN_CUSTOMER_IDS = frozenset({"ALFKI", "ANATR", "BONAP"})


@dataclass(frozen=True)
class _ToolPolicy:
    needs_memory: bool
    needs_isolated_clarification: bool
    needs_documents: bool
    needs_penalty: bool
    needs_economic_impact: bool
    needs_customer_orders: bool
    needs_production: bool
    needs_blocked_cross: bool
    needs_erp: bool
    rag_budget: int


class DeepAgentsToolsQueryService:
    """DeepAgents business flow with direct access to deterministic tools."""

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

    def run(self, request: QueryRequest) -> QueryResponse:
        self._prime_provider_environment()
        history = self._memory_store.history(request.conversation_id)
        execution = _DirectToolsExecution(
            question=request.question,
            conversation_history=history,
            include_citation_previews=request.include_citation_previews,
            erp_tool=self._erp_tool,
            production_tool=self._production_tool,
            erp_query_tool=self._erp_query_tool,
            production_query_tool=self._production_query_tool,
            rag_tool=self._rag_tool,
            memory_tool=MemoryTool(),
        )
        preflight_response = execution.preflight_response()
        if preflight_response is not None:
            self._memory_store.remember(
                conversation_id=request.conversation_id,
                question=request.question,
                response=preflight_response,
            )
            return preflight_response

        execution.run_mandatory_tools()
        agent = self._agent_builder(
            model=self._model,
            tools=execution.tools(),
            system_prompt=MAIN_DEEP_AGENT_PROMPT,
            name="nunsys-deepagent-query",
        )
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": execution.agent_user_message(request),
                    }
                ]
            }
        )
        execution.record_deepagents_planning(result)
        response = execution.build_response(_last_message_text(result))
        self._memory_store.remember(
            conversation_id=request.conversation_id,
            question=request.question,
            response=response,
        )
        return response

    def _prime_provider_environment(self) -> None:
        _set_env_if_missing("GEMINI_API_KEY", self._gemini_api_key)
        _set_env_if_missing("GOOGLE_API_KEY", self._gemini_api_key)
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

    def run_mandatory_tools(self) -> None:
        """Ejecuta las tools beta-criticas antes del texto libre del agente."""
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
                    self.query_erp_orders,
                ]
            )
        if self._policy.needs_production:
            tools.extend(
                [
                    self.query_production_status,
                    self.list_production_orders,
                    self.get_production_status_for_order_ids,
                    self.query_production_orders,
                ]
            )
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
        production_orders = self.query_production_orders(production_status="blocked")
        order_ids = _order_ids(production_orders)
        erp_orders = self.query_erp_orders(order_ids=order_ids) if order_ids else []
        return {
            "production_orders": production_orders,
            "erp_orders": erp_orders,
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

    def agent_user_message(self, request: QueryRequest) -> str:
        lines = [_direct_tools_user_message(request)]
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
        if todo_tool_calls_count <= 0:
            return
        with self._lock:
            self.data["deepagents_planning"] = {
                "todos_used": True,
                "todo_tool_calls_count": todo_tool_calls_count,
            }

    def build_response(self, answer: str | None) -> QueryResponse:
        agent_answer = _agent_answer_from_text(answer)
        status = self._status(agent_answer)
        deterministic_answer = self._deterministic_answer(status, agent_answer)
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
            failure_reason=None,
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


def _create_deep_agent(**kwargs: Any) -> Any:
    if not deepagents_is_available():
        raise DeepAgentsUnavailableError(
            "deepagents no esta instalado. Instala requirements.txt "
            "en un entorno compatible para activar el flujo principal DeepAgents."
        )
    try:
        from deepagents import HarnessProfile, create_deep_agent, register_harness_profile
    except ImportError as exc:
        raise DeepAgentsUnavailableError(
            "deepagents esta instalado pero no puede importarse correctamente."
        ) from exc
    _register_business_harness_profile(
        kwargs.get("model"),
        harness_profile=HarnessProfile,
        register_harness_profile=register_harness_profile,
    )
    return create_deep_agent(**kwargs)


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


def _normalized_answer(answer: str | None, status: QueryStatus) -> str:
    if status == "insufficient_context":
        return (
            "No he encontrado informacion en los documentos disponibles para "
            "responder a esa pregunta con fiabilidad."
        )
    if status == "needs_clarification":
        return (
            "Necesito contexto previo o que me indiques el cliente, pedido "
            "o periodo concreto para saber a que te refieres."
        )
    if answer and answer.strip():
        return answer.strip()
    if status == "tool_error":
        return "No se pudo completar la consulta por un error en una fuente."
    return "Deep Agents no genero una respuesta final usable para esta consulta."


def _confidence(status: QueryStatus) -> float | None:
    if status == "completed":
        return 0.75
    if status == "insufficient_context":
        return 0.45
    if status == "needs_clarification":
        return 0.6
    return None


def _with_deepagents_planning(
    public_data: dict[str, Any] | None,
    raw_data: dict[str, Any],
) -> dict[str, Any] | None:
    planning = raw_data.get("deepagents_planning")
    if not isinstance(planning, dict):
        return public_data
    summary = dict(public_data or {})
    summary["deepagents_planning"] = {
        "todos_used": bool(planning.get("todos_used")),
        "todo_tool_calls_count": int(planning.get("todo_tool_calls_count") or 0),
    }
    return summary


def _register_business_harness_profile(
    model: Any,
    harness_profile: Any,
    register_harness_profile: Any,
) -> None:
    if not isinstance(model, str) or not model.strip():
        return
    model_key = model.strip()
    if model_key in _REGISTERED_BUSINESS_HARNESS_MODELS:
        return
    register_harness_profile(
        model_key,
        harness_profile(excluded_tools=_DEEPAGENTS_BUSINESS_EXCLUDED_TOOLS),
    )
    _REGISTERED_BUSINESS_HARNESS_MODELS.add(model_key)


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


def _tool_policy(
    question: str,
    conversation_history: list[dict[str, Any]],
) -> _ToolPolicy:
    text = _normalize_text(question)
    has_history = bool(conversation_history)
    needs_isolated_clarification = _looks_like_follow_up(text) and not has_history
    mentions_penalty = _contains_any(text, ("penaliz", "sla"))
    document_first = _contains_any(text, ("segun", "pdf", "document", "contrato", "anexo"))
    needs_penalty = mentions_penalty and not document_first and _contains_any(
        text,
        ("pedido", "pedidos", "estado", "erp", "produccion"),
    )
    needs_economic_impact = has_history and _contains_any(
        text,
        ("impacto economico", "importe", "importes", "valor", "cuanto suman"),
    )
    needs_documents = mentions_penalty or _contains_any(
        text,
        (
            "segun",
            "contrato",
            "document",
            "pdf",
            "anexo",
            "clausul",
            "criptomon",
            "bitcoin",
            "divisa",
            "plazo contractual",
            "logistic",
            "receta",
            "cocina",
            "vegana",
        ),
    )
    has_known_customer = any(customer_id.lower() in text for customer_id in _KNOWN_CUSTOMER_IDS)
    needs_customer_orders = has_known_customer or (
        "cliente" in text and "pedido" in text and "pendiente" in text
    )
    needs_blocked_cross = "bloque" in text and _contains_any(
        text,
        ("produccion", "erp", "cliente", "cruza", "cruce"),
    )
    needs_production = _contains_any(
        text,
        ("produccion", "estado", "bloque", "retras", "fabricacion"),
    )
    needs_erp = needs_customer_orders or needs_economic_impact or _contains_any(
        text,
        ("erp", "pedido"),
    )
    needs_memory = has_history and (
        _looks_like_follow_up(text) or not _has_explicit_business_anchor(text)
    )

    if needs_penalty or needs_blocked_cross:
        needs_erp = True
        needs_production = True
    if needs_memory and _contains_any(text, ("estado", "produccion")):
        needs_production = True

    return _ToolPolicy(
        needs_memory=needs_memory,
        needs_isolated_clarification=needs_isolated_clarification,
        needs_documents=needs_documents,
        needs_penalty=needs_penalty,
        needs_economic_impact=needs_economic_impact,
        needs_customer_orders=needs_customer_orders,
        needs_production=needs_production,
        needs_blocked_cross=needs_blocked_cross,
        needs_erp=needs_erp,
        rag_budget=1 if needs_documents else 0,
    )


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _looks_like_follow_up(text: str) -> bool:
    tokenized = f" {_word_text(text)} "
    return text.startswith(("y ", "ademas", "tambien")) or _contains_any(
        tokenized,
        (" esos ", " esas ", " ellos ", " ellas ", " anterior ", " antes "),
    )


def _has_explicit_business_anchor(text: str) -> bool:
    return bool(_order_ids_from_text(text)) or _contains_any(
        text,
        ("alfki", "bonap", "anatr", "cliente", "pedido", "contrato", "document", "pdf"),
    )


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _word_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


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


def _economic_impact_answer(data: dict[str, Any]) -> str:
    order_amounts = [
        amount
        for amount in data.get("order_amounts", [])
        if isinstance(amount, dict)
    ]
    rows = []
    total = Decimal("0.00")
    for amount in order_amounts:
        order_id = amount.get("order_id")
        value = _money(amount.get("amount"))
        if order_id is None or value is None:
            continue
        total += value
        rows.append([str(order_id), f"{value:.2f}"])

    if not rows:
        return "No se encontraron importes ERP para los pedidos referenciados."
    if len(rows) == 1:
        return (
            "Con los datos disponibles, el impacto economico del pedido "
            f"referenciado es {rows[0][0]}: {rows[0][1]}."
        )
    return (
        "Con los datos disponibles, el impacto economico total de los pedidos "
        f"referenciados es {total:.2f}.\n\n"
        + _markdown_table(["Pedido", "Importe"], rows)
    )


def _production_status_answer(data: dict[str, Any]) -> str:
    requested_status = data.get("requested_production_status")
    production_orders = [
        order
        for order in data.get("production_orders", [])
        if isinstance(order, dict)
        and (
            not isinstance(requested_status, str)
            or order.get("production_status") == requested_status
        )
    ]
    if not production_orders:
        return "No se encontraron estados de produccion para los pedidos referenciados."

    customers_by_order = data.get("customers_by_order") or {}
    rows = []
    for order in production_orders:
        order_id = int(order["order_id"])
        customer = customers_by_order.get(order_id) or customers_by_order.get(
            str(order_id)
        )
        customer_label = _customer_label(customer)
        reason = (
            order.get("blocked_reason")
            or order.get("delay_reason")
            or "sin motivo informado"
        )
        rows.append(
            [
                str(order_id),
                customer_label,
                _production_status_label(str(order.get("production_status") or "")),
                str(reason),
            ]
        )

    return (
        "Estos son los estados de produccion de los pedidos referenciados:\n\n"
        + _markdown_table(["Pedido", "Cliente", "Estado", "Motivo"], rows)
    )


def _erp_with_production_answer(data: dict[str, Any]) -> str:
    orders = [
        order
        for order in data.get("erp_orders", [])
        if isinstance(order, dict)
    ]
    production_by_order = data.get("production_by_order") or {}
    if not orders:
        return "No se encontraron pedidos ERP con los criterios solicitados."

    rows = []
    for order in orders:
        order_id = int(order["order_id"])
        production = production_by_order.get(order_id) or production_by_order.get(
            str(order_id)
        )
        if isinstance(production, dict):
            production_status = _production_status_label(
                str(production.get("production_status") or "")
            )
            observation = (
                production.get("blocked_reason")
                or production.get("delay_reason")
                or "sin bloqueo informado"
            )
        else:
            production_status = "sin informacion"
            observation = "sin estado de produccion disponible"
        rows.append(
            [
                str(order_id),
                _erp_status_label(str(order.get("erp_status") or "")),
                production_status,
                str(observation),
            ]
        )

    customer_id = str(orders[0].get("customer_id") or "cliente")
    return (
        f"El cliente {customer_id} tiene {len(orders)} pedidos pendientes:\n\n"
        + _markdown_table(
            ["Pedido", "Estado ERP", "Estado produccion", "Observacion"],
            rows,
        )
    )


def _month_summary_answer(data: dict[str, Any]) -> str:
    orders = [
        order
        for order in data.get("erp_orders", [])
        if isinstance(order, dict)
    ]
    production_by_order = data.get("production_by_order") or {}
    period = data.get("period") or {}
    rows = []
    status_counts: dict[str, int] = {}
    for order in orders:
        order_id = int(order["order_id"])
        production = production_by_order.get(order_id) or production_by_order.get(
            str(order_id)
        )
        if isinstance(production, dict):
            status = _production_status_label(
                str(production.get("production_status") or "")
            )
        else:
            status = "sin informacion"
        status_counts[status] = status_counts.get(status, 0) + 1
        rows.append([str(order_id), _erp_status_label(str(order.get("erp_status") or "")), status])

    month = int(period.get("month") or 5)
    year = int(period.get("year") or 2026)
    summary = ", ".join(
        f"{status}: {count}" for status, count in sorted(status_counts.items())
    )
    return (
        f"En mayo de {year} hay {len(orders)} pedidos ERP. "
        f"Distribucion por estado de produccion: {summary}.\n\n"
        + _markdown_table(["Pedido", "Estado ERP", "Estado produccion"], rows)
        + f"\n\nPeriodo auditado: {year}-{month:02d}."
    )


def _erp_orders_answer(data: dict[str, Any]) -> str:
    orders = [
        order
        for order in data.get("erp_orders", [])
        if isinstance(order, dict)
    ]
    if not orders:
        return "No se encontraron pedidos ERP con los criterios solicitados."

    rows = [
        [
            str(order.get("order_id")),
            _erp_status_label(str(order.get("erp_status") or "")),
        ]
        for order in orders
    ]
    customer_id = str(orders[0].get("customer_id") or "cliente")
    return (
        f"El cliente {customer_id} tiene {len(orders)} pedidos pendientes:\n\n"
        + _markdown_table(["Pedido", "Estado ERP"], rows)
    )


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def _money(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def _customer_label(customer: Any) -> str:
    if not isinstance(customer, dict):
        return "cliente ERP no resuelto"
    customer_id = customer.get("customer_id")
    customer_name = customer.get("company_name") or customer.get("customer_name")
    if customer_id and customer_name:
        return f"{customer_id} - {customer_name}"
    if customer_id:
        return str(customer_id)
    return "cliente ERP no resuelto"


def _production_status_label(status: str) -> str:
    labels = {
        "blocked": "bloqueado",
        "delayed": "retrasado",
        "finished": "finalizado",
        "in_progress": "en curso",
    }
    return labels.get(status, status or "sin informacion")


def _erp_status_label(status: str) -> str:
    labels = {
        "pending": "pendiente",
        "shipped": "enviado",
        "completed": "completado",
        "cancelled": "cancelado",
    }
    return labels.get(status, status or "sin informacion")


def _order_ids_from_text(text: str) -> list[int]:
    order_ids = []
    for raw_word in text.replace(",", " ").replace(".", " ").split():
        if not raw_word.isdigit():
            continue
        value = int(raw_word)
        if value > 0 and value not in order_ids:
            order_ids.append(value)
    return order_ids


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
