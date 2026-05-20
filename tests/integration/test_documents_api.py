import pytest
from fastapi.testclient import TestClient

from app.api.routes_documents import get_document_service
from app.main import create_app
from app.rag.ingestion import DocumentIngestionService
from app.rag.vector_store import InMemoryDocumentVectorStore


@pytest.fixture()
def client() -> TestClient:
    app = create_app()
    service = DocumentIngestionService(vector_store=InMemoryDocumentVectorStore())
    app.dependency_overrides[get_document_service] = lambda: service
    return TestClient(app)


def test_upload_document_indexes_pdf_and_list_documents(client: TestClient) -> None:
    response = client.post(
        "/api/documents/upload",
        files={
            "file": (
                "contrato.pdf",
                _pdf_bytes("Contrato marco con penalizacion por retrasos."),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["filename"] == "contrato.pdf"
    assert payload["status"] == "indexed"
    assert payload["chunks_indexed"] == 1

    list_response = client.get("/api/documents")

    assert list_response.status_code == 200
    assert list_response.json()["documents"][0]["document_id"] == payload["document_id"]


def test_upload_document_rejects_non_pdf_filename(client: TestClient) -> None:
    response = client.post(
        "/api/documents/upload",
        files={"file": ("notas.txt", b"texto plano", "text/plain")},
    )

    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


def _pdf_bytes(text: str) -> bytes:
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        b"5 0 obj << /Length "
        + str(len(stream)).encode()
        + b" >> stream\n"
        + stream
        + b"\nendstream endobj\n",
    ]
    body = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for pdf_object in objects:
        offsets.append(len(body))
        body.extend(pdf_object)
    xref = len(body)
    body.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    body.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        body.extend(f"{offset:010d} 00000 n \n".encode())
    body.extend(
        f"trailer << /Root 1 0 R /Size {len(objects) + 1} >>\n"
        f"startxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(body)
