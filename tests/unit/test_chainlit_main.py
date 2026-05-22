from app.schemas.query import QueryResponse
from chainlit_app.main import _citation_preview_elements


def test_citation_preview_elements_use_traceability_text_preview() -> None:
    response = QueryResponse(
        answer="Respuesta RAG.",
        status="completed",
        data={
            "rag": {
                "citations": [
                    {
                        "filename": "contrato.pdf",
                        "page": 2,
                        "chunk_id": "doc_123_p2_c1",
                        "score": 0.8123,
                        "text_preview": "Texto verificable del chunk.",
                    }
                ]
            }
        },
    )

    elements = _citation_preview_elements(response)

    assert len(elements) == 1
    assert elements[0].name == "Chunk 1"
    assert elements[0].display == "side"
    assert "contrato.pdf" in str(elements[0].content)
    assert "Texto verificable del chunk." in str(elements[0].content)

