from typing import Any, Literal

from pydantic import BaseModel, Field

from app.agents.state import AgentIntent


PlanTool = Literal[
    "ERPTool",
    "ProductionAPITool",
    "ERPQueryTool",
    "ProductionQueryTool",
    "DocumentRAGTool",
    "MemoryTool",
]


class PlanStep(BaseModel):
    step_id: int
    tool: PlanTool
    action: str
    args: dict[str, Any] = Field(default_factory=dict)
    required: bool = True


class ExecutionPlan(BaseModel):
    intent: AgentIntent
    steps: list[PlanStep]
    expected_sources: list[str]
    answer_requirements: list[str] = Field(default_factory=list)
