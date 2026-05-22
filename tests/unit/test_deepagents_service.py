import json

import pytest

from app.agents import deepagents_service
from app.agents.deepagents_service import (
    DeepAgentsExecutionError,
    DeepAgentsQueryService,
    _extract_audited_query_response,
)
from app.schemas.query import QueryRequest, QueryResponse


class _FakeWorkflow:
    pass


class _FakeAgent:
    def __init__(self, result: dict) -> None:
        self.result = result
        self.invocations: list[dict] = []

    def invoke(self, payload: dict) -> dict:
        self.invocations.append(payload)
        return self.result


class _Message:
    def __init__(self, content: str) -> None:
        self.content = content


def test_deepagents_query_service_returns_audited_tool_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audited = QueryResponse(
        answer="Respuesta auditada",
        sources=["ERP"],
        reasoning=["Consulta ERP"],
        tool_calls=[],
        fallbacks=[],
        confidence=0.9,
        status="completed",
        data={"erp_order_ids": [10248]},
    )
    fake_agent = _FakeAgent(
        {
            "messages": [
                _Message("texto intermedio"),
                _Message(json.dumps(audited.model_dump(mode="json"))),
            ]
        }
    )

    def fake_build_business_deep_agent(**kwargs):
        assert kwargs["model"] == "google_genai:gemini-3.5-flash"
        return fake_agent

    monkeypatch.setattr(
        deepagents_service,
        "build_business_deep_agent",
        fake_build_business_deep_agent,
    )
    service = DeepAgentsQueryService(
        workflow=_FakeWorkflow(),
        model="google_genai:gemini-3.5-flash",
    )

    response = service.run(
        QueryRequest(
            question="Pedidos de ALFKI",
            conversation_id="demo-deep",
            include_citation_previews=True,
        )
    )

    assert response == audited
    prompt = fake_agent.invocations[0]["messages"][0]["content"]
    assert "Pedidos de ALFKI" in prompt
    assert "conversation_id: demo-deep" in prompt
    assert "include_citation_previews: true" in prompt


def test_extract_audited_query_response_rejects_missing_tool_payload() -> None:
    with pytest.raises(DeepAgentsExecutionError, match="QueryResponse auditable"):
        _extract_audited_query_response({"messages": [_Message("sin json valido")]})
