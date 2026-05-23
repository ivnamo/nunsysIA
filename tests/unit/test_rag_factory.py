import sys
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.core.llm import LLMProviderError
from app.rag.embeddings import DeterministicEmbeddingModel
from app.rag.factory import create_document_service


def test_document_service_scopes_chroma_collection_to_embedding_model(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            captured["client_kwargs"] = kwargs

        def get_or_create_collection(
            self,
            name: str,
            metadata: dict[str, str],
        ) -> object:
            captured["collection_name"] = name
            captured["collection_metadata"] = metadata
            return object()

    def http_client(host: str, port: int) -> FakeClient:
        return FakeClient(host=host, port=port)

    fake_chromadb = SimpleNamespace(HttpClient=http_client)
    monkeypatch.setitem(sys.modules, "chromadb", fake_chromadb)

    class FakeEmbeddingModel:
        model = "gemini-embedding-001"

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return [[0.1, 0.2] for _ in texts]

        def embed_query(self, text: str) -> list[float]:
            return [0.1, 0.2]

    monkeypatch.setattr(
        "app.rag.factory.create_embedding_model",
        lambda settings: FakeEmbeddingModel(),
    )

    service = create_document_service(
        Settings(
            chroma_mode="http",
            chroma_host="chromadb",
            chroma_port=8000,
            chroma_collection="documents",
            embedding_provider="gemini",
            gemini_api_key="test-key",
        )
    )

    assert type(service.vector_store).__name__ == "ChromaDocumentVectorStore"
    assert captured["collection_name"] == "documents_gemini_embedding_001"
    assert captured["collection_metadata"] == {"hnsw:space": "cosine"}


def test_document_service_rejects_deterministic_embeddings(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.rag.factory.create_embedding_model",
        lambda settings: DeterministicEmbeddingModel(),
    )

    with pytest.raises(LLMProviderError, match="embeddings reales"):
        create_document_service(Settings(embedding_provider="deterministic"))
