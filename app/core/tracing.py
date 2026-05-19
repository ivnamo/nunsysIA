from typing import Any, Literal

from pydantic import BaseModel, Field


ToolCallStatus = Literal["success", "error", "skipped"]
SourceName = Literal["ERP", "Produccion", "Documentos", "Memoria"]


class ToolCallTrace(BaseModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    status: ToolCallStatus
    output_summary: str | None = None
    error: str | None = None
    duration_ms: int | None = None
    source: SourceName


class ToolResult(BaseModel):
    data: Any = None
    tool_call: ToolCallTrace
