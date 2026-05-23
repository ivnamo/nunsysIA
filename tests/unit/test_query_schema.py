from app.schemas.query import QueryRequest


def test_query_request_leaves_mode_unset_when_omitted() -> None:
    request = QueryRequest(question="Que pedidos hay?")

    assert request.mode is None
