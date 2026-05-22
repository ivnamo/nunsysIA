from __future__ import annotations

import os
import unicodedata
from dataclasses import dataclass
from threading import Lock
from typing import Any, Callable

from app.agents.deepagents_adapter import DeepAgentsUnavailableError, deepagents_is_available
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


@dataclass(frozen=True)
class _ToolPolicy:
    needs_memory: bool
    needs_documents: bool
    needs_penalty: bool
    needs_customer_orders: bool
    needs_production: bool
    needs_blocked_cross: bool
    needs_erp: bool
    rag_budget: int


class DeepAgentsToolsQueryService:
    """Experimental Deep Agents flow with direct access to deterministic tools."""

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
        agent = self._agent_builder(
            model=self._model,
            tools=execution.tools(),
            system_prompt=_DIRECT_TOOLS_SYSTEM_PROMPT,
            name="nunsys-experimental-deepagents-tools-query",
        )
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": _direct_tools_user_message(request),
                    }
                ]
            }
        )
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

    def tools(self) -> list[Callable[..., dict[str, Any] | list[dict[str, Any]] | None]]:
        tools: list[Callable[..., Any]] = []
        if self._policy.needs_memory:
            tools.append(self.resolve_referenced_orders_with_erp_and_production)
            tools.append(self.recall_memory)
        if self._policy.needs_penalty:
            tools.append(self.assess_penalty_risk_for_orders)
        if self._policy.needs_customer_orders and self._policy.needs_production:
            tools.append(self.get_customer_pending_orders_with_production)
        if self._policy.needs_blocked_cross:
            tools.append(self.get_blocked_production_orders_with_erp)
        if self._policy.needs_documents and not self._policy.needs_penalty:
            tools.append(self.answer_document_question_with_citations)
        if self._policy.needs_erp:
            tools.extend(
                [
                    self.get_pending_orders_by_customer,
                    self.get_orders_by_month,
                    self.calculate_order_amount,
                    self.query_erp_orders,
                ]
            )
        if self._policy.needs_production:
            tools.extend(
                [
                    self.list_production_orders,
                    self.get_production_status_for_order_ids,
                    self.query_production_orders,
                ]
            )
        if self._policy.needs_documents:
            tools.append(self.query_documents)
        if not tools:
            tools.extend([self.query_erp_orders, self.query_production_orders])
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

    def assess_penalty_risk_for_orders(self) -> dict[str, Any]:
        """Tool compuesta: ERP, produccion y contrato para riesgo de penalizacion."""
        erp_orders = self.query_erp_orders(limit=20)
        order_ids = _order_ids(erp_orders)
        production_orders = (
            self.query_production_orders(order_ids=order_ids, limit=20)
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
        memory = self.recall_memory(query=query or self._question)
        facts = memory.get("facts") if isinstance(memory, dict) else {}
        facts = facts if isinstance(facts, dict) else {}
        order_ids = _unique_ints(facts.get("order_ids") or [])
        customer_id = facts.get("customer_id")

        erp_orders: list[dict[str, Any]] = []
        if order_ids:
            erp_orders = self.query_erp_orders(order_ids=order_ids)
        elif isinstance(customer_id, str) and customer_id.strip():
            erp_orders = self.get_pending_orders_by_customer(customer_id)
            order_ids = _order_ids(erp_orders)

        production_orders = (
            self.get_production_status_for_order_ids(order_ids) if order_ids else []
        )
        return {
            "memory": memory,
            "erp_orders": erp_orders,
            "production_orders": production_orders,
        }

    def recall_memory(self, query: str | None = None, max_turns: int = 5) -> dict[str, Any]:
        """Recupera memoria conversacional de esta conversacion."""
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

    def list_production_orders(
        self,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lista ordenes de produccion; status puede ser blocked, delayed, finished o in_progress."""
        cache_key = _cache_key("list_production_orders", {"status": status})
        cached = self._cached_data(cache_key)
        if cached is not _CACHE_MISS:
            return cached
        result = self._production_tool.list_orders(ProductionOrdersInput(status=status))
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
        cache_key = _cache_key(
            "get_production_status_for_order_ids",
            {"order_ids": normalized_order_ids, "status": status},
        )
        cached = self._cached_data(cache_key)
        if cached is not _CACHE_MISS:
            return cached
        result = self._production_tool.get_status_for_order_ids(
            ProductionOrdersByIdsInput(order_ids=normalized_order_ids, status=status)
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
        cache_key = _cache_key(
            "query_production_orders",
            {
                "order_ids": normalized_order_ids,
                "production_status": production_status,
                "limit": limit,
            },
        )
        cached = self._cached_data(cache_key)
        if cached is not _CACHE_MISS:
            return cached
        filters = _production_filters(normalized_order_ids, production_status)
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
            self._record(result, "Consulta RAG documental con chunks recuperados")
        return data

    def _cached_data(self, key: Any) -> Any:
        with self._lock:
            return self._cache.get(key, _CACHE_MISS)

    def _claim_rag_budget(self) -> bool:
        with self._lock:
            if self._rag_calls >= self._policy.rag_budget:
                return False
            self._rag_calls += 1
            return True

    def build_response(self, answer: str | None) -> QueryResponse:
        status = self._status(answer)
        normalized_answer = _normalized_answer(answer, status)
        return QueryResponse(
            answer=normalized_answer,
            sources=list(self.sources),
            reasoning=sanitize_reasoning(self.reasoning),
            tool_calls=sanitize_tool_calls(self.tool_calls),
            fallbacks=list(self.fallbacks),
            confidence=_confidence(status),
            status=status,
            data=build_public_data_summary(
                self.data,
                include_rag_text_preview=self._include_citation_previews,
            ),
            failure_reason=None,
        )

    def _record(self, result: ToolResult, reasoning: str) -> None:
        self.tool_calls.append(result.tool_call)
        if result.tool_call.source not in self.sources:
            self.sources.append(result.tool_call.source)
        self.reasoning.append(reasoning)
        self._add_fallbacks(result)

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
            and not (answer and answer.strip())
        ):
            return "insufficient_context"
        return "completed"


def _create_deep_agent(**kwargs: Any) -> Any:
    if not deepagents_is_available():
        raise DeepAgentsUnavailableError(
            "deepagents no esta instalado. Instala requirements-deepagents.txt "
            "en un entorno compatible para activar este flujo experimental."
        )
    try:
        from deepagents import create_deep_agent
    except ImportError as exc:
        raise DeepAgentsUnavailableError(
            "deepagents esta instalado pero no puede importarse correctamente."
        ) from exc
    return create_deep_agent(**kwargs)


def _direct_tools_user_message(request: QueryRequest) -> str:
    return "\n".join(
        [
            f"Pregunta: {request.question}",
            f"conversation_id: {request.conversation_id or ''}",
            "Usa solo las tools disponibles para obtener datos antes de responder.",
            "Si aparece una tool compuesta, usala antes que repetir primitives.",
            "No repitas consultas con los mismos argumentos.",
            "Si la pregunta es documental o contractual, haz una sola consulta documental.",
            "Si necesitas cruzar ERP y produccion, cruza por order_id.",
        ]
    )


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


def _mapping_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _normalized_answer(answer: str | None, status: QueryStatus) -> str:
    if answer and answer.strip():
        return answer.strip()
    if status == "insufficient_context":
        return (
            "No he encontrado informacion en los documentos disponibles para "
            "responder a esa pregunta con fiabilidad."
        )
    if status == "tool_error":
        return "No se pudo completar la consulta por un error en una fuente."
    return "Deep Agents no genero una respuesta final usable para esta consulta."


def _confidence(status: QueryStatus) -> float | None:
    if status == "completed":
        return 0.75
    if status == "insufficient_context":
        return 0.45
    return None


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
    needs_penalty = _contains_any(text, ("penaliz", "sla"))
    needs_documents = needs_penalty or _contains_any(
        text,
        (
            "contrato",
            "document",
            "clausul",
            "criptomon",
            "bitcoin",
            "divisa",
            "plazo contractual",
            "logistic",
        ),
    )
    needs_customer_orders = "alfki" in text or (
        "cliente" in text and "pedido" in text
    )
    needs_blocked_cross = _contains_any(text, ("bloque", "retras")) and _contains_any(
        text,
        ("produccion", "erp", "cliente", "cruza", "cruce"),
    )
    needs_production = _contains_any(
        text,
        ("produccion", "estado", "bloque", "retras", "fabricacion"),
    )
    needs_erp = needs_customer_orders or _contains_any(text, ("erp", "pedido"))
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
        needs_documents=needs_documents,
        needs_penalty=needs_penalty,
        needs_customer_orders=needs_customer_orders,
        needs_production=needs_production,
        needs_blocked_cross=needs_blocked_cross,
        needs_erp=needs_erp,
        rag_budget=1 if needs_documents else 0,
    )


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _looks_like_follow_up(text: str) -> bool:
    return text.startswith(("y ", "ademas", "tambien")) or _contains_any(
        text,
        (" esos ", " esas ", " ellos ", " ellas ", " anterior", "antes"),
    )


def _has_explicit_business_anchor(text: str) -> bool:
    return bool(_order_ids_from_text(text)) or _contains_any(
        text,
        ("alfki", "bonap", "anatr", "cliente", "pedido", "contrato", "document"),
    )


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(character for character in normalized if not unicodedata.combining(character))


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


_DIRECT_TOOLS_SYSTEM_PROMPT = """Eres un Deep Agent experimental de nunsysIA.

Tienes acceso directo a tools deterministas de ERP, produccion, memoria y RAG.
No inventes datos: responde solo con datos devueltos por las tools.
El runtime solo te expone las tools necesarias para la intencion detectada.

Reglas:
- Prefiere las tools compuestas cuando esten disponibles; ya hacen los cruces seguros.
- Para pedidos de un cliente, usa ERP y despues produccion por order_id.
- Para bloqueos/retrasos de produccion, consulta produccion y cruza con ERP por order_id.
- Para contratos, penalizaciones, SLA o documentos, usa una unica consulta documental.
- Para follow-ups ambiguos sobre pedidos, usa resolve_referenced_orders_with_erp_and_production.
- Conserva en la respuesta los pedidos, clientes, estados, motivos y documentos relevantes.
- No uses filesystem ni herramientas de sistema para preguntas de negocio.
"""


__all__ = [
    "DeepAgentsToolsQueryService",
    "create_deepagents_tools_query_service",
]
