import httpx
import pytest
from fastapi.testclient import TestClient

from app.agents.deep_agent import DeepAgentService
from app.agents.deepagents_tools_service import DeepAgentsToolsQueryService
from app.agents.router import AgentRouter
from app.api.routes_documents import get_document_service
from app.api.routes_query import get_agent_router
from app.core.config import get_settings
from app.erp.database import create_sqlite_connection, load_seed_sql
from app.erp.repositories import NorthwindRepository
from app.main import create_app
from app.production.client import ProductionAPIClient
from app.rag.embeddings import DeterministicEmbeddingModel
from app.rag.ingestion import DocumentIngestionService
from app.rag.vector_store import InMemoryDocumentVectorStore
from app.services.response_normalizer import ResponseNormalizer
from app.tools.erp_query_tool import ERPQueryTool
from app.tools.erp_tool import ERPTool
from app.tools.production_query_tool import ProductionQueryTool
from app.tools.production_tool import ProductionAPITool
from app.tools.rag_tool import DocumentRAGTool
from scripts.generate_sample_pdfs import SAMPLE_DOCUMENTS, build_pdf_bytes


@pytest.fixture()
def client() -> TestClient:
    app = create_app()
    vector_store = InMemoryDocumentVectorStore()
    embedding_model = DeterministicEmbeddingModel()
    document_service = DocumentIngestionService(
        vector_store=vector_store,
        embedding_model=embedding_model,
    )

    app.dependency_overrides[get_document_service] = lambda: document_service
    app.dependency_overrides[get_agent_router] = lambda: _agent_router(document_service)
    return TestClient(app)


def test_api_uploads_demo_document_space_and_answers_rag_questions(
    client: TestClient,
) -> None:
    filenames = [
        "contrato_marco_logistica_2026.pdf",
        "anexo_penalizaciones_sla.pdf",
        "procedimiento_produccion_bloqueos.pdf",
    ]

    for filename in filenames:
        response = client.post(
            "/api/documents/upload",
            files={
                "file": (
                    filename,
                    build_pdf_bytes(SAMPLE_DOCUMENTS[filename]),
                    "application/pdf",
                )
            },
        )
        assert response.status_code == 201
        assert response.json()["filename"] == filename

    list_response = client.get("/api/documents")

    assert list_response.status_code == 200
    indexed_names = {
        document["filename"] for document in list_response.json()["documents"]
    }
    assert indexed_names == set(filenames)

    penalty_response = client.post(
        "/api/query",
        json={"question": "Segun el PDF, hay alguna penalizacion por retrasos?"},
    )

    assert penalty_response.status_code == 200
    penalty_payload = penalty_response.json()
    assert penalty_payload["metadata"]["agent_mode"] == "deepagent"
    assert penalty_payload["sources"] == ["Documentos"]
    assert "penalizacion" in penalty_payload["answer"].lower()
    assert "anexo_penalizaciones_sla.pdf" in penalty_payload["data"]["rag"]["documents"]

    deadline_response = client.post(
        "/api/query",
        json={"question": "Que dice el documento sobre plazos de entrega standard?"},
    )

    assert deadline_response.status_code == 200
    deadline_payload = deadline_response.json()
    assert "5 dias laborables" in deadline_payload["answer"]
    assert "contrato_marco_logistica_2026.pdf" in deadline_payload["data"]["rag"]["documents"]


def test_api_returns_insufficient_context_for_unrelated_document_question(
    client: TestClient,
) -> None:
    for filename in [
        "contrato_marco_logistica_2026.pdf",
        "v2_procedimiento_produccion_bloqueos.pdf",
    ]:
        upload_response = client.post(
            "/api/documents/upload",
            files={
                "file": (
                    filename,
                    build_pdf_bytes(SAMPLE_DOCUMENTS[filename]),
                    "application/pdf",
                )
            },
        )
        assert upload_response.status_code == 201

    response = client.post(
        "/api/query",
        json={"question": "Segun el PDF, que receta de cocina vegana recomienda?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "insufficient_context"
    assert payload["sources"] == ["Documentos"]
    assert "documentos disponibles" in payload["answer"]


def _agent_router(document_service: DocumentIngestionService) -> AgentRouter:
    deepagent = DeepAgentService(
        DeepAgentsToolsQueryService(
            erp_tool=_erp_tool(),
            production_tool=_production_tool(),
            erp_query_tool=_erp_query_tool(),
            production_query_tool=_production_query_tool(),
            rag_tool=DocumentRAGTool(
                vector_store=document_service.vector_store,
                embedding_model=document_service.embedding_model,
            ),
            model=get_settings().deepagents_model,
            agent_builder=lambda **kwargs: _StaticAgent("Respuesta no determinista."),
        )
    )
    return AgentRouter(
        deepagent_service=deepagent,
        response_normalizer=ResponseNormalizer(),
    )


class _StaticAgent:
    def __init__(self, content: str) -> None:
        self._content = content

    def invoke(self, payload: dict) -> dict:
        return {"messages": [{"content": self._content}]}


def _erp_tool() -> ERPTool:
    connection = create_sqlite_connection(check_same_thread=False)
    load_seed_sql(connection)
    return ERPTool(NorthwindRepository(connection))


def _erp_query_tool() -> ERPQueryTool:
    connection = create_sqlite_connection(check_same_thread=False)
    load_seed_sql(connection)
    return ERPQueryTool(NorthwindRepository(connection))


def _production_tool() -> ProductionAPITool:
    return ProductionAPITool(_production_client())


def _production_query_tool() -> ProductionQueryTool:
    return ProductionQueryTool(_production_client())


def _production_client() -> ProductionAPIClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/production/orders":
            return httpx.Response(200, json={"orders": []})
        return httpx.Response(404, json={"detail": "Production order not found"})

    return ProductionAPIClient(
        base_url="http://production-api.test",
        transport=httpx.MockTransport(handler),
    )

