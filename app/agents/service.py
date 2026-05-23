from app.agents.graph import run_agent_graph
from app.core.config import Settings
from app.core.llm import ChatModel, LLMProviderError, create_chat_model
from app.rag.ingestion import DocumentIngestionService
from app.schemas.query import QueryRequest, QueryResponse
from app.services.erp_service import create_erp_tools
from app.services.production_service import create_production_tools
from app.services.rag_service import create_rag_tool
from app.tools.erp_query_tool import ERPQueryTool
from app.tools.erp_tool import ERPTool
from app.tools.memory_tool import ConversationMemoryStore
from app.tools.production_query_tool import ProductionQueryTool
from app.tools.production_tool import ProductionAPITool
from app.tools.rag_tool import DocumentRAGTool


class QueryWorkflowService:
    def __init__(
        self,
        erp_tool: ERPTool,
        production_tool: ProductionAPITool,
        erp_query_tool: ERPQueryTool | None = None,
        production_query_tool: ProductionQueryTool | None = None,
        rag_tool: DocumentRAGTool | None = None,
        chat_model: ChatModel | None = None,
        llm_timeout_seconds: float = 8.0,
        memory_store: ConversationMemoryStore | None = None,
    ) -> None:
        self._erp_tool = erp_tool
        self._production_tool = production_tool
        self._erp_query_tool = erp_query_tool
        self._production_query_tool = production_query_tool
        self._rag_tool = rag_tool
        self._chat_model = chat_model
        self._llm_timeout_seconds = llm_timeout_seconds
        self._memory_store = memory_store or ConversationMemoryStore()

    def run(self, request: QueryRequest) -> QueryResponse:
        conversation_history = self._memory_store.history(request.conversation_id)
        response = run_agent_graph(
            erp_tool=self._erp_tool,
            production_tool=self._production_tool,
            erp_query_tool=self._erp_query_tool,
            production_query_tool=self._production_query_tool,
            rag_tool=self._rag_tool,
            chat_model=self._chat_model,
            llm_timeout_seconds=self._llm_timeout_seconds,
            question=request.question,
            conversation_id=request.conversation_id,
            conversation_history=conversation_history,
            include_citation_previews=request.include_citation_previews,
        )
        self._memory_store.remember(
            conversation_id=request.conversation_id,
            question=request.question,
            response=response,
        )
        return response


def create_query_workflow_service(
    settings: Settings,
    document_service: DocumentIngestionService,
) -> QueryWorkflowService:
    try:
        chat_model = create_chat_model(settings)
    except LLMProviderError:
        chat_model = None

    erp_tool, erp_query_tool = create_erp_tools()
    production_tool, production_query_tool = create_production_tools(settings)

    return QueryWorkflowService(
        erp_tool=erp_tool,
        production_tool=production_tool,
        erp_query_tool=erp_query_tool,
        production_query_tool=production_query_tool,
        rag_tool=create_rag_tool(document_service),
        chat_model=chat_model,
        llm_timeout_seconds=settings.llm_timeout_seconds,
    )

