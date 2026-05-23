import asyncio

from app.agents.deepagents_service import DeepAgentsQueryService
from app.schemas.query import AgentMode, QueryRequest


class DeepAgentSidecarService:
    """Experimental sidecar where DeepAgents delegates to the legacy workflow."""

    def __init__(self, service: DeepAgentsQueryService) -> None:
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
            mode=AgentMode.DEEPAGENT_SIDECAR,
            include_citation_previews=include_citation_previews,
        )
        return await asyncio.to_thread(self._service.run, request)

