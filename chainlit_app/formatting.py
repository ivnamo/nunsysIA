from app.schemas.documents import DocumentListResponse, DocumentUploadResponse
from app.schemas.query import QueryResponse


def format_query_response(response: QueryResponse) -> str:
    sections = [response.answer]
    meta = _format_meta(response)
    if meta:
        sections.append(meta)

    if response.sources:
        sections.append("**Fuentes**\n" + "\n".join(f"- {source}" for source in response.sources))

    if response.reasoning:
        sections.append(
            "**Pasos ejecutados**\n"
            + "\n".join(f"{index}. {step}" for index, step in enumerate(response.reasoning, start=1))
        )

    if response.tool_calls:
        sections.append(
            "**Tool calls**\n"
            + "\n".join(
                f"- `{call.tool}` [{call.status}]: {call.output_summary or 'sin resumen'}"
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


def _format_meta(response: QueryResponse) -> str | None:
    values = [f"Estado: `{response.status}`"]
    if response.confidence is not None:
        values.append(f"confianza: `{response.confidence:.2f}`")
    return " | ".join(values) if values else None
