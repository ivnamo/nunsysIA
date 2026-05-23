from __future__ import annotations

import json


def _usable_document_agent_answer(answer: str | None) -> bool:
    if not isinstance(answer, str) or not answer.strip():
        return False
    normalized = answer.strip()
    if len(normalized.split()) < 8:
        return False
    lowered = normalized.lower()
    return not any(
        marker in lowered
        for marker in (
            "no tengo contexto",
            "no puedo responder",
            "sin informacion suficiente",
            "respuesta no determinista",
        )
    )


def _usable_business_agent_answer(answer: str | None) -> bool:
    if not isinstance(answer, str) or not answer.strip():
        return False
    normalized = answer.strip()
    if len(normalized.split()) < 4:
        return False
    lowered = normalized.lower()
    return not any(
        marker in lowered
        for marker in (
            "respuesta no determinista",
            "sin consultas para inspeccion",
            "updated todo list",
            "todo list",
            "write_todos",
            "in_progress",
            "'pending'",
            '"pending"',
            "pregunta:",
            "conversation_id:",
            "usa solo las tools",
            "no tengo contexto",
            "no puedo responder",
            "no hay informacion suficiente",
            "deep agents no genero",
        )
    )


def _agent_answer_from_text(text: str | None) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return None

    stripped = _strip_code_fence(text.strip())
    try:
        payload = json.loads(stripped)
    except ValueError:
        return text.strip()

    if isinstance(payload, dict) and isinstance(payload.get("answer"), str):
        return payload["answer"].strip() or None
    return text.strip()


def _strip_code_fence(text: str) -> str:
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if len(lines) >= 3 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return text
