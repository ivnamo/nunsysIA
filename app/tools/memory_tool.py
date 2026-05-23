import re
import time
from threading import Lock
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.tracing import ToolCallTrace, ToolResult
from app.schemas.query import QueryResponse


MAX_MEMORY_TURNS = 5


class MemoryRecallInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(min_length=1)
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    max_turns: int = Field(default=MAX_MEMORY_TURNS, ge=1, le=MAX_MEMORY_TURNS)


class ConversationMemoryStore:
    def __init__(self, max_turns: int = MAX_MEMORY_TURNS) -> None:
        self._max_turns = max_turns
        self._history_by_conversation: dict[str, list[dict[str, Any]]] = {}
        self._lock = Lock()

    def history(self, conversation_id: str | None) -> list[dict[str, Any]]:
        if not conversation_id:
            return []

        with self._lock:
            return [
                _copy_turn(turn)
                for turn in self._history_by_conversation.get(conversation_id, [])
            ]

    def remember(
        self,
        conversation_id: str | None,
        question: str,
        response: QueryResponse,
    ) -> None:
        if not conversation_id:
            return

        turn = {
            "question": _short_text(question, max_length=400),
            "answer": _short_text(response.answer, max_length=900),
            "status": response.status,
            "sources": list(response.sources),
            "data": response.data or {},
            "facts": _extract_facts(question, response),
        }

        with self._lock:
            history = self._history_by_conversation.setdefault(conversation_id, [])
            history.append(turn)
            del history[: max(0, len(history) - self._max_turns)]


class MemoryTool:
    name = "MemoryTool"

    def recall(self, tool_input: MemoryRecallInput) -> ToolResult:
        started_at = time.perf_counter()
        turns = [
            _public_turn(turn)
            for turn in tool_input.conversation_history[-tool_input.max_turns :]
        ]
        facts = _merge_facts(turns)
        status = "found" if turns else "empty"
        summary = (
            f"Memoria conversacional: {len(turns)} interacciones recuperadas"
            if turns
            else "Memoria conversacional: no hay interacciones previas"
        )
        return ToolResult(
            data={
                "status": status,
                "turns": turns,
                "facts": facts,
            },
            tool_call=ToolCallTrace(
                tool=self.name,
                action="recall",
                args={
                    "query": tool_input.query,
                    "max_turns": tool_input.max_turns,
                },
                status="success" if turns else "skipped",
                output_summary=summary,
                duration_ms=_duration_ms(started_at),
                source="Memoria",
            ),
        )


def _extract_facts(question: str, response: QueryResponse) -> dict[str, Any]:
    data = response.data or {}
    facts: dict[str, Any] = {
        "status": response.status,
        "sources": list(response.sources),
    }

    customer_id = _extract_customer_id(question) or _extract_customer_id(response.answer)
    if customer_id:
        facts["customer_id"] = customer_id

    order_ids = _extract_order_ids(data)
    if order_ids:
        facts["order_ids"] = order_ids

    rag = data.get("rag")
    if isinstance(rag, dict):
        documents = rag.get("documents")
        if isinstance(documents, list):
            facts["documents"] = [str(document) for document in documents]

    return facts


def _merge_facts(turns: list[dict[str, Any]]) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    latest_order_ids: list[int] = []
    documents: list[str] = []

    for turn in reversed(turns):
        turn_facts = turn.get("facts") or {}
        if not isinstance(turn_facts, dict):
            continue

        customer_id = turn_facts.get("customer_id")
        if customer_id and "customer_id" not in facts:
            facts["customer_id"] = str(customer_id)

        if not latest_order_ids:
            for order_id in turn_facts.get("order_ids", []):
                try:
                    normalized_order_id = int(order_id)
                except (TypeError, ValueError):
                    continue
                if normalized_order_id not in latest_order_ids:
                    latest_order_ids.append(normalized_order_id)

        for document in turn_facts.get("documents", []):
            document_name = str(document)
            if document_name not in documents:
                documents.append(document_name)

    if latest_order_ids:
        facts["order_ids"] = latest_order_ids
    if documents:
        facts["documents"] = documents

    return facts


def _extract_order_ids(data: dict[str, Any]) -> list[int]:
    order_ids: list[int] = []
    for key in ("erp_order_ids", "production_order_ids", "order_amount_order_ids"):
        values = data.get(key)
        if not isinstance(values, list):
            continue
        for value in values:
            try:
                order_id = int(value)
            except (TypeError, ValueError):
                continue
            if order_id not in order_ids:
                order_ids.append(order_id)
    return order_ids


def _extract_customer_id(text: str) -> str | None:
    matches = re.findall(r"\b[A-Z]{5}\b", text)
    return matches[0] if matches else None


def _public_turn(turn: dict[str, Any]) -> dict[str, Any]:
    return {
        "question": _short_text(str(turn.get("question") or ""), max_length=220),
        "answer": _short_text(str(turn.get("answer") or ""), max_length=500),
        "status": str(turn.get("status") or ""),
        "sources": [str(source) for source in turn.get("sources", [])],
        "facts": _copy_turn(turn.get("facts") if isinstance(turn.get("facts"), dict) else {}),
    }


def _copy_turn(turn: Any) -> dict[str, Any]:
    if not isinstance(turn, dict):
        return {}

    copied: dict[str, Any] = {}
    for key, value in turn.items():
        if isinstance(value, dict):
            copied[key] = _copy_turn(value)
        elif isinstance(value, list):
            copied[key] = [
                _copy_turn(item) if isinstance(item, dict) else item for item in value
            ]
        else:
            copied[key] = value
    return copied


def _short_text(value: str, max_length: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3].rstrip() + "..."


def _duration_ms(started_at: float) -> int:
    return max(0, int((time.perf_counter() - started_at) * 1000))
