from __future__ import annotations

from typing import Any


ANSWER_AUDITOR_SUBAGENT_NAME = "answer_auditor"


def build_answer_auditor_subagents(model: str) -> list[dict[str, Any]]:
    """Subagent DeepAgents sin acceso a fuentes externas para revisar respuestas."""
    return [
        {
            "name": ANSWER_AUDITOR_SUBAGENT_NAME,
            "description": (
                "Verifica que la respuesta final sea una respuesta de negocio "
                "limpia, no una traza interna, lista de TODOs, eco del prompt "
                "o salida de planificacion."
            ),
            "system_prompt": (
                "Eres auditor de respuesta para una POC empresarial. No tienes "
                "tools externas y no debes inventar datos. Tu tarea es revisar "
                "un borrador de respuesta junto con sus fuentes, pasos y tool "
                "calls visibles.\n\n"
                "Rechaza la respuesta si contiene listas internas de TODOs, "
                "frases como 'Updated todo list', estados 'in_progress' o "
                "'pending', eco del prompt, instrucciones internas, JSON no "
                "solicitado o texto que no responda a la pregunta de negocio.\n\n"
                "Devuelve una recomendacion breve: APROBADA si la respuesta es "
                "presentable para el usuario final; REPARAR si debe redactarse "
                "de nuevo con la evidencia disponible."
            ),
            "tools": [],
            "model": model,
        }
    ]


def answer_auditor_names() -> list[str]:
    return [ANSWER_AUDITOR_SUBAGENT_NAME]
