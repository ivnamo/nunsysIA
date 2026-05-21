import re
from collections.abc import Iterable
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
    "archivo",
    "con",
    "cual",
    "de",
    "del",
    "dice",
    "documento",
    "el",
    "este",
    "esta",
    "en",
    "frase",
    "frases",
    "hay",
    "la",
    "las",
    "los",
    "pdf",
    "por",
    "que",
    "recomienda",
    "resume",
    "resumir",
    "resumen",
    "resumeme",
    "segun",
    "sobre",
    "un",
    "una",
}
_ANSWER_MAX_CHARS = 900
_FILENAME_PATTERN = re.compile(r"[\w.-]+\.pdf", flags=re.IGNORECASE)
_SENTENCE_COUNT_WORDS = {
    "una": 1,
    "un": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
}


class DocumentRAGInput(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)
    min_score: float = Field(default=0.2, ge=0, le=1)
    filename: str | None = None


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
        requested_filenames = self._resolve_requested_filenames(
            _requested_filenames(tool_input.query, tool_input.filename)
        )
        evidence_query = _query_without_filenames(tool_input.query)
        document_wide_query = _is_document_wide_query(tool_input.query)
        try:
            query_embedding = self._embedding_model.embed_query(tool_input.query)
            chunks = self._vector_store.similarity_search(
                query_embedding=query_embedding,
                top_k=tool_input.top_k,
                filenames=requested_filenames or None,
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

        relevant_chunks = []
        for chunk in chunks:
            if chunk.score < tool_input.min_score:
                continue
            if requested_filenames and document_wide_query:
                relevant_chunks.append(chunk)
                continue
            if _has_query_evidence(evidence_query, chunk.text):
                relevant_chunks.append(chunk)
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
                    action="query",
                    args=tool_input.model_dump(),
                    status="success",
                    output_summary="0 chunks relevantes recuperados",
                    duration_ms=self._duration_ms(started_at),
                    source="Documentos",
                ),
            )

        data = DocumentRAGAnswer(
            answer=self._build_grounded_answer(tool_input.query, relevant_chunks),
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
                action="query",
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
                action="query",
                args=tool_input.model_dump(),
                status="error",
                output_summary="Error al consultar documentos",
                error=error,
                duration_ms=self._duration_ms(started_at),
                source="Documentos",
            ),
        )

    @staticmethod
    def _build_grounded_answer(query: str, chunks: list) -> str:
        sentences = _deduplicate_sentences(
            sentence
            for chunk in chunks
            for sentence in _split_sentences(chunk.text)
        )
        if not sentences:
            excerpts = [chunk.text for chunk in chunks]
            return _limit_answer(" ".join(excerpts))

        sentence_count = _requested_sentence_count(query)
        if sentence_count is not None:
            selected = _select_summary_sentences(sentences, sentence_count)
            return _limit_answer(
                _naturalize_answer(" ".join(selected)),
                max_sentences=sentence_count,
            )

        selected = _select_relevant_sentences(
            query=_query_without_filenames(query),
            sentences=sentences,
            max_sentences=3,
        )
        return _limit_answer(_naturalize_answer(" ".join(selected)))

    @staticmethod
    def _duration_ms(started_at: float) -> int:
        return round((perf_counter() - started_at) * 1000)

    def _add_fallback(self, fallback: str) -> None:
        if fallback not in self._fallbacks:
            self._fallbacks.append(fallback)

    def _resolve_requested_filenames(self, requested_filenames: set[str]) -> set[str]:
        if not requested_filenames:
            return set()
        try:
            indexed_documents = self._vector_store.list_documents()
        except Exception:
            return requested_filenames

        filenames_by_lower = {
            document.filename.lower(): document.filename
            for document in indexed_documents
        }
        return {
            filenames_by_lower.get(filename.lower(), filename)
            for filename in requested_filenames
        }


def _has_query_evidence(query: str, text: str) -> bool:
    query_tokens = _meaningful_tokens(query)
    if not query_tokens:
        return False
    text_tokens = _meaningful_tokens(text)
    overlap = _token_overlap(query_tokens, text_tokens)
    required_overlap = 2 if len(query_tokens) >= 3 else 1
    return len(overlap) >= required_overlap


def _meaningful_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if len(token) > 2 and token not in _RAG_STOPWORDS
    }


def _requested_filenames(query: str, explicit_filename: str | None = None) -> set[str]:
    filenames = set()
    if explicit_filename:
        filenames.add(explicit_filename.strip())
    filenames.update(
        match.group(0).strip(".,;:()[]{}")
        for match in _FILENAME_PATTERN.finditer(query)
    )
    return {filename for filename in filenames if filename}


def _query_without_filenames(query: str) -> str:
    return _FILENAME_PATTERN.sub(" ", query)


def _is_document_wide_query(query: str) -> bool:
    normalized = query.lower()
    if " sobre " in normalized or " acerca de " in normalized:
        return any(
            marker in normalized
            for marker in (
                "resume",
                "resumir",
                "resumen",
                "resumeme",
                "sintetiza",
            )
        )
    return any(
        marker in normalized
        for marker in (
            "resume",
            "resumir",
            "resumen",
            "resumeme",
            "sintetiza",
            "de que trata",
            "que dice este documento",
            "que dice el documento",
            "que dice el pdf",
        )
    )


