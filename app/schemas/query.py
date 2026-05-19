from typing import Literal

from pydantic import BaseModel, Field

from app.core.tracing import SourceName, ToolCallTrace


QueryStatus = Literal[
    "completed",
    "partial_answer",
    "insufficient_context",
    "tool_error",
    "failed",
    "unsupported",
]


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    conversation_id: str | None = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceName] = Field(default_factory=list)
    reasoning: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    status: QueryStatus
    data: dict | None = None
    failure_reason: str | None = None
