from app.rag.relevance import has_query_evidence, meaningful_tokens


def test_meaningful_tokens_normalizes_spanish_accents() -> None:
    assert "logistica" in meaningful_tokens("Logística y producción")
    assert "produccion" in meaningful_tokens("Logística y producción")


def test_has_query_evidence_matches_accented_document_text() -> None:
    assert has_query_evidence(
        "logistica produccion",
        "La logística depende de la producción validada.",
    )