def _requested_sentence_count(query: str) -> int | None:
    normalized = query.lower()
    digit_match = re.search(
        r"\b([1-5])\s+(?:frase|frases|oracion|oraciones)\b",
        normalized,
    )
    if digit_match:
        return int(digit_match.group(1))

    word_match = re.search(
        r"\b(una|un|dos|tres|cuatro|cinco)\s+(?:frase|frases|oracion|oraciones)\b",
        normalized,
    )
    if word_match:
        return _SENTENCE_COUNT_WORDS[word_match.group(1)]

    if _is_document_wide_query(query):
        return 2
    return None


def _split_sentences(text: str) -> list[str]:
    normalized = " ".join(text.split())
    raw_sentences = re.split(r"(?<=[.!?])\s+", normalized)
    sentences = []
    for raw_sentence in raw_sentences:
        sentence = _strip_section_heading(raw_sentence.strip())
        if len(sentence) < 20 or len(sentence.split()) < 5:
            continue
        sentences.append(sentence)
    return sentences


def _strip_section_heading(sentence: str) -> str:
    if ": " not in sentence:
        return sentence
    heading, rest = sentence.split(": ", 1)
    if 3 <= len(heading) <= 90 and len(rest) >= 20:
        return rest.strip()
    return sentence


def _deduplicate_sentences(sentences: Iterable[str]) -> list[str]:
    unique_sentences = []
    seen = set()
    for sentence in sentences:
        if not isinstance(sentence, str):
            continue
        normalized = " ".join(sentence.split())
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_sentences.append(normalized)
    return unique_sentences


def _select_summary_sentences(sentences: list[str], count: int) -> list[str]:
    if len(sentences) <= count:
        return sentences

    count = max(1, min(count, len(sentences)))
    if count == 1:
        return [sentences[0]]
    if count == 2:
        tail = _build_summary_tail(sentences[1:])
        if tail:
            return [sentences[0], tail]

    selected_indexes = {0, len(sentences) - 1}
    if count > 2:
        step = (len(sentences) - 1) / (count - 1)
        selected_indexes.update(round(index * step) for index in range(count))

    selected = [sentences[index] for index in sorted(selected_indexes)]
    return selected[:count]


def _build_summary_tail(sentences: list[str]) -> str | None:
    scored = []
    for index, sentence in enumerate(sentences):
        score = _summary_sentence_score(sentence)
        if score > 0:
            scored.append((score, -index, index))

    if not scored:
        return sentences[-1] if sentences else None

    selected_indexes = [
        index
        for _, _, index in sorted(scored, reverse=True)[:2]
    ]
    selected = [sentences[index] for index in sorted(selected_indexes)]
    return _join_clauses_as_sentence(selected)


def _summary_sentence_score(sentence: str) -> int:
    normalized = sentence.lower()
    score = 0
    for marker in ("motivo", "motivos", "debe", "escalar", "escala"):
        if marker in normalized:
            score += 3
    for marker in ("bloque", "retras", "falta", "material", "capacidad", "calidad"):
        if marker in normalized:
            score += 2
    for marker in ("cliente", "erp", "responsable", "fecha", "operaciones", "comercial"):
        if marker in normalized:
            score += 1
    return score


def _join_clauses_as_sentence(sentences: list[str]) -> str:
    clauses = [
        sentence.rstrip(".!?").strip()
        for sentence in sentences
        if sentence.strip()
    ]
    if not clauses:
        return ""
    joined = clauses[0]
    for clause in clauses[1:]:
        joined += "; " + clause[:1].lower() + clause[1:]
    return joined + "."


def _select_relevant_sentences(
    query: str,
    sentences: list[str],
    max_sentences: int,
) -> list[str]:
    query_tokens = _meaningful_tokens(query)
    if not query_tokens:
        return sentences[:max_sentences]

    scored = []
    for index, sentence in enumerate(sentences):
        sentence_tokens = _meaningful_tokens(sentence)
        overlap = _token_overlap(query_tokens, sentence_tokens)
        if not overlap:
            continue
        scored.append((len(overlap), -index, index))

    if not scored:
        return sentences[:max_sentences]

    selected_indexes = [
        index
        for _, _, index in sorted(scored, reverse=True)[:max_sentences]
    ]
    return [sentences[index] for index in sorted(selected_indexes)]


def _limit_answer(answer: str, max_sentences: int | None = None) -> str:
    normalized = " ".join(answer.split())
    if len(normalized) <= _ANSWER_MAX_CHARS:
        return normalized

    sentences = _split_sentences(normalized)
    if max_sentences is not None:
        sentences = sentences[:max_sentences]

    limited = []
    current_length = 0
    for sentence in sentences:
        next_length = current_length + len(sentence) + (1 if limited else 0)
        if next_length > _ANSWER_MAX_CHARS:
            break
        limited.append(sentence)
        current_length = next_length

    if limited:
        return " ".join(limited)
    return normalized[: _ANSWER_MAX_CHARS - 3].rstrip() + "..."


def _naturalize_answer(answer: str) -> str:
    replacements = (
        (
            "en in_progress, blocked, delayed o finished",
            "en curso, bloqueada, retrasada o finalizada",
        ),
        ("in_progress", "en curso"),
        ("blocked", "bloqueado"),
        ("delayed", "retrasado"),
        ("finished", "finalizado"),
    )
    naturalized = answer
    for source, target in replacements:
        naturalized = naturalized.replace(source, target)
    return naturalized


def _token_overlap(query_tokens: set[str], text_tokens: set[str]) -> set[str]:
    overlap = query_tokens & text_tokens
    for query_token in query_tokens - overlap:
        if len(query_token) < 5:
            continue
        for text_token in text_tokens:
            if len(text_token) >= 5 and (
                query_token in text_token or text_token in query_token
            ):
                overlap.add(query_token)
                break
    return overlap
