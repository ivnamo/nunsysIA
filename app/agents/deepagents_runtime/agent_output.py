from __future__ import annotations

from typing import Any, Callable


def _last_message_text(result: Any) -> str | None:
    messages = _mapping_value(result, "messages") or []
    for message in reversed(messages):
        content = _mapping_value(message, "content")
        text = _content_text(content)
        if text:
            return text
    return None


def _content_text(content: Any) -> str | None:
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


def _count_tool_calls(result: Any, tool_name: str) -> int:
    messages = _mapping_value(result, "messages") or []
    ai_tool_call_count = 0
    tool_message_count = 0
    for message in messages:
        for tool_call in _message_tool_calls(message):
            if _tool_call_name(tool_call) == tool_name:
                ai_tool_call_count += 1
        if _mapping_value(message, "name") == tool_name:
            tool_message_count += 1
    return ai_tool_call_count or tool_message_count


def _message_tool_calls(message: Any) -> list[Any]:
    tool_calls = _mapping_value(message, "tool_calls")
    if isinstance(tool_calls, list):
        return tool_calls
    additional_kwargs = _mapping_value(message, "additional_kwargs")
    if isinstance(additional_kwargs, dict) and isinstance(
        additional_kwargs.get("tool_calls"),
        list,
    ):
        return additional_kwargs["tool_calls"]
    content = _mapping_value(message, "content")
    if isinstance(content, list):
        return [
            item
            for item in content
            if isinstance(item, dict)
            and item.get("type") in {"tool_use", "tool_call"}
        ]
    return []


def _tool_call_name(tool_call: Any) -> str | None:
    name = _mapping_value(tool_call, "name")
    if isinstance(name, str):
        return name
    function = _mapping_value(tool_call, "function")
    if isinstance(function, dict) and isinstance(function.get("name"), str):
        return function["name"]
    return None


def _mapping_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _dedupe_tools(tools: list[Callable[..., Any]]) -> list[Callable[..., Any]]:
    deduped = []
    seen: set[str] = set()
    for tool in tools:
        name = tool.__name__
        if name in seen:
            continue
        seen.add(name)
        deduped.append(tool)
    return deduped
