from __future__ import annotations

import inspect
from typing import Any, Callable

from app.agents.deep_agent import DeepAgentService
from app.agents.deepagents_service import create_deepagents_query_service
from app.agents.deepagents_tools_service import create_deepagents_tools_query_service
from app.agents.legacy_langgraph_agent import LegacyLangGraphService
from app.agents.router import AgentRouter
from app.agents.service import create_query_workflow_service
from app.agents.sidecar_agent import DeepAgentSidecarService
from app.core.config import Settings
from app.rag.ingestion import DocumentIngestionService
from app.schemas.query import AgentMode
from app.services.erp_service import create_erp_tools
from app.services.production_service import create_production_tools
from app.services.rag_service import create_rag_tool
from app.services.response_normalizer import ResponseNormalizer
from app.services.trace_service import TraceService


class LazyAgentService:
    """Carga flujos alternativos solo cuando se solicitan explicitamente."""

    def __init__(self, factory: Callable[[], Any]) -> None:
        self._factory = factory
        self._service: Any | None = None

    async def query(
        self,
        question: str,
        conversation_id: str | None = None,
        include_citation_previews: bool = False,
    ) -> Any:
        service = self._get_service()
        result = service.query(
            question=question,
            conversation_id=conversation_id,
            include_citation_previews=include_citation_previews,
        )
        if inspect.isawaitable(result):
            return await result
        return result

    def _get_service(self) -> Any:
        if self._service is None:
            self._service = self._factory()
        return self._service


def create_agent_router(
    settings: Settings,
    document_service: DocumentIngestionService,
) -> AgentRouter:
    erp_tool, erp_query_tool = create_erp_tools()
    production_tool, production_query_tool = create_production_tools(settings)
    rag_tool = create_rag_tool(document_service)
    trace_service = TraceService()
    response_normalizer = ResponseNormalizer(trace_service=trace_service)

    deepagent_service = DeepAgentService(
        create_deepagents_tools_query_service(
            settings=settings,
            erp_tool=erp_tool,
            production_tool=production_tool,
            erp_query_tool=erp_query_tool,
            production_query_tool=production_query_tool,
            rag_tool=rag_tool,
        )
    )

    legacy_workflow_cache: dict[str, Any] = {}

    def legacy_workflow() -> Any:
        workflow = legacy_workflow_cache.get("workflow")
        if workflow is None:
            workflow = create_query_workflow_service(
                settings=settings,
                document_service=document_service,
            )
            legacy_workflow_cache["workflow"] = workflow
        return workflow

    legacy_service = LazyAgentService(lambda: LegacyLangGraphService(legacy_workflow()))
    sidecar_service = LazyAgentService(
        lambda: DeepAgentSidecarService(
            create_deepagents_query_service(
                settings=settings,
                workflow=legacy_workflow(),
            )
        )
    )

    return AgentRouter(
        deepagent_service=deepagent_service,
        sidecar_service=sidecar_service,
        legacy_service=legacy_service,
        response_normalizer=response_normalizer,
        default_mode=configured_agent_mode(settings),
    )


def configured_agent_mode(settings: Settings) -> AgentMode:
    try:
        return AgentMode(settings.agent_mode or AgentMode.DEEPAGENT.value)
    except ValueError:
        return AgentMode.DEEPAGENT

