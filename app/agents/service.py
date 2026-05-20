from app.agents.graph import run_agent_graph
from app.core.config import Settings
from app.erp.database import create_sqlite_connection, load_seed_sql
from app.erp.repositories import NorthwindRepository
from app.production.client import ProductionAPIClient
from app.rag.ingestion import DocumentIngestionService
from app.schemas.query import QueryRequest, QueryResponse
from app.tools.erp_tool import ERPTool
from app.tools.production_tool import ProductionAPITool
from app.tools.rag_tool import DocumentRAGTool


class QueryWorkflowService:
    def __init__(
        self,
        erp_tool: ERPTool,
        production_tool: ProductionAPITool,
        rag_tool: DocumentRAGTool | None = None,
    ) -> None:
        self._erp_tool = erp_tool
        self._production_tool = production_tool
        self._rag_tool = rag_tool

    def run(self, request: QueryRequest) -> QueryResponse:
        return run_agent_graph(
            erp_tool=self._erp_tool,
            production_tool=self._production_tool,
            rag_tool=self._rag_tool,
            question=request.question,
            conversation_id=request.conversation_id,
        )


def create_query_workflow_service(
    settings: Settings,
    document_service: DocumentIngestionService,
) -> QueryWorkflowService:
    return QueryWorkflowService(
        erp_tool=_create_erp_tool(),
        production_tool=_create_production_tool(settings),
        rag_tool=DocumentRAGTool(
            vector_store=document_service.vector_store,
            embedding_model=document_service.embedding_model,
        ),
    )


def _create_erp_tool() -> ERPTool:
    connection = create_sqlite_connection(check_same_thread=False)
    load_seed_sql(connection)
    return ERPTool(NorthwindRepository(connection))


def _create_production_tool(settings: Settings) -> ProductionAPITool:
    client = ProductionAPIClient(
        base_url=settings.production_api_base_url,
        timeout=settings.production_api_timeout_seconds,
    )
    return ProductionAPITool(client)
