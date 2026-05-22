import sys
from types import SimpleNamespace

from app.core.config import Settings
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

    service = create_document_service(
        Settings(
            chroma_mode="http",
            chroma_host="chromadb",
            chroma_port=8000,
            chroma_collection="documents",
            embedding_provider="deterministic",
        )
    )

    assert type(service.vector_store).__name__ == "ChromaDocumentVectorStore"
    assert captured["collection_name"] == "documents_deterministic_128"
    assert captured["collection_metadata"] == {"hnsw:space": "cosine"}
