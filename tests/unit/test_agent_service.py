import pytest

from app.core.config import Settings
from app.schemas.query import AgentMode
from app.schemas.query import QueryResponse
from app.services.agent_service import LazyAgentService, configured_agent_mode


@pytest.mark.asyncio
async def test_lazy_agent_service_builds_alternative_flow_only_on_first_query() -> None:
    calls = []

    def factory() -> "_Service":
        calls.append("created")
        return _Service()

    lazy_service = LazyAgentService(factory)

    assert calls == []
    first = await lazy_service.query("Pregunta")
    second = await lazy_service.query("Otra pregunta")

    assert first.answer == "ok"
    assert second.answer == "ok"
    assert calls == ["created"]


def test_configured_agent_mode_falls_back_to_deepagent_on_invalid_value() -> None:
    assert configured_agent_mode(Settings(agent_mode="otro")) == AgentMode.DEEPAGENT


class _Service:
    async def query(
        self,
        question: str,
        conversation_id: str | None = None,
        include_citation_previews: bool = False,
    ) -> QueryResponse:
        return QueryResponse(answer="ok")
