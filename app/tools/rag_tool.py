from time import perf_counter

from pydantic import BaseModel, Field

from app.core.tracing import ToolCallTrace, ToolResult
from app.rag.embeddings import DeterministicEmbeddingModel
from app.rag.vector_store import DocumentVectorStore, VectorStoreError
from app.schemas.documents import DocumentRAGAnswer


class DocumentRAGInput(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)
    min_score: float = Field(default=0.2, ge=0, le=1)


class DocumentRAGTool:
    name = "DocumentRAGTool"

    def __init__(
        self,
        vector_store: DocumentVectorStore,
        embedding_model: DeterministicEmbeddingModel | None = None,
    ) -> None:
        self._vector_store = vector_store
        self._embedding_model = embedding_model or DeterministicEmbeddingModel()

    def query(self, tool_input: DocumentRAGInput) -> ToolResult:
        started_at = perf_counter()
        try:
            query_embedding = self._embedding_model.embed_query(tool_input.query)
            chunks = self._vector_store.similarity_search(
                query_embedding=query_embedding,
                top_k=tool_input.top_k,
            )
        except VectorStoreError as exc:
            return ToolResult(
                data=None,
                tool_call=ToolCallTrace(
                    tool=self.name,
                    args=tool_input.model_dump(),
                    status="error",
                    output_summary="Error al consultar documentos",
                    error=str(exc),
                    duration_ms=self._duration_ms(started_at),
                    source="Documentos",
                ),
            )

        relevant_chunks = [chunk for chunk in chunks if chunk.score >= tool_input.min_score]
        if not relevant_chunks:
            data = DocumentRAGAnswer(
                answer="No hay contexto documental suficiente para responder sin inventar.",
                status="insufficient_context",
                chunks=[],
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
        )
        filenames = sorted({chunk.metadata.filename for chunk in relevant_chunks})
        return ToolResult(
            data=data.model_dump(mode="json"),
            tool_call=ToolCallTrace(
                tool=self.name,
                args=tool_input.model_dump(),
                status="success",
                output_summary=(
                    f"{len(relevant_chunks)} chunks recuperados de "
                    f"{', '.join(filenames)}"
                ),
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
