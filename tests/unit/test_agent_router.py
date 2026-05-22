import pytest

from app.agents.router import AgentModeUnavailableError, AgentRouter
from app.schemas.query import AgentMode, QueryResponse
from app.services.response_normalizer import ResponseNormalizer


@pytest.mark.asyncio
async def test_agent_router_defaults_to_deepagent() -> None:
    service = _Service("deep")
    router = AgentRouter(
        deepagent_service=service,
        response_normalizer=ResponseNormalizer(),
    )

    response = await router.query("Pregunta", mode=None)

    assert response.answer == "deep"
    assert service.calls == [("Pregunta", None, False)]
    assert response.metadata["agent_mode"] == "deepagent"


@pytest.mark.asyncio
async def test_agent_router_raises_clear_error_for_missing_experimental_mode() -> None:
    router = AgentRouter(
        deepagent_service=_Service("deep"),
        response_normalizer=ResponseNormalizer(),
    )

    with pytest.raises(AgentModeUnavailableError, match="legacy_langgraph"):
        await router.query("Pregunta", mode=AgentMode.LEGACY_LANGGRAPH)


class _Service:
    def __init__(self, answer: str) -> None:
        self._answer = answer
        self.calls = []

    async def query(
        self,
        question: str,
        conversation_id: str | None = None,
        include_citation_previews: bool = False,
    ) -> QueryResponse:
        self.calls.append((question, conversation_id, include_citation_previews))
        return QueryResponse(
            answer=self._answer,
            sources=["ERP"],
            reasoning=["Consulta"],
        )

