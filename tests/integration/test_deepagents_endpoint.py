from fastapi.testclient import TestClient

from app.agents.deepagents_service import DeepAgentsUnavailableError
from app.api import routes_deepagents
from app.api.routes_deepagents import (
    _cached_deepagents_query_service,
    _cached_deepagents_tools_query_service,
    get_deepagents_query_service,
    get_deepagents_tools_query_service,
)
from app.core.config import get_settings
from app.main import create_app
from app.schemas.query import QueryRequest, QueryResponse


class _FakeDeepAgentsService:
    def __init__(
        self,
        response: QueryResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.requests: list[QueryRequest] = []

    def run(self, request: QueryRequest) -> QueryResponse:
        self.requests.append(request)
        if self.error:
            raise self.error
        assert self.response is not None
        return self.response


def test_deepagents_endpoint_is_hidden_when_experiment_is_disabled(monkeypatch) -> None:
    get_settings.cache_clear()
    _cached_deepagents_query_service.cache_clear()
    monkeypatch.setenv("ENABLE_DEEPAGENTS_EXPERIMENT", "false")
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/experimental/deepagents/query",
        json={"question": "Que pedidos tiene ALFKI?"},
    )

    assert response.status_code == 404
    assert "no esta habilitado" in response.json()["detail"]
    get_settings.cache_clear()
    _cached_deepagents_query_service.cache_clear()


def test_deepagents_endpoint_returns_query_response_from_service() -> None:
    app = create_app()
    service = _FakeDeepAgentsService(
        response=QueryResponse(
            answer="Respuesta experimental",
            sources=["ERP"],
            reasoning=["Consulta via Deep Agents"],
            tool_calls=[],
            fallbacks=[],
            confidence=0.9,
            status="completed",
            data={"erp_order_ids": [10248]},
        )
    )
    app.dependency_overrides[get_deepagents_query_service] = lambda: service
    client = TestClient(app)

    response = client.post(
        "/api/experimental/deepagents/query",
        json={"question": "Que pedidos tiene ALFKI?", "conversation_id": "deep-1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Respuesta experimental"
    assert payload["status"] == "completed"
    assert service.requests == [
        QueryRequest(
            question="Que pedidos tiene ALFKI?",
            conversation_id="deep-1",
        )
    ]


def test_deepagents_tools_endpoint_returns_query_response_from_service() -> None:
    app = create_app()
    service = _FakeDeepAgentsService(
        response=QueryResponse(
            answer="Respuesta tools experimental",
            sources=["ERP", "Produccion"],
            reasoning=["Consulta directa via Deep Agents"],
            tool_calls=[],
            fallbacks=[],
            confidence=0.75,
            status="completed",
            data={"erp_order_ids": [10248]},
        )
    )
    app.dependency_overrides[get_deepagents_tools_query_service] = lambda: service
    client = TestClient(app)

    response = client.post(
        "/api/experimental/deepagents/tools/query",
        json={"question": "Que pedidos tiene ALFKI?", "conversation_id": "deep-tools"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Respuesta tools experimental"
    assert payload["sources"] == ["ERP", "Produccion"]
    assert service.requests == [
        QueryRequest(
            question="Que pedidos tiene ALFKI?",
            conversation_id="deep-tools",
        )
    ]


def test_deepagents_endpoint_returns_503_when_package_is_missing(
    monkeypatch,
) -> None:
    get_settings.cache_clear()
    _cached_deepagents_query_service.cache_clear()
    _cached_deepagents_tools_query_service.cache_clear()
    monkeypatch.setenv("ENABLE_DEEPAGENTS_EXPERIMENT", "true")
    monkeypatch.setattr(routes_deepagents, "deepagents_is_available", lambda: False)
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/experimental/deepagents/query",
        json={"question": "Que pedidos tiene ALFKI?"},
    )

    assert response.status_code == 503
    assert "deepagents no esta instalado" in response.json()["detail"]
    get_settings.cache_clear()
    _cached_deepagents_query_service.cache_clear()
    _cached_deepagents_tools_query_service.cache_clear()


def test_deepagents_endpoint_returns_503_when_dependency_is_missing() -> None:
    app = create_app()
    app.dependency_overrides[get_deepagents_query_service] = lambda: _FakeDeepAgentsService(
        error=DeepAgentsUnavailableError("deepagents no esta instalado")
    )
    client = TestClient(app)

    response = client.post(
        "/api/experimental/deepagents/query",
        json={"question": "Que pedidos tiene ALFKI?"},
    )

    assert response.status_code == 503
    assert "deepagents no esta instalado" in response.json()["detail"]
