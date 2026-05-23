from __future__ import annotations

import inspect
from typing import Any, Protocol

from app.schemas.query import AgentMode, QueryResponse
from app.services.response_normalizer import ResponseNormalizer


class AgentModeUnavailableError(RuntimeError):
    pass


class AgentService(Protocol):
    async def query(
        self,
        question: str,
        conversation_id: str | None = None,
        include_citation_previews: bool = False,
    ) -> Any:
        ...


class AgentRouter:
    def __init__(
        self,
        deepagent_service: AgentService,
        response_normalizer: ResponseNormalizer,
        sidecar_service: AgentService | None = None,
        legacy_service: AgentService | None = None,
        default_mode: AgentMode = AgentMode.DEEPAGENT,
    ) -> None:
        self._deepagent_service = deepagent_service
        self._sidecar_service = sidecar_service
        self._legacy_service = legacy_service
        self._response_normalizer = response_normalizer
        self._default_mode = default_mode

    async def query(
        self,
        question: str,
        conversation_id: str | None = None,
        mode: AgentMode | None = None,
        include_citation_previews: bool = False,
    ) -> QueryResponse:
        selected_mode = mode or self._default_mode
        service = self._service_for_mode(selected_mode)
        raw_result = await _call_service(
            service=service,
            question=question,
            conversation_id=conversation_id,
            include_citation_previews=include_citation_previews,
        )
        return self._response_normalizer.normalize(raw_result, selected_mode)

    def _service_for_mode(self, mode: AgentMode) -> AgentService:
        if mode == AgentMode.DEEPAGENT:
            return self._deepagent_service
        if mode == AgentMode.DEEPAGENT_SIDECAR:
            if self._sidecar_service is None:
                raise AgentModeUnavailableError(
                    "El modo deepagent_sidecar no esta disponible en este entorno."
                )
            return self._sidecar_service
        if mode == AgentMode.LEGACY_LANGGRAPH:
            if self._legacy_service is None:
                raise AgentModeUnavailableError(
                    "El modo legacy_langgraph no esta disponible en este entorno."
                )
            return self._legacy_service
        raise AgentModeUnavailableError(f"Modo agentic no soportado: {mode!r}.")


async def _call_service(
    *,
    service: AgentService,
    question: str,
    conversation_id: str | None,
    include_citation_previews: bool,
) -> Any:
    result = service.query(
        question=question,
        conversation_id=conversation_id,
        include_citation_previews=include_citation_previews,
    )
    if inspect.isawaitable(result):
        return await result
    return result

