from __future__ import annotations

from importlib.util import find_spec
from typing import Any, Protocol

from app.schemas.query import QueryRequest, QueryResponse


DEEPAGENTS_PACKAGE = "deepagents"


class DeepAgentsUnavailableError(RuntimeError):
    """Raised when the optional Deep Agents adapter is requested but unavailable."""


class BusinessWorkflow(Protocol):
    def run(self, request: QueryRequest) -> QueryResponse:
        """Execute the audited business workflow."""


def deepagents_is_available() -> bool:
    return find_spec(DEEPAGENTS_PACKAGE) is not None


def build_business_deep_agent(
    workflow: BusinessWorkflow,
    model: str,
    *,
    name: str = "nunsys-business-deep-agent",
) -> Any:
    """Create an optional Deep Agents sidecar around the existing workflow.

    The production path remains the explicit LangGraph workflow. This adapter is a
    compatibility sidecar for environments that require the `deepagents` package.
    """
    if not deepagents_is_available():
        raise DeepAgentsUnavailableError(
            "deepagents no esta instalado. Instala requirements-deepagents.txt "
            "en un entorno compatible para activar este adapter opcional."
        )

    try:
        from deepagents import create_deep_agent
    except ImportError as exc:
        raise DeepAgentsUnavailableError(
            "deepagents esta instalado pero no puede importarse correctamente. "
            "Revisa que el entorno use las dependencias de requirements-deepagents.txt."
        ) from exc

    return create_deep_agent(
        model=model,
        tools=[_build_business_workflow_tool(workflow)],
        system_prompt=_DEEP_AGENT_SYSTEM_PROMPT,
        name=name,
    )


def _build_business_workflow_tool(workflow: BusinessWorkflow):
    def consultar_flujo_agentic(
        question: str,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        """Consulta el workflow agentic empresarial auditado."""
        response = workflow.run(
            QueryRequest(
                question=question,
                conversation_id=conversation_id,
            )
        )
        return response.model_dump(mode="json")

    return consultar_flujo_agentic


_DEEP_AGENT_SYSTEM_PROMPT = """Eres un sidecar Deep Agents para la POC nunsysIA.

Tu unica fuente de verdad de negocio es la tool `consultar_flujo_agentic`.
Usala para responder preguntas sobre ERP, produccion, documentos o memoria
conversacional. No inventes datos ni sustituyas el workflow principal: resume
la respuesta devuelta por la tool y conserva el estado, fuentes, tool calls y
fallbacks cuando sean relevantes para auditoria.
"""
