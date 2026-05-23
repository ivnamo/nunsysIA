from __future__ import annotations

from typing import Any

from app.schemas.query import QueryRequest


def _direct_tools_user_message(request: QueryRequest) -> str:
    return "\n".join(
        [
            f"Pregunta: {request.question}",
            f"conversation_id: {request.conversation_id or ''}",
            "Usa solo las tools disponibles para obtener datos antes de responder.",
            "Usa write_todos en consultas multi-fuente o con varios pasos.",
            "Si aparece una tool compuesta, usala antes que repetir primitives.",
            "No repitas consultas con los mismos argumentos.",
            "Si la pregunta es documental o contractual, haz una sola consulta documental.",
            "Si necesitas cruzar ERP y produccion, cruza por order_id.",
        ]
    )


def _document_context_for_agent(rag: Any) -> str:
    if not isinstance(rag, dict) or rag.get("status") != "completed":
        return ""
    chunks = rag.get("chunks")
    if not isinstance(chunks, list):
        return ""

    lines = []
    for index, chunk in enumerate(chunks[:3], start=1):
        if not isinstance(chunk, dict):
            continue
        text = str(chunk.get("text") or "").strip()
        if not text:
            continue
        metadata = chunk.get("metadata") or {}
        metadata = metadata if isinstance(metadata, dict) else {}
        filename = str(metadata.get("filename") or "documento")
        page = metadata.get("page")
        chunk_id = str(metadata.get("chunk_id") or f"chunk-{index}")
        text_preview = " ".join(text.split())[:900]
        lines.append(
            f"[{index}] {filename}, pagina {page}, {chunk_id}: {text_preview}"
        )
    return "\n".join(lines)


def _rag_retrieval_reasoning(rag: Any) -> str:
    if not isinstance(rag, dict):
        return "Consulta RAG documental para localizar evidencia verificable"
    chunks = _rag_chunks(rag)
    if rag.get("status") == "insufficient_context" or not chunks:
        return (
            "Consulta RAG documental para buscar evidencia; no se recuperan "
            "chunks relevantes suficientes"
        )
    return (
        "Consulta RAG documental para localizar evidencia verificable sobre "
        "la pregunta"
    )


def _rag_evidence_reasoning_steps(rag: Any) -> list[str]:
    if not isinstance(rag, dict):
        return []

    chunks = _rag_chunks(rag)
    if rag.get("status") == "insufficient_context" or not chunks:
        return [
            "Valida que no hay evidencia documental suficiente y evita completar con conocimiento del modelo",
        ]

    documents = _rag_document_names(chunks)
    document_label = ", ".join(documents[:3]) if documents else "documentos recuperados"
    if len(documents) > 3:
        document_label += f" y {len(documents) - 3} mas"

    return [
        (
            f"Selecciona {len(chunks)} chunk(s) relevante(s) de {document_label} "
            "como base de evidencia"
        ),
        (
            "Sintetiza la respuesta final usando solo el contexto recuperado "
            "y deja las citas documentales auditables en data.rag.citations"
        ),
    ]


def _rag_chunks(rag: dict[str, Any]) -> list[dict[str, Any]]:
    chunks = rag.get("chunks")
    if not isinstance(chunks, list):
        return []
    return [chunk for chunk in chunks if isinstance(chunk, dict)]


def _rag_document_names(chunks: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for chunk in chunks:
        metadata = chunk.get("metadata")
        if not isinstance(metadata, dict):
            continue
        filename = str(metadata.get("filename") or "").strip()
        if filename and filename not in names:
            names.append(filename)
    return names
