from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from app.agents.tools import source_for_tool
from app.core.tracing import SourceName, ToolCallTrace
from app.schemas.query import AgentMode, QueryResponse
from app.services.trace_service import TraceEvent, TraceService


class ResponseNormalizer:
    """Converts heterogeneous agent outputs into the public QueryResponse."""

    def __init__(self, trace_service: TraceService | None = None) -> None:
        self._trace_service = trace_service

    def normalize(self, raw_result: Any, mode: AgentMode) -> QueryResponse:
        response = self._coerce_query_response(raw_result)
        if response is None:
            response = self._build_minimal_response(raw_result)

        trace_events: list[TraceEvent] = []
        if self._trace_service:
            trace_events = self._trace_service.record_tool_calls(
                response.tool_calls,
                mode,
            )

        sources = list(response.sources) or _sources_from_tool_calls(response.tool_calls)
        reasoning = list(response.reasoning) or _reasoning_from_tool_calls(
            response.tool_calls
        )
        if not sources:
            sources = _sources_from_events(trace_events)
        if not reasoning:
            reasoning = _reasoning_from_events(trace_events)

        metadata = dict(response.metadata or {})
        metadata.setdefault("agent_mode", mode.value)
        metadata.setdefault("agent_framework", _framework_label(mode))
        if mode != AgentMode.DEEPAGENT:
            metadata.setdefault("experimental", True)

        return response.model_copy(
            update={
                "answer": str(response.answer or "").strip()
                or "No se pudo generar una respuesta final.",
                "sources": sources,
                "reasoning": reasoning,
                "metadata": metadata,
            }
        )

    def _coerce_query_response(self, value: Any) -> QueryResponse | None:
        if isinstance(value, QueryResponse):
            return value

        if isinstance(value, dict):
            try:
                return QueryResponse.model_validate(value)
            except ValidationError:
                pass

            for key in ("structured_response", "response", "output"):
                response = self._coerce_query_response(value.get(key))
                if response is not None:
                    return response

            message_response = self._coerce_query_response(_last_message_content(value))
            if message_response is not None:
                return message_response

        if isinstance(value, str):
            try:
                return self._coerce_query_response(json.loads(value))
            except json.JSONDecodeError:
                return None

        if isinstance(value, list):
            text = _text_from_content(value)
            if text:
                return self._coerce_query_response(text)

        return None

    def _build_minimal_response(self, raw_result: Any) -> QueryResponse:
        payload = raw_result if isinstance(raw_result, dict) else {}
        tool_calls = _tool_calls_from_payload(payload)
        return QueryResponse(
            answer=_answer_from_payload(raw_result),
            sources=_sources_from_tool_calls(tool_calls),
            reasoning=_reasoning_from_tool_calls(tool_calls),
            tool_calls=tool_calls,
            status="completed" if _answer_from_payload(raw_result) else "failed",
            data=None,
            failure_reason=None,
        )


def _framework_label(mode: AgentMode) -> str:
    if mode == AgentMode.DEEPAGENT:
        return "LangChain DeepAgents"
    if mode == AgentMode.DEEPAGENT_SIDECAR:
        return "LangChain DeepAgents sidecar"
    return "LangGraph legacy"


def _answer_from_payload(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if not isinstance(value, dict):
        return str(value).strip() if value is not None else ""

    for key in ("answer", "content", "output", "text"):
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

    content = _last_message_content(value)
    text = _text_from_content(content)
    return text or ""


def _last_message_content(value: dict[str, Any]) -> Any:
    messages = value.get("messages")
    if not isinstance(messages, list):
        return None
    for message in reversed(messages):
        content = _mapping_value(message, "content")
        if content:
            return content
    return None


def _text_from_content(content: Any) -> str | None:
    if isinstance(content, str):
        return content.strip() or None
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        text = "\n".join(part.strip() for part in parts if part.strip()).strip()
        return text or None
    return None


def _tool_calls_from_payload(payload: dict[str, Any]) -> list[ToolCallTrace]:
    raw_tool_calls = payload.get("tool_calls")
    if not isinstance(raw_tool_calls, list):
        raw_tool_calls = _message_tool_calls(payload)

    tool_calls = []
    for raw_tool_call in raw_tool_calls:
        call = _coerce_tool_call(raw_tool_call)
        if call is not None:
            tool_calls.append(call)
    return tool_calls


def _coerce_tool_call(value: Any) -> ToolCallTrace | None:
    if isinstance(value, ToolCallTrace):
        return value
    if not isinstance(value, dict):
        return None
    try:
        return ToolCallTrace.model_validate(value)
    except ValidationError:
        pass

    tool_name = _tool_call_name(value)
    if not tool_name:
        return None
    source = source_for_tool(tool_name)
    if source is None:
        return None
    return ToolCallTrace(
        tool=tool_name,
        action=tool_name,
        args=_tool_call_args(value),
        status="success",
        output_summary=None,
        source=source,
    )


def _message_tool_calls(payload: dict[str, Any]) -> list[Any]:
    calls = []
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return calls
    for message in messages:
        tool_calls = _mapping_value(message, "tool_calls")
        if isinstance(tool_calls, list):
            calls.extend(tool_calls)
        additional_kwargs = _mapping_value(message, "additional_kwargs")
        if isinstance(additional_kwargs, dict) and isinstance(
            additional_kwargs.get("tool_calls"),
            list,
        ):
            calls.extend(additional_kwargs["tool_calls"])
    return calls


def _sources_from_tool_calls(tool_calls: list[ToolCallTrace]) -> list[SourceName]:
    sources: list[SourceName] = []
    for call in tool_calls:
        if call.source not in sources:
            sources.append(call.source)
    return sources


def _sources_from_events(events: list[TraceEvent]) -> list[SourceName]:
    sources: list[SourceName] = []
    for event in events:
        if event.source not in sources:
            sources.append(event.source)
    return sources


def _reasoning_from_tool_calls(tool_calls: list[ToolCallTrace]) -> list[str]:
    reasoning = []
    for call in tool_calls:
        action = call.action or call.tool
        step = _public_reasoning_step(call.source, action)
        if step not in reasoning:
            reasoning.append(step)
    return reasoning


def _reasoning_from_events(events: list[TraceEvent]) -> list[str]:
    reasoning = []
    for event in events:
        label = event.output_summary or event.action
        if label and label not in reasoning:
            reasoning.append(label)
    return reasoning


def _public_reasoning_step(source: SourceName, action: str) -> str:
    if source == "ERP":
        return f"Consulta ERP para {action}"
    if source == "Produccion":
        return f"Consulta API de produccion para {action}"
    if source == "Documentos":
        return f"Consulta documentos mediante RAG para {action}"
    return f"Consulta memoria conversacional para {action}"


def _tool_call_name(tool_call: Any) -> str | None:
    name = _mapping_value(tool_call, "name")
    if isinstance(name, str):
        return name
    function = _mapping_value(tool_call, "function")
    if isinstance(function, dict) and isinstance(function.get("name"), str):
        return function["name"]
    return None


def _tool_call_args(tool_call: Any) -> dict[str, Any]:
    args = _mapping_value(tool_call, "args")
    if isinstance(args, dict):
        return args
    function = _mapping_value(tool_call, "function")
    if isinstance(function, dict):
        raw_arguments = function.get("arguments")
        if isinstance(raw_arguments, str):
            try:
                decoded = json.loads(raw_arguments)
            except json.JSONDecodeError:
                return {}
            return decoded if isinstance(decoded, dict) else {}
    return {}


def _mapping_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)
