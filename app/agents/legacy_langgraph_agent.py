from app.agents.service import QueryWorkflowService
from app.schemas.query import AgentMode, QueryRequest


class LegacyLangGraphService:
    """Experimental compatibility wrapper around the previous LangGraph flow."""

    def __init__(self, workflow: QueryWorkflowService) -> None:
        self._workflow = workflow

    async def query(
        self,
        question: str,
        conversation_id: str | None = None,
        include_citation_previews: bool = False,
    ):
        return self._workflow.run(
            QueryRequest(
                question=question,
                conversation_id=conversation_id,
                mode=AgentMode.LEGACY_LANGGRAPH,
                include_citation_previews=include_citation_previews,
            )
        )

