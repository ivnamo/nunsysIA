import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.rag.vector_store import ChromaDocumentVectorStore, VectorStoreError


def test_chroma_vector_store_uses_persistent_client(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, client_type: str, **kwargs: object) -> None:
            captured["client_type"] = client_type
            captured["client_kwargs"] = kwargs

        def get_or_create_collection(
            self,
            name: str,
            metadata: dict[str, str],
        ) -> object:
            captured["collection_name"] = name
            captured["collection_metadata"] = metadata
            return object()

    def persistent_client(path: str) -> FakeClient:
        return FakeClient("persistent", path=path)

    fake_chromadb = SimpleNamespace(PersistentClient=persistent_client)
    monkeypatch.setitem(sys.modules, "chromadb", fake_chromadb)
    monkeypatch.setattr(Path, "mkdir", lambda *args, **kwargs: None)

    persist_directory = "data/chroma-test"

    ChromaDocumentVectorStore(
        mode="persistent",
        host="chromadb",
        port=8000,
        collection_name="documents",
        persist_directory=str(persist_directory),
    )

    assert captured["client_type"] == "persistent"
    assert captured["client_kwargs"] == {"path": str(Path(persist_directory).resolve())}
    assert captured["collection_name"] == "documents"
    assert captured["collection_metadata"] == {"hnsw:space": "cosine"}


def test_chroma_vector_store_rejects_unknown_mode() -> None:
    with pytest.raises(VectorStoreError) as exc_info:
        ChromaDocumentVectorStore(
            mode="sqlite",
            host="chromadb",
            port=8000,
            collection_name="documents",
        )

    assert "CHROMA_MODE=http" in str(exc_info.value)


def test_chroma_vector_store_deletes_matching_chunks(monkeypatch) -> None:
    deleted: list[str] = []

    class FakeCollection:
        def get(self, where: dict[str, str] | None = None):
            if where == {"filename": "contrato.pdf"}:
                return {"ids": ["chunk-1", "chunk-2"]}
            return {"ids": []}

        def delete(self, ids: list[str]) -> None:
            deleted.extend(ids)

    class FakeClient:
        def get_or_create_collection(self, name: str, metadata: dict[str, str]):
            return FakeCollection()

    fake_chromadb = SimpleNamespace(HttpClient=lambda host, port: FakeClient())
    monkeypatch.setitem(sys.modules, "chromadb", fake_chromadb)

    store = ChromaDocumentVectorStore(
        mode="http",
        host="chromadb",
        port=8000,
        collection_name="documents",
    )

    removed = store.delete_chunks(filename="contrato.pdf")

    assert removed == 2
    assert deleted == ["chunk-1", "chunk-2"]
