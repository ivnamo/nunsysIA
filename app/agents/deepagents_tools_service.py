from __future__ import annotations

import os
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
        self._lock = Lock()
        self.data: dict[str, Any] = {}
        self.tool_calls: list[ToolCallTrace] = []
        self.reasoning: list[str] = []
        self.sources: list[SourceName] = []
        self.fallbacks: list[str] = []

    def tools(self) -> list[Callable[..., dict[str, Any] | list[dict[str, Any]] | None]]:
        return [
            self.recall_memory,
            self.get_pending_orders_by_customer,
            self.get_orders_by_month,
            self.calculate_order_amount,
            self.list_production_orders,
            self.get_production_status_for_order_ids,
            self.query_erp_orders,
            self.query_production_orders,
            self.query_documents,
        ]

    def recall_memory(self, query: str | None = None, max_turns: int = 5) -> dict[str, Any]:
        """Recupera memoria conversacional de esta conversacion."""
        result = self._memory_tool.recall(
            MemoryRecallInput(
                query=query or self._question,
                conversation_history=self._conversation_history,
                max_turns=max_turns,
            )
        )
        with self._lock:
            self.data["memory"] = result.data
            self._record(result, "Consulta memoria conversacional")
        return result.data

    def get_pending_orders_by_customer(self, customer_id: str) -> list[dict[str, Any]]:
        """Consulta pedidos ERP pendientes por customer_id."""
        result = self._erp_tool.get_pending_orders_by_customer(
            PendingOrdersByCustomerInput(customer_id=customer_id)
        )
        with self._lock:
            self.data["erp_orders"] = result.data
            self._record(result, "Consulta ERP de pedidos pendientes")
        return result.data or []

    def get_orders_by_month(self, year: int, month: int) -> list[dict[str, Any]]:
        """Consulta pedidos ERP por ano y mes."""
        result = self._erp_tool.get_orders_by_month(
            OrdersByMonthInput(year=year, month=month)
        )
        with self._lock:
            self.data["erp_orders"] = result.data
            self.data["period"] = {"year": year, "month": month}
            self._record(result, "Consulta ERP de pedidos por mes")
        return result.data or []

    def calculate_order_amount(self, order_id: int) -> dict[str, Any] | None:
        """Calcula importe de un pedido ERP por order_id."""
        result = self._erp_tool.calculate_order_amount(OrderAmountInput(order_id=order_id))
        with self._lock:
            if result.data:
                self.data.setdefault("order_amounts", []).append(result.data)
            self._record(result, f"Consulta ERP de importe para pedido {order_id}")
        return result.data

    def list_production_orders(
        self,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lista ordenes de produccion; status puede ser blocked, delayed, finished o in_progress."""
        result = self._production_tool.list_orders(ProductionOrdersInput(status=status))
        with self._lock:
            self.data["production_orders"] = _merge_rows(
                self.data.get("production_orders"),
                result.data,
            )
            self._record(result, "Consulta API de produccion por estado")
        return result.data or []

    def get_production_status_for_order_ids(
        self,
        order_ids: list[int],
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Consulta estados de produccion para una lista de order_id."""
        result = self._production_tool.get_status_for_order_ids(
            ProductionOrdersByIdsInput(order_ids=order_ids, status=status)
        )
        with self._lock:
            self.data["production_orders"] = _merge_rows(
                self.data.get("production_orders"),
                result.data,
            )
            production_by_order = self.data.setdefault("production_by_order", {})
            for row in result.data or []:
                production_by_order[int(row["order_id"])] = row
            self._record(result, "Consulta API de produccion para pedidos referenciados")
        return result.data or []

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
        filters = _erp_filters(customer_id, order_ids, erp_status, year, month)
        result = self._erp_query_tool.query_orders(
            ERPQuerySpec(filters=filters, limit=limit)
        )
        with self._lock:
            self.data["erp_query_orders"] = _merge_rows(
                self.data.get("erp_query_orders"),
                result.data,
            )
            self._record(result, "Consulta ERP mediante filtros seguros")
        return result.data or []

    def query_production_orders(
        self,
        order_ids: list[int] | None = None,
        production_status: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Consulta produccion con filtros seguros por order_id o estado."""
        filters = _production_filters(order_ids, production_status)
        result = self._production_query_tool.query_orders(
            ProductionQuerySpec(filters=filters, limit=limit)
        )
        with self._lock:
            self.data["production_orders"] = _merge_rows(
                self.data.get("production_orders"),
                result.data,
            )
            production_by_order = self.data.setdefault("production_by_order", {})
            for row in result.data or []:
                production_by_order[int(row["order_id"])] = row
            self._record(result, "Consulta Produccion mediante filtros seguros")
        return result.data or []

    def query_documents(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.2,
        filename: str | None = None,
    ) -> dict[str, Any]:
        """Consulta documentos RAG; obligatorio para preguntas contractuales o documentales."""
        result = self._rag_tool.query(
            DocumentRAGInput(
                query=query,
                top_k=top_k,
                min_score=min_score,
                filename=filename,
            )
        )
        with self._lock:
            self.data["rag"] = result.data
            self._record(result, "Consulta RAG documental con chunks recuperados")
        return result.data or {}

    def build_response(self, answer: str | None) -> QueryResponse:
        status = self._status()
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

    def _status(self) -> QueryStatus:
        if any(call.status == "error" for call in self.tool_calls):
            return "tool_error"
        rag = self.data.get("rag")
        if isinstance(rag, dict) and rag.get("status") == "insufficient_context":
            return "insufficient_context"
        if not self.tool_calls:
            return "failed"
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
            "Si la pregunta es documental o contractual, llama query_documents.",
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

Reglas:
- Para pedidos de un cliente, usa ERP y despues produccion por order_id.
- Para bloqueos/retrasos de produccion, consulta produccion y cruza con ERP por order_id.
- Para contratos, penalizaciones, SLA o documentos, usa query_documents.
- Para follow-ups ambiguos, usa recall_memory antes de consultar fuentes actuales.
- Conserva en la respuesta los pedidos, clientes, estados, motivos y documentos relevantes.
- No uses filesystem ni herramientas de sistema para preguntas de negocio.
"""


__all__ = [
    "DeepAgentsToolsQueryService",
    "create_deepagents_tools_query_service",
]
