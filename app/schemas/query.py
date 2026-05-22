from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.tracing import SourceName, ToolCallTrace


class AgentMode(str, Enum):
    DEEPAGENT = "deepagent"
    DEEPAGENT_SIDECAR = "deepagent_sidecar"
    LEGACY_LANGGRAPH = "legacy_langgraph"


QueryStatus = Literal[
    "completed",
    "partial_answer",
    "insufficient_context",
    "tool_error",
    "failed",
    "unsupported",
    "needs_clarification",
]


class QueryRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1)
    conversation_id: str | None = None
    mode: AgentMode | None = AgentMode.DEEPAGENT
    include_citation_previews: bool = Field(
        default=False,
        description=(
            "Incluye una vista previa truncada de chunks documentales en "
            "data.rag.citations para clientes UI autorizados."
        ),
    )


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceName] = Field(default_factory=list)
    reasoning: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
    fallbacks: list[str] = Field(
        default_factory=list,
        description="Mecanismos FALLBACK usados durante la ejecucion, visibles para auditoria.",
    )
    confidence: float | None = Field(default=None, ge=0, le=1)
    status: QueryStatus = "completed"
    data: dict | None = Field(
        default=None,
        description="Resumen publico de evidencias; no debe incluir filas raw ni objetos internos.",
    )
    failure_reason: str | None = None
