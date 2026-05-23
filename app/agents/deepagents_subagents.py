from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any


def build_business_subagents(
    *,
    model: str,
    erp_tools: Sequence[Callable[..., Any]],
    production_tools: Sequence[Callable[..., Any]],
    document_tools: Sequence[Callable[..., Any]],
    memory_tools: Sequence[Callable[..., Any]],
) -> list[dict[str, Any]]:
    """Specialist DeepAgents used by the primary business orchestrator."""
    return [
        {
            "name": "erp_specialist",
            "description": (
                "Consulta ERP/Northwind para clientes, pedidos, importes y "
                "resumenes de negocio."
            ),
            "system_prompt": (
                "Eres especialista ERP. Usa solo tools ERP. Devuelve hechos "
                "verificables, IDs de pedido y resumen de entidades consultadas."
            ),
            "tools": list(erp_tools),
            "model": model,
        },
        {
            "name": "production_specialist",
            "description": (
                "Consulta la API REST de produccion para estados, bloqueos, "
                "retrasos y motivos operativos."
            ),
            "system_prompt": (
                "Eres especialista de produccion. Usa solo tools de produccion. "
                "No inventes estados ni motivos; cita order_id y estado operativo."
            ),
            "tools": list(production_tools),
            "model": model,
        },
        {
            "name": "document_rag_specialist",
            "description": (
                "Recupera evidencia documental en PDFs mediante RAG y ChromaDB."
            ),
            "system_prompt": (
                "Eres especialista RAG. Usa solo tools documentales. Responde "
                "solo con evidencia recuperada y conserva referencias de archivo, "
                "pagina y chunk."
            ),
            "tools": list(document_tools),
            "model": model,
        },
        {
            "name": "memory_specialist",
            "description": (
                "Resuelve referencias conversacionales usando memoria de la "
                "conversacion actual."
            ),
            "system_prompt": (
                "Eres especialista de memoria. Usa solo MemoryTool para recuperar "
                "hechos recientes; no sustituyas ERP, produccion ni documentos."
            ),
            "tools": list(memory_tools),
            "model": model,
        },
        {
            "name": "answer_auditor",
            "description": (
                "Revisa que la respuesta final tenga fuentes, pasos visibles y "
                "no afirme datos sin evidencia."
            ),
            "system_prompt": (
                "Eres auditor de respuesta. No consultes fuentes externas. "
                "Comprueba que answer, sources y reasoning esten alineados con "
                "las tool calls visibles y pide correccion si falta evidencia."
            ),
            "tools": [],
            "model": model,
        },
    ]


def subagent_names(subagents: Sequence[dict[str, Any]]) -> list[str]:
    return [str(subagent.get("name")) for subagent in subagents if subagent.get("name")]

