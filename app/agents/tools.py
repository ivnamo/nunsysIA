from app.core.tracing import SourceName


DEEP_AGENT_TOOL_SOURCES: dict[str, SourceName] = {
    "query_erp_orders": "ERP",
    "query_erp_customer_summary": "ERP",
    "get_pending_orders_by_customer": "ERP",
    "get_orders_by_month": "ERP",
    "calculate_order_amount": "ERP",
    "get_customer_for_order": "ERP",
    "get_customers_for_order_ids": "ERP",
    "query_production_status": "Produccion",
    "query_production_orders": "Produccion",
    "query_blocked_orders": "Produccion",
    "list_production_orders": "Produccion",
    "get_production_status_for_order_ids": "Produccion",
    "search_documents": "Documentos",
    "summarize_document_context": "Documentos",
    "query_documents": "Documentos",
    "recall_memory": "Memoria",
}


def source_for_tool(tool_name: str) -> SourceName | None:
    return DEEP_AGENT_TOOL_SOURCES.get(tool_name)

