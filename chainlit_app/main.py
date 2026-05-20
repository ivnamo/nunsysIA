from pathlib import Path
from uuid import uuid4

import chainlit as cl

from chainlit_app.client import BackendClient, BackendClientError
from chainlit_app.config import get_chainlit_settings
from chainlit_app.formatting import (
    format_document_list,
    format_error,
    format_query_response,
    format_upload_response,
)

_DOCUMENT_LIST_REQUESTS = {"/documentos", "documentos", "listar documentos"}


@cl.on_chat_start
async def on_chat_start() -> None:
    settings = get_chainlit_settings()
    cl.user_session.set("conversation_id", f"chainlit-{uuid4().hex[:12]}")
    cl.user_session.set(
        "backend_client",
        BackendClient(
            base_url=settings.backend_api_base_url,
            timeout=settings.backend_api_timeout_seconds,
        ),
    )
    await cl.Message(content="Listo para consultar la POC. Puedes adjuntar PDFs al espacio documental.").send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    client = _client()
    await _upload_pdf_attachments(client, message)

    question = message.content.strip()
    if not question:
        return

    if question.lower() in _DOCUMENT_LIST_REQUESTS:
        await _send_document_list(client)
        return

    response_message = cl.Message(content="Procesando consulta...")
    await response_message.send()

    try:
        response = await client.query(
            question=question,
            conversation_id=cl.user_session.get("conversation_id"),
        )
    except BackendClientError as exc:
        response_message.content = format_error(str(exc))
    else:
        response_message.content = format_query_response(response)

    await response_message.update()


def _client() -> BackendClient:
    client = cl.user_session.get("backend_client")
    if isinstance(client, BackendClient):
        return client

    settings = get_chainlit_settings()
    return BackendClient(
        base_url=settings.backend_api_base_url,
        timeout=settings.backend_api_timeout_seconds,
    )


async def _upload_pdf_attachments(
    client: BackendClient,
    message: cl.Message,
) -> None:
    for element in message.elements or []:
        path = getattr(element, "path", None)
        name = getattr(element, "name", None) or (Path(path).name if path else "")
        mime = getattr(element, "mime", None) or getattr(element, "type", None)
        if not path or not _is_pdf(name=name, mime=mime):
            continue

        try:
            response = await client.upload_document(Path(path), filename=name)
        except BackendClientError as exc:
            await cl.Message(content=format_error(str(exc))).send()
        else:
            await cl.Message(content=format_upload_response(response)).send()


async def _send_document_list(client: BackendClient) -> None:
    try:
        documents = await client.list_documents()
    except BackendClientError as exc:
        await cl.Message(content=format_error(str(exc))).send()
    else:
        await cl.Message(content=format_document_list(documents)).send()


def _is_pdf(name: str, mime: str | None) -> bool:
    return name.lower().endswith(".pdf") or mime == "application/pdf"
