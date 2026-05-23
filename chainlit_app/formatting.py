from app.schemas.documents import DocumentListResponse, DocumentUploadResponse
from app.schemas.query import QueryResponse


def format_query_response(response: QueryResponse) -> str:
    sections = [response.answer]
    meta = _format_meta(response)
    if meta:
        sections.append(meta)

    if response.sources:
        sections.append("**Fuentes**\n" + "\n".join(f"- {source}" for source in response.sources))

    citations = _format_rag_citations(response)
    if citations:
        sections.append(citations)

    if response.reasoning:
        sections.append(
            "**Pasos ejecutados**\n"
            + "\n".join(f"{index}. {step}" for index, step in enumerate(response.reasoning, start=1))
        )

    if response.tool_calls:
        sections.append(
            "**Tool calls**\n"
            + "\n".join(
                f"- `{_tool_call_label(call)}` [{call.status}]: {call.output_summary or 'sin resumen'}"
                for call in response.tool_calls
            )
        )

    if response.fallbacks:
        sections.append(
            "**FALLBACKS**\n"
            + "\n".join(f"- `{fallback}`" for fallback in response.fallbacks)
        )

    if response.failure_reason:
        sections.append(f"**Motivo**\n{response.failure_reason}")

    return "\n\n".join(sections)


def format_upload_response(response: DocumentUploadResponse) -> str:
    content = (
        f"Documento indexado: `{response.filename}` "
        f"({response.chunks_indexed} chunks)."
    )
    if response.fallbacks:
        content += "\n\n**FALLBACKS**\n" + "\n".join(
            f"- `{fallback}`" for fallback in response.fallbacks
        )
    return content


def format_document_list(response: DocumentListResponse) -> str:
    if not response.documents:
        return "Espacio documental vacio."

    lines = [
        f"- `{document.filename}` ({document.chunks_indexed} chunks)"
        for document in response.documents
    ]
    content = "**Espacio documental**\n" + "\n".join(lines)
    if response.fallbacks:
        content += "\n\n**FALLBACKS**\n" + "\n".join(
            f"- `{fallback}`" for fallback in response.fallbacks
        )
    return content


def format_error(message: str) -> str:
    return f"No se pudo completar la operacion: {message}"


def _tool_call_label(call: object) -> str:
    tool = getattr(call, "tool", "")
    action = getattr(call, "action", None)
    return f"{tool}.{action}" if action else str(tool)


def _format_meta(response: QueryResponse) -> str | None:
    values = [f"Estado: `{response.status}`"]
    if response.confidence is not None:
        values.append(f"confianza: `{response.confidence:.2f}`")
    metadata = response.metadata or {}
    request_id = metadata.get("request_id")
    if request_id:
        values.append(f"request_id: `{request_id}`")
    duration_ms = metadata.get("duration_ms")
    if isinstance(duration_ms, int):
        values.append(f"duracion: `{duration_ms} ms`")
    return " | ".join(values) if values else None


def _format_rag_citations(response: QueryResponse) -> str | None:
    rag = (response.data or {}).get("rag") if response.data else None
    if not isinstance(rag, dict):
        return None

    citations = rag.get("citations")
    if not isinstance(citations, list) or not citations:
        return None

    lines = []
    for index, citation in enumerate(citations, start=1):
        if not isinstance(citation, dict):
            continue
        filename = citation.get("filename")
        page = citation.get("page")
        chunk_id = citation.get("chunk_id")
        score = citation.get("score")
        if filename is None or page is None or chunk_id is None or score is None:
            continue
        try:
            score_value = float(score)
        except (TypeError, ValueError):
            continue
        text_preview = str(citation.get("text_preview") or "").strip()
        view_text = f" - Ver texto: {citation_preview_label(index)}" if text_preview else ""
        lines.append(
            f"- `{filename}` - pagina `{page}` - chunk `{chunk_id}` - "
            f"score `{score_value:.4f}`{view_text}"
        )
    if not lines:
        return None
    return "**Citas documentales**\n" + "\n".join(lines)


def citation_preview_label(index: int) -> str:
    return f"Chunk {index}"
