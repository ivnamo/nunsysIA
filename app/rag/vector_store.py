import math
from collections import defaultdict
from pathlib import Path
from typing import Protocol

from app.schemas.documents import DocumentChunk, IndexedDocument, RetrievedDocumentChunk


class VectorStoreError(RuntimeError):
    pass


class DocumentVectorStore(Protocol):
    def add_chunks(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> None:
        ...

    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int,
        filenames: set[str] | None = None,
    ) -> list[RetrievedDocumentChunk]:
        ...

    def list_documents(self) -> list[IndexedDocument]:
        ...


class InMemoryDocumentVectorStore:
    def __init__(self) -> None:
        self._items: list[tuple[DocumentChunk, list[float]]] = []

    def add_chunks(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> None:
        self._items.extend(zip(chunks, embeddings, strict=True))

    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int,
        filenames: set[str] | None = None,
    ) -> list[RetrievedDocumentChunk]:
        normalized_filenames = _normalize_filenames(filenames)
        scored_chunks = [
            RetrievedDocumentChunk(
                text=chunk.text,
                metadata=chunk.metadata,
                score=_cosine_similarity(query_embedding, embedding),
            )
            for chunk, embedding in self._items
            if not normalized_filenames
            or chunk.metadata.filename.lower() in normalized_filenames
        ]
        return sorted(scored_chunks, key=lambda chunk: chunk.score, reverse=True)[:top_k]

    def list_documents(self) -> list[IndexedDocument]:
        grouped: dict[str, dict[str, object]] = defaultdict(
            lambda: {"filename": "", "uploaded_at": None, "chunks_indexed": 0}
        )
        for chunk, _ in self._items:
            document = grouped[chunk.metadata.document_id]
            document["filename"] = chunk.metadata.filename
            document["uploaded_at"] = chunk.metadata.uploaded_at
            document["chunks_indexed"] = int(document["chunks_indexed"]) + 1

        return [
            IndexedDocument(
                document_id=document_id,
                filename=str(values["filename"]),
                uploaded_at=values["uploaded_at"],
                chunks_indexed=int(values["chunks_indexed"]),
            )
            for document_id, values in sorted(grouped.items())
        ]


class ChromaDocumentVectorStore:
    def __init__(
        self,
        host: str,
        port: int,
        collection_name: str,
        mode: str = "http",
        persist_directory: str = "data/chroma",
    ) -> None:
        normalized_mode = mode.strip().lower()
        if normalized_mode not in {"http", "persistent"}:
            raise VectorStoreError(
                "Modo ChromaDB no soportado. Usa CHROMA_MODE=http o CHROMA_MODE=persistent."
            )

        try:
            import chromadb
        except ImportError as exc:
            raise VectorStoreError("chromadb no esta instalado.") from exc

        try:
            if normalized_mode == "persistent":
                persist_path = Path(persist_directory).resolve()
                persist_path.mkdir(parents=True, exist_ok=True)
                self._client = chromadb.PersistentClient(path=str(persist_path))
            else:
                self._client = chromadb.HttpClient(host=host, port=port)
            self._collection = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as exc:
            raise VectorStoreError("No se pudo conectar con ChromaDB.") from exc

    def add_chunks(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> None:
        try:
            self._collection.add(
                ids=[chunk.metadata.chunk_id for chunk in chunks],
                documents=[chunk.text for chunk in chunks],
                embeddings=embeddings,
                metadatas=[
                    chunk.metadata.model_dump(mode="json")
                    for chunk in chunks
                ],
            )
        except Exception as exc:
            raise VectorStoreError("No se pudieron indexar chunks en ChromaDB.") from exc

    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int,
        filenames: set[str] | None = None,
    ) -> list[RetrievedDocumentChunk]:
        where = _chroma_filename_filter(filenames or set())
        try:
            query_args = {
                "query_embeddings": [query_embedding],
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"],
            }
            if where:
                query_args["where"] = where
            result = self._collection.query(**query_args)
        except Exception as exc:
            raise VectorStoreError("No se pudo consultar ChromaDB.") from exc

        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        return [
            RetrievedDocumentChunk(
                text=document,
                metadata=metadata,
                score=max(0.0, 1.0 - float(distance)),
            )
            for document, metadata, distance in zip(documents, metadatas, distances, strict=True)
        ]

    def list_documents(self) -> list[IndexedDocument]:
        try:
            result = self._collection.get(include=["metadatas"])
        except Exception as exc:
            raise VectorStoreError("No se pudo listar documentos en ChromaDB.") from exc

        grouped: dict[str, dict[str, object]] = defaultdict(
            lambda: {"filename": "", "uploaded_at": None, "chunks_indexed": 0}
        )
        for metadata in result.get("metadatas", []):
            document = grouped[metadata["document_id"]]
            document["filename"] = metadata["filename"]
            document["uploaded_at"] = metadata["uploaded_at"]
            document["chunks_indexed"] = int(document["chunks_indexed"]) + 1

        return [
            IndexedDocument(
                document_id=document_id,
                filename=str(values["filename"]),
                uploaded_at=values["uploaded_at"],
                chunks_indexed=int(values["chunks_indexed"]),
            )
            for document_id, values in sorted(grouped.items())
        ]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _normalize_filenames(filenames: set[str] | None) -> set[str]:
    return {filename.lower() for filename in filenames or set() if filename}


def _chroma_filename_filter(filenames: set[str]) -> dict[str, object] | None:
    if not filenames:
        return None
    if len(filenames) == 1:
        return {"filename": next(iter(filenames))}
    return {"filename": {"$in": sorted(filenames)}}
