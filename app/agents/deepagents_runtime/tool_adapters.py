from __future__ import annotations

from typing import Any

from app.agents.deepagents_runtime.constants import _CACHE_MISS
from app.agents.deepagents_runtime.messages import (
    _rag_evidence_reasoning_steps,
    _rag_retrieval_reasoning,
)
from app.agents.deepagents_runtime.selectors import (
    _cache_key,
    _erp_filters,
    _merge_rows,
    _order_ids,
    _order_ids_from_memory_data,
    _production_filters,
    _requested_production_status,
    _unique_ints,
)
from app.tools.erp_tool import (
    CustomerByOrderInput,
    OrderAmountInput,
    OrdersByMonthInput,
    PendingOrdersByCustomerInput,
)
from app.tools.memory_tool import MemoryRecallInput
from app.tools.production_tool import ProductionOrdersByIdsInput, ProductionOrdersInput
from app.tools.query_dsl import ERPQuerySpec, ProductionQuerySpec
from app.tools.rag_tool import DocumentRAGInput


class DeepAgentsToolAdapters:
    """Tools de negocio expuestas al DeepAgent.

    Este mixin asume que la clase concreta mantiene estado de ejecucion,
    cache, trazas y helpers de registro.
    """

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

