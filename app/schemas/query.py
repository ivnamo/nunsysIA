from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.tracing import SourceName, ToolCallTrace


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


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceName] = Field(default_factory=list)
    reasoning: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
    fallbacks: list[str] = Field(
        default_factory=list,
        description="Mecanismos FALLBACK usados durante la ejecucion, visibles para auditoria.",
    )
    confidence: float | None = Field(default=None, ge=0, le=1)
    status: QueryStatus
    data: dict | None = Field(
        default=None,
        description="Resumen publico de evidencias; no debe incluir filas raw ni objetos internos.",
    )
    failure_reason: str | None = None
