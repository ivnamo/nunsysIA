import importlib.util

import pytest

from app.agents import deepagents_adapter
from app.agents.deepagents_adapter import (
    DeepAgentsUnavailableError,
    _build_business_workflow_tool,
    build_business_deep_agent,
)
from app.schemas.query import QueryRequest, QueryResponse


class FakeWorkflow:
    def __init__(self) -> None:
        self.requests: list[QueryRequest] = []

    def run(self, request: QueryRequest) -> QueryResponse:
        self.requests.append(request)
        return QueryResponse(
            answer="Respuesta auditada",
            sources=["ERP"],
            reasoning=["Consulta ERP"],
            tool_calls=[],
            fallbacks=[],
            confidence=0.9,
            status="completed",
            data={"order_ids": [10248]},
            failure_reason=None,
        )


def test_business_workflow_tool_delegates_to_query_workflow() -> None:
    workflow = FakeWorkflow()
    tool = _build_business_workflow_tool(workflow)

    result = tool("Pedidos pendientes de ALFKI", conversation_id="demo-001")

    assert workflow.requests == [
        QueryRequest(
            question="Pedidos pendientes de ALFKI",
            conversation_id="demo-001",
        )
    ]
    assert result["answer"] == "Respuesta auditada"
    assert result["sources"] == ["ERP"]
    assert result["status"] == "completed"
    assert result["data"] == {"order_ids": [10248]}


def test_build_business_deep_agent_fails_cleanly_when_dependency_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_find_spec(package: str):
        assert package == deepagents_adapter.DEEPAGENTS_PACKAGE
        return None

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    monkeypatch.setattr(deepagents_adapter, "find_spec", fake_find_spec)

    with pytest.raises(DeepAgentsUnavailableError, match="deepagents no esta instalado"):
        build_business_deep_agent(FakeWorkflow(), model="google_genai:gemini-3.5-flash")
