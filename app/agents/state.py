from typing import Any, Literal, TypedDict

from app.core.tracing import ToolCallTrace
from app.schemas.query import QueryResponse


MAX_REPLANS = 2

AgentIntent = Literal[
    "erp",
    "production",
    "erp_production",
    "rag",
    "mixed",
    "conversation",
    "clarification",
    "unsupported",
]

WorkflowStatus = Literal[
    "planning",
    "executing",
    "validating",
    "completed",
    "partial_answer",
    "insufficient_context",
    "tool_error",
    "failed",
    "unsupported",
    "needs_clarification",
]

ValidationDecision = Literal["finish", "replan", "fail"]


class AgentState(TypedDict, total=False):
    question: str
    conversation_id: str | None
    conversation_history: list[dict[str, Any]]
    intent: AgentIntent | None
    plan: dict[str, Any] | None
    tool_results: list[dict[str, Any]]
    sources: list[str]
    reasoning: list[str]
    tool_calls: list[ToolCallTrace]
    fallbacks: list[str]
    attempts: int
    status: WorkflowStatus
    final_answer: str | None
    failure_reason: str | None
    confidence: float | None
    data: dict[str, Any]
    replan_history: list[dict[str, Any]]
    validation_decision: ValidationDecision
    response: QueryResponse
