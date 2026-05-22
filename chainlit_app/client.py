from pathlib import Path
from typing import Any

import httpx

from app.schemas.documents import DocumentListResponse, DocumentUploadResponse
from app.schemas.query import QueryResponse


class BackendClientError(RuntimeError):
    pass


class BackendClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport

    async def query(
        self,
        question: str,
        conversation_id: str | None = None,
        include_citation_previews: bool = False,
    ) -> QueryResponse:
        async with self._client() as client:
            response = await client.post(
                "/api/query",
                json={
                    "question": question,
                    "conversation_id": conversation_id,
                    "include_citation_previews": include_citation_previews,
                },
            )

        self._raise_for_status(response, "No se pudo procesar la consulta.")
        return QueryResponse.model_validate(response.json())

    async def upload_document(
        self,
        file_path: Path,
        filename: str,
    ) -> DocumentUploadResponse:
        async with self._client() as client:
            with file_path.open("rb") as file_handle:
                response = await client.post(
                    "/api/documents/upload",
                    files={
                        "file": (
                            filename,
                            file_handle,
                            "application/pdf",
                        )
                    },
                )

        self._raise_for_status(response, "No se pudo indexar el documento.")
        return DocumentUploadResponse.model_validate(response.json())

    async def list_documents(self) -> DocumentListResponse:
        async with self._client() as client:
            response = await client.get("/api/documents")

        self._raise_for_status(response, "No se pudo listar el espacio documental.")
        return DocumentListResponse.model_validate(response.json())

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            transport=self._transport,
        )

    @staticmethod
    def _raise_for_status(response: httpx.Response, fallback_message: str) -> None:
        if response.status_code < 400:
            return

        detail = _response_detail(response)
        raise BackendClientError(detail or fallback_message)


def _response_detail(response: httpx.Response) -> str | None:
    try:
        payload: dict[str, Any] = response.json()
    except ValueError:
        return response.text or None

    detail = payload.get("detail")
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        return "; ".join(str(item) for item in detail)
    return None
