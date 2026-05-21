import re
from collections.abc import Iterable

from app.rag.document_filters import is_document_wide_query, query_without_filenames
from app.rag.relevance import meaningful_tokens, token_overlap
from app.schemas.documents import RetrievedDocumentChunk


ANSWER_MAX_CHARS = 900
SENTENCE_COUNT_WORDS = {
    "una": 1,
    "un": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
}


def build_grounded_answer(query: str, chunks: list[RetrievedDocumentChunk]) -> str:
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
        query=query_without_filenames(query),
        sentences=sentences,
        max_sentences=3,
    )
    return _limit_answer(_naturalize_answer(" ".join(selected)))


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
        return SENTENCE_COUNT_WORDS[word_match.group(1)]

    if is_document_wide_query(query):
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
    query_tokens = meaningful_tokens(query)
    if not query_tokens:
        return sentences[:max_sentences]

    scored = []
    for index, sentence in enumerate(sentences):
        sentence_tokens = meaningful_tokens(sentence)
        overlap = token_overlap(query_tokens, sentence_tokens)
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
    if len(normalized) <= ANSWER_MAX_CHARS:
        return normalized

    sentences = _split_sentences(normalized)
    if max_sentences is not None:
        sentences = sentences[:max_sentences]

    limited = []
    current_length = 0
    for sentence in sentences:
        next_length = current_length + len(sentence) + (1 if limited else 0)
        if next_length > ANSWER_MAX_CHARS:
            break
        limited.append(sentence)
        current_length = next_length

    if limited:
        return " ".join(limited)
    return normalized[: ANSWER_MAX_CHARS - 3].rstrip() + "..."


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
