import asyncio
import json
from pathlib import Path

import httpx
import pytest

from chainlit_app.client import BackendClient, BackendClientError


def test_backend_client_queries_api() -> None:
    async def run() -> None:
        client = BackendClient(
            base_url="http://backend.test",
            transport=httpx.MockTransport(handler),
        )

        response = await client.query(
            question="Que pedidos pendientes tiene ALFKI?",
            conversation_id="demo-001",
            mode="deepagent",
            include_citation_previews=True,
        )

        assert response.status == "completed"
        assert response.sources == ["ERP"]
        assert response.answer == "Respuesta ERP"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/query"
        payload = json.loads(request.read())
        assert payload["question"] == "Que pedidos pendientes tiene ALFKI?"
        assert payload["conversation_id"] == "demo-001"
        assert payload["mode"] == "deepagent"
        assert payload["include_citation_previews"] is True
        return httpx.Response(
            200,
            json={
                "answer": "Respuesta ERP",
                "sources": ["ERP"],
                "reasoning": ["Consulta ERP"],
                "tool_calls": [],
                "confidence": 0.9,
                "status": "completed",
            },
        )

    asyncio.run(run())


def test_backend_client_uploads_pdf() -> None:
    async def run() -> None:
        client = BackendClient(
            base_url="http://backend.test",
            transport=httpx.MockTransport(handler),
        )

        response = await client.upload_document(
            file_path=Path("tests/fixtures/sample_upload.pdf"),
            filename="contrato.pdf",
        )

        assert response.filename == "contrato.pdf"
        assert response.chunks_indexed == 2

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/documents/upload"
        assert "multipart/form-data" in request.headers["content-type"]
        return httpx.Response(
            201,
            json={
                "document_id": "doc_123",
                "filename": "contrato.pdf",
                "status": "indexed",
                "chunks_indexed": 2,
            },
        )

    asyncio.run(run())


def test_backend_client_lists_documents() -> None:
    async def run() -> None:
        client = BackendClient(
            base_url="http://backend.test",
            transport=httpx.MockTransport(handler),
        )

        response = await client.list_documents()

        assert len(response.documents) == 1
        assert response.documents[0].filename == "contrato.pdf"
        assert response.documents[0].chunks_indexed == 3

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/documents"
        return httpx.Response(
            200,
            json={
                "documents": [
                    {
                        "document_id": "doc_123",
                        "filename": "contrato.pdf",
                        "uploaded_at": "2026-05-20T10:00:00Z",
                        "chunks_indexed": 3,
                    }
                ]
            },
        )

    asyncio.run(run())


def test_backend_client_raises_controlled_error() -> None:
    async def run() -> None:
        client = BackendClient(
            base_url="http://backend.test",
            transport=httpx.MockTransport(handler),
        )

        with pytest.raises(BackendClientError, match="Backend caido"):
            await client.query(question="Que pedidos hay?")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "Backend caido"})

    asyncio.run(run())
