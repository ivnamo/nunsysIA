import re
from time import perf_counter

from pydantic import BaseModel, Field

from app.core.tracing import ToolCallTrace, ToolResult
from app.rag.embeddings import DeterministicEmbeddingModel, EmbeddingModel
from app.rag.vector_store import (
    DocumentVectorStore,
    InMemoryDocumentVectorStore,
    VectorStoreError,
)
from app.schemas.documents import DocumentRAGAnswer

_RAG_STOPWORDS = {
    "a",
    "al",
    "alguna",
    "con",
    "de",
    "del",
    "dice",
    "documento",
    "el",
    "en",
    "hay",
    "la",
    "las",
    "los",
    "pdf",
    "por",
    "que",
    "recomienda",
    "segun",
    "sobre",
    "un",
    "una",
}


class DocumentRAGInput(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)
    min_score: float = Field(default=0.2, ge=0, le=1)


class DocumentRAGTool:
    name = "DocumentRAGTool"

    def __init__(
        self,
        vector_store: DocumentVectorStore,
        embedding_model: EmbeddingModel | None = None,
    ) -> None:
        self._vector_store = vector_store
        self._embedding_model = embedding_model or DeterministicEmbeddingModel()
        self._fallbacks: list[str] = []
        if isinstance(self._vector_store, InMemoryDocumentVectorStore):
            self._add_fallback(
                "FALLBACK_VECTOR_STORE_IN_MEMORY: ChromaDB no disponible o no usado; retrieval en memoria del proceso."
            )
        if isinstance(self._embedding_model, DeterministicEmbeddingModel):
            self._add_fallback(
                "FALLBACK_EMBEDDINGS_DETERMINISTIC: embeddings locales deterministas; no se esta usando proveedor externo."
            )

    def query(self, tool_input: DocumentRAGInput) -> ToolResult:
        started_at = perf_counter()
        try:
            query_embedding = self._embedding_model.embed_query(tool_input.query)
            chunks = self._vector_store.similarity_search(
                query_embedding=query_embedding,
                top_k=tool_input.top_k,
            )
        except VectorStoreError as exc:
            return self._error_result(
                tool_input=tool_input,
                started_at=started_at,
                error=str(exc),
            )
        except Exception:
            return self._error_result(
                tool_input=tool_input,
                started_at=started_at,
                error="Error al generar embeddings o consultar documentos.",
            )

        relevant_chunks = [
            chunk
            for chunk in chunks
            if chunk.score >= tool_input.min_score
            and _has_query_evidence(tool_input.query, chunk.text)
        ]
        if not relevant_chunks:
            data = DocumentRAGAnswer(
                answer="No hay contexto documental suficiente para responder sin inventar.",
                status="insufficient_context",
                chunks=[],
                fallbacks=self._fallbacks,
            )
            return ToolResult(
                data=data.model_dump(mode="json"),
                tool_call=ToolCallTrace(
                    tool=self.name,
                    args=tool_input.model_dump(),
                    status="success",
                    output_summary="0 chunks relevantes recuperados",
                    duration_ms=self._duration_ms(started_at),
                    source="Documentos",
                ),
            )

        data = DocumentRAGAnswer(
            answer=self._build_grounded_answer(relevant_chunks),
            status="completed",
            chunks=relevant_chunks,
            fallbacks=self._fallbacks,
        )
        filenames = sorted({chunk.metadata.filename for chunk in relevant_chunks})
        fallback_marker = " [FALLBACK]" if self._fallbacks else ""
        return ToolResult(
            data=data.model_dump(mode="json"),
            tool_call=ToolCallTrace(
                tool=self.name,
                args=tool_input.model_dump(),
                status="success",
                output_summary=(
                    f"{fallback_marker} {len(relevant_chunks)} chunks recuperados de "
                    f"{', '.join(filenames)}"
                ).strip(),
                duration_ms=self._duration_ms(started_at),
                source="Documentos",
            ),
        )

    def _error_result(
        self,
        tool_input: DocumentRAGInput,
        started_at: float,
        error: str,
    ) -> ToolResult:
        return ToolResult(
            data=None,
            tool_call=ToolCallTrace(
                tool=self.name,
                args=tool_input.model_dump(),
                status="error",
                output_summary="Error al consultar documentos",
                error=error,
                duration_ms=self._duration_ms(started_at),
                source="Documentos",
            ),
        )

    @staticmethod
    def _build_grounded_answer(chunks: list) -> str:
        excerpts = [chunk.text for chunk in chunks]
        return " ".join(excerpts)

    @staticmethod
    def _duration_ms(started_at: float) -> int:
        return round((perf_counter() - started_at) * 1000)

    def _add_fallback(self, fallback: str) -> None:
        if fallback not in self._fallbacks:
            self._fallbacks.append(fallback)


def _has_query_evidence(query: str, text: str) -> bool:
    query_tokens = _meaningful_tokens(query)
    if not query_tokens:
        return False
    text_tokens = _meaningful_tokens(text)
    return bool(query_tokens & text_tokens)


def _meaningful_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if len(token) > 2 and token not in _RAG_STOPWORDS
    }
