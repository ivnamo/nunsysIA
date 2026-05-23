from __future__ import annotations

import json
import os
from typing import Any

from pydantic import ValidationError

from app.agents.deepagents_adapter import (
    BusinessWorkflow,
    DeepAgentsUnavailableError,
    build_business_deep_agent,
)
from app.core.config import Settings
from app.schemas.query import QueryRequest, QueryResponse


class DeepAgentsExecutionError(RuntimeError):
    """Raised when the sidecar DeepAgents flow cannot return QueryResponse."""


class DeepAgentsQueryService:
    """Experimental DeepAgents sidecar that preserves the audited response.

    DeepAgents decides whether to call the legacy business workflow tool, but this
    service returns the `QueryResponse` produced by that audited workflow. The
    experimental mode can therefore be compared against the principal
    `/api/query` DeepAgent without changing the stable API contract.
    """

    def __init__(
        self,
        workflow: BusinessWorkflow,
        model: str,
        gemini_api_key: str | None = None,
        openai_api_key: str | None = None,
    ) -> None:
        self._workflow = workflow
        self._model = model
        self._gemini_api_key = gemini_api_key
        self._openai_api_key = openai_api_key
        self._agent: Any | None = None

    def run(self, request: QueryRequest) -> QueryResponse:
        agent = self._get_agent()
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": _deepagents_user_message(request),
                    }
                ]
            }
        )
        return _extract_audited_query_response(result)

    def _get_agent(self) -> Any:
        if self._agent is None:
            self._prime_provider_environment()
            self._agent = build_business_deep_agent(
                workflow=self._workflow,
                model=self._model,
                name="nunsys-experimental-deepagents-query",
            )
        return self._agent

    def _prime_provider_environment(self) -> None:
        _set_env_if_missing("GEMINI_API_KEY", self._gemini_api_key)
        _set_env_if_missing("OPENAI_API_KEY", self._openai_api_key)


def create_deepagents_query_service(
    settings: Settings,
    workflow: BusinessWorkflow,
) -> DeepAgentsQueryService:
    return DeepAgentsQueryService(
        workflow=workflow,
        model=settings.deepagents_model,
        gemini_api_key=settings.gemini_api_key,
        openai_api_key=settings.openai_api_key,
    )


def _deepagents_user_message(request: QueryRequest) -> str:
    conversation_id = request.conversation_id or ""
    citation_previews = "true" if request.include_citation_previews else "false"
    return "\n".join(
        [
            "Ejecuta la consulta de negocio usando la tool consultar_flujo_agentic.",
            "",
            f"question: {request.question}",
            f"conversation_id: {conversation_id}",
            f"include_citation_previews: {citation_previews}",
            "",
            "Devuelve una respuesta breve basada solo en el resultado de la tool.",
        ]
    )


def _extract_audited_query_response(result: Any) -> QueryResponse:
    if isinstance(result, QueryResponse):
        return result

    structured_response = _mapping_value(result, "structured_response")
    if structured_response is not None:
        response = _coerce_query_response(structured_response)
        if response is not None:
            return response

    messages = _mapping_value(result, "messages") or []
    for message in reversed(messages):
        response = _coerce_query_response(_message_content(message))
        if response is not None:
            return response

    raise DeepAgentsExecutionError(
        "Deep Agents no devolvio una QueryResponse auditable desde "
        "consultar_flujo_agentic."
    )


def _coerce_query_response(value: Any) -> QueryResponse | None:
    if isinstance(value, QueryResponse):
        return value

    if isinstance(value, dict):
        try:
            return QueryResponse.model_validate(value)
        except ValidationError:
            return None

    if isinstance(value, str):
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            return None
        return _coerce_query_response(payload)

    if isinstance(value, list):
        text_parts = []
        for item in value:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                text_parts.append(item["text"])
        if text_parts:
            return _coerce_query_response("\n".join(text_parts))

    return None


def _mapping_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _message_content(message: Any) -> Any:
    return _mapping_value(message, "content")


def _set_env_if_missing(name: str, value: str | None) -> None:
    if value and not os.getenv(name):
        os.environ[name] = value


__all__ = [
    "DeepAgentsExecutionError",
    "DeepAgentsQueryService",
    "DeepAgentsUnavailableError",
    "create_deepagents_query_service",
]
