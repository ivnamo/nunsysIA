from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ToolCallStatus = Literal["success", "error", "skipped"]
SourceName = Literal["ERP", "Produccion", "Documentos", "Memoria"]


class ToolCallTrace(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    tool: str = Field(min_length=1)
    action: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    status: ToolCallStatus
    output_summary: str | None = None
    error: str | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    source: SourceName


class ToolResult(BaseModel):
    data: Any = None
    tool_call: ToolCallTrace
