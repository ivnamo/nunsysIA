import re


RAG_STOPWORDS = {
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


def has_query_evidence(query: str, text: str) -> bool:
    query_tokens = meaningful_tokens(query)
    if not query_tokens:
        return False
    text_tokens = meaningful_tokens(text)
    overlap = token_overlap(query_tokens, text_tokens)
    required_overlap = 2 if len(query_tokens) >= 3 else 1
    return len(overlap) >= required_overlap


def meaningful_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if len(token) > 2 and token not in RAG_STOPWORDS
    }


def token_overlap(query_tokens: set[str], text_tokens: set[str]) -> set[str]:
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
