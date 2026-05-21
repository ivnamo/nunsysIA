import json
import re
import unicodedata
from typing import Any

from app.agents.state import AgentState


def extract_customer_id(question: str) -> str | None:
    explicit_customer = re.search(
        r"\bcliente\s+([A-Za-z]{5})\b",
        question,
        flags=re.IGNORECASE,
    )
    if explicit_customer:
        return explicit_customer.group(1).upper()
    matches = re.findall(r"\b[A-Z]{5}\b", question)
    return matches[0] if matches else None


def compact_history_for_prompt(state: AgentState) -> str:
    compact_history = []
    for turn in state.get("conversation_history", [])[-5:]:
        if not isinstance(turn, dict):
            continue
        compact_history.append(
            {
                "question": _short_text(str(turn.get("question") or ""), 180),
                "answer": _short_text(str(turn.get("answer") or ""), 240),
                "facts": turn.get("facts") if isinstance(turn.get("facts"), dict) else {},
            }
        )
    return json.dumps(compact_history, ensure_ascii=True)


def strip_accents(value: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFD", value)
        if unicodedata.category(character) != "Mn"
    )


def message_content(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    return str(content)


def extract_json_payload(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError("Planner LLM response did not include JSON.")
    payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("Planner LLM response JSON must be an object.")
    return payload


def bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def bounded_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def normalize_order_ids(value: Any) -> list[int]:
    values = value if isinstance(value, list) else [value]
    order_ids: list[int] = []
    for item in values:
        try:
            order_id = int(item)
        except (TypeError, ValueError):
            continue
        if order_id > 0 and order_id not in order_ids:
            order_ids.append(order_id)
    return order_ids


def _short_text(value: str, max_length: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3].rstrip() + "..."
