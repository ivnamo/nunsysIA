from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.core.tracing import SourceName, ToolCallTrace
from app.schemas.query import AgentMode


class TraceEvent(BaseModel):
    source: SourceName
    action: str
    input_summary: str | None = None
    output_summary: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    mode: AgentMode = AgentMode.DEEPAGENT


class TraceService:
    """In-memory trace collector used to enrich public response metadata."""

    def __init__(self) -> None:
        self._events: list[TraceEvent] = []

    def record(
        self,
        *,
        source: SourceName,
        action: str,
        mode: AgentMode,
        input_summary: str | None = None,
        output_summary: str | None = None,
    ) -> TraceEvent:
        event = TraceEvent(
            source=source,
            action=action,
            mode=mode,
            input_summary=input_summary,
            output_summary=output_summary,
        )
        self._events.append(event)
        return event

    def record_tool_call(
        self,
        tool_call: ToolCallTrace,
        mode: AgentMode,
    ) -> TraceEvent:
        return self.record(
            source=tool_call.source,
            action=tool_call.action or tool_call.tool,
            mode=mode,
            input_summary=_short_summary(tool_call.args),
            output_summary=tool_call.output_summary,
        )

    def record_tool_calls(
        self,
        tool_calls: list[ToolCallTrace],
        mode: AgentMode,
    ) -> list[TraceEvent]:
        events = []
        for tool_call in tool_calls:
            events.append(self.record_tool_call(tool_call, mode))
        return events

    def sources(self, mode: AgentMode | None = None) -> list[SourceName]:
        sources: list[SourceName] = []
        for event in self.events(mode):
            if event.source not in sources:
                sources.append(event.source)
        return sources

    def reasoning(self, mode: AgentMode | None = None) -> list[str]:
        steps = []
        for event in self.events(mode):
            label = event.output_summary or event.action
            if label and label not in steps:
                steps.append(label)
        return steps

    def events(self, mode: AgentMode | None = None) -> list[TraceEvent]:
        if mode is None:
            return list(self._events)
        return [event for event in self._events if event.mode == mode]


def _short_summary(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if len(text) <= 200 else text[:197].rstrip() + "..."
