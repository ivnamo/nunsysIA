import asyncio

from app.agents.deepagents_tools_service import DeepAgentsToolsQueryService
from app.schemas.query import AgentMode, QueryRequest


class DeepAgentService:
    """Primary agentic engine backed by LangChain DeepAgents."""

    def __init__(self, service: DeepAgentsToolsQueryService) -> None:
        self._service = service

    async def query(
        self,
        question: str,
        conversation_id: str | None = None,
        include_citation_previews: bool = False,
    ):
        request = QueryRequest(
            question=question,
            conversation_id=conversation_id,
            mode=AgentMode.DEEPAGENT,
            include_citation_previews=include_citation_previews,
        )
        return await asyncio.to_thread(self._service.run, request)

