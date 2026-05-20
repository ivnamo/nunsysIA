import time

from app.agents.final_response import FinalResponseBuilder


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChatModel:
    def __init__(self, content: str) -> None:
        self.content = content
        self.calls = 0
        self.last_input: object | None = None

    def invoke(self, input: object, **kwargs: object) -> _FakeMessage:
        self.calls += 1
        self.last_input = input
        return _FakeMessage(self.content)


class _SlowChatModel:
    def invoke(self, input: object, **kwargs: object) -> _FakeMessage:
        time.sleep(0.2)
        return _FakeMessage('{"answer": "Respuesta tardia"}')


class _ExplodingChatModel:
    def invoke(self, input: object, **kwargs: object) -> _FakeMessage:
        raise Exception("provider unavailable")


def test_final_response_uses_grounded_llm_answer_when_available() -> None:
    chat_model = _FakeChatModel(
        '{"answer": "El cliente ALFKI tiene 2 pedidos pendientes. '
        'El pedido 10248 esta en curso en produccion y el pedido 10252 '
        'esta bloqueado por Falta de material."}'
    )
    builder = FinalResponseBuilder(chat_model=chat_model)

    state = builder(_erp_production_state())

    assert chat_model.calls == 1
    assert state["response"].answer.startswith("El cliente ALFKI tiene 2 pedidos")
    assert "ERP pending" not in state["response"].answer
    assert state["response"].status == "completed"
    assert state["response"].fallbacks == []
    assert "Answer the user question from scratch" in str(chat_model.last_input)
    assert "safe_fallback_answer" in str(chat_model.last_input)


def test_final_response_falls_back_when_llm_adds_unsupported_number() -> None:
    chat_model = _FakeChatModel(
        '{"answer": "El cliente ALFKI tiene 3 pedidos pendientes."}'
    )
    builder = FinalResponseBuilder(chat_model=chat_model)

    state = builder(_erp_production_state())

    assert state["response"].answer == (
        "Pedidos del cliente ALFKI: 10248: ERP pendiente, produccion en curso; "
        "10252: ERP pendiente, produccion bloqueado (Falta de material)."
    )
    assert len(state["response"].fallbacks) == 1
    assert state["response"].fallbacks[0].startswith(
        "FALLBACK_FINAL_RESPONSE_DETERMINISTIC: LLM final no paso validacion de evidencias"
    )
    assert "numero no soportado: 3" in state["response"].fallbacks[0]


def test_final_response_allows_natural_wording_from_evidence() -> None:
    chat_model = _FakeChatModel(
        '{"answer": "El pedido 10252 esta pendiente y bloqueado por falta de material. '
        'No conviene prometer una fecha al cliente hasta resolver el bloqueo."}'
    )
    builder = FinalResponseBuilder(chat_model=chat_model)

    state = builder(_erp_production_state())

    assert state["response"].answer.startswith("El pedido 10252")
    assert "No conviene prometer" in state["response"].answer
    assert state["response"].fallbacks == []


def test_final_response_falls_back_when_llm_adds_unsupported_name() -> None:
    chat_model = _FakeChatModel(
        '{"answer": "Juan Perez debe revisar el pedido 10252 por falta de material."}'
    )
    builder = FinalResponseBuilder(chat_model=chat_model)

    state = builder(_erp_production_state())

    assert "Pedidos del cliente ALFKI" in state["response"].answer
    assert len(state["response"].fallbacks) == 1
    assert "nombre no soportado: juan perez" in state["response"].fallbacks[0]


def test_final_response_respects_dynamic_length_limit() -> None:
    long_answer = " ".join(["respuesta"] * 130)
    chat_model = _FakeChatModel(f'{{"answer": "{long_answer}"}}')
    builder = FinalResponseBuilder(chat_model=chat_model)

    state = builder(_erp_production_state())

    assert "Pedidos del cliente ALFKI" in state["response"].answer
    assert len(state["response"].fallbacks) == 1
    assert "excedio la longitud permitida" in state["response"].fallbacks[0]


def test_final_response_answers_rag_summary_with_llm_not_chunk_fallback() -> None:
    chat_model = _FakeChatModel(
        '{"answer": "El procedimiento define cuando una orden esta en curso, bloqueada, retrasada o finalizada. '
        'Tambien fija motivos habituales de bloqueo y escalado a operaciones tras 72 horas."}'
    )
    builder = FinalResponseBuilder(chat_model=chat_model)

    state = builder(_rag_summary_state())

    assert chat_model.calls == 1
    assert state["response"].answer.count(".") == 2
    assert "Tambien fija motivos" in state["response"].answer
    assert state["response"].fallbacks == []


def test_final_response_answers_mixed_penalties_with_llm() -> None:
    chat_model = _FakeChatModel(
        '{"answer": "Con la evidencia actual, el pedido 10252 no tiene penalizacion aplicable porque esta bloqueado por falta de material. '
        'El pedido 10301 queda pendiente de fecha real de entrega e imputabilidad, ya que consta retrasado por averia en linea de produccion."}'
    )
    builder = FinalResponseBuilder(chat_model=chat_model)

    state = builder(_mixed_penalty_state())

    assert state["response"].fallbacks == []
    assert "10252" in state["response"].answer
    assert "10301" in state["response"].answer
    assert "penalizacion" in state["response"].answer


def test_final_response_falls_back_when_llm_times_out() -> None:
    builder = FinalResponseBuilder(
        chat_model=_SlowChatModel(),
        llm_timeout_seconds=0.01,
    )

    state = builder(_erp_production_state())

    assert "Pedidos del cliente ALFKI" in state["response"].answer
    assert len(state["response"].fallbacks) == 1
    assert state["response"].fallbacks[0].startswith(
        "FALLBACK_FINAL_RESPONSE_DETERMINISTIC: LLM final fallo o no devolvio JSON valido"
    )
    assert "TimeoutError" in state["response"].fallbacks[0]


def test_final_response_falls_back_when_llm_provider_fails() -> None:
    builder = FinalResponseBuilder(chat_model=_ExplodingChatModel())

    state = builder(_erp_production_state())

    assert "Pedidos del cliente ALFKI" in state["response"].answer
    assert state["response"].status == "completed"
    assert len(state["response"].fallbacks) == 1
    assert state["response"].fallbacks[0].startswith(
        "FALLBACK_FINAL_RESPONSE_DETERMINISTIC: LLM final fallo"
    )
    assert "Exception" in state["response"].fallbacks[0]


def test_final_response_marks_fallback_when_llm_is_not_configured() -> None:
    builder = FinalResponseBuilder()

    state = builder(_erp_production_state())

    assert "Pedidos del cliente ALFKI" in state["response"].answer
    assert state["response"].fallbacks == [
        "FALLBACK_FINAL_RESPONSE_DETERMINISTIC: LLM final no configurado; respuesta construida por reglas."
    ]


def test_final_response_does_not_call_llm_for_insufficient_context() -> None:
    chat_model = _FakeChatModel('{"answer": "Invento una respuesta"}')
    builder = FinalResponseBuilder(chat_model=chat_model)

    state = builder(
        {
            "question": "Que dice el documento?",
            "plan": {
                "intent": "rag",
                "steps": [],
                "expected_sources": ["Documentos"],
                "answer_requirements": [],
            },
            "status": "insufficient_context",
            "data": {
                "rag": {
                    "answer": "No hay contexto documental suficiente para responder sin inventar.",
                    "status": "insufficient_context",
                    "chunks": [],
                }
            },
            "sources": [],
            "reasoning": [],
            "tool_calls": [],
        }
    )

    assert chat_model.calls == 0
    assert state["response"].answer == (
        "No hay contexto documental suficiente para responder sin inventar."
    )


def _erp_production_state() -> dict:
    return {
        "question": "Que pedidos pendientes tiene el cliente ALFKI y en que estado de produccion estan?",
        "plan": {
            "intent": "erp_production",
            "steps": [],
            "expected_sources": ["ERP", "Produccion"],
            "answer_requirements": [],
        },
        "status": "completed",
        "data": {
            "erp_orders": [
                {
                    "order_id": 10248,
                    "customer_id": "ALFKI",
                    "erp_status": "pending",
                },
                {
                    "order_id": 10252,
                    "customer_id": "ALFKI",
                    "erp_status": "pending",
                },
            ],
            "production_by_order": {
                10248: {
                    "order_id": 10248,
                    "production_status": "in_progress",
                    "blocked_reason": None,
                    "delay_reason": None,
                },
                10252: {
                    "order_id": 10252,
                    "production_status": "blocked",
                    "blocked_reason": "Falta de material",
                    "delay_reason": None,
                },
            },
        },
        "sources": ["ERP", "Produccion"],
        "reasoning": [
            "Consulta ERP de pedidos pendientes",
            "Consulta API de produccion para pedido 10248",
            "Consulta API de produccion para pedido 10252",
        ],
        "tool_calls": [],
    }


def _rag_summary_state() -> dict:
    return {
        "question": "resumeme en dos frases este documento: procedimiento_produccion_bloqueos.pdf",
        "plan": {
            "intent": "rag",
            "steps": [],
            "expected_sources": ["Documentos"],
            "answer_requirements": ["Responder solo con chunks documentales recuperados."],
        },
        "status": "completed",
        "data": {
            "rag": {
                "answer": (
                    "Una orden puede estar en in_progress, blocked, delayed o finished. "
                    "Un pedido bloqueado mas de 72 horas debe escalarse a operaciones."
                ),
                "status": "completed",
                "chunks": [
                    {
                        "text": (
                            "Procedimiento operativo de produccion. Una orden puede estar "
                            "en in_progress, blocked, delayed o finished. Un pedido "
                            "bloqueado mas de 72 horas debe escalarse a operaciones."
                        ),
                        "metadata": {
                            "document_id": "doc_1",
                            "filename": "procedimiento_produccion_bloqueos.pdf",
                            "page": 1,
                            "chunk_id": "doc_1_p1_c1",
                            "uploaded_at": "2026-05-20T00:00:00Z",
                        },
                        "score": 0.91,
                    }
                ],
            }
        },
        "sources": ["Documentos"],
        "reasoning": ["Consulta RAG documental con chunks recuperados"],
        "tool_calls": [],
    }


def _mixed_penalty_state() -> dict:
    state = _erp_production_state()
    state["question"] = (
        "en funcion de los pedidos y su estado dime que penalizaciones vamos a tener en cada uno"
    )
    state["plan"] = {
        "intent": "mixed",
        "steps": [],
        "expected_sources": ["ERP", "Produccion", "Documentos"],
        "answer_requirements": [
            "Devolver penalizacion aplicable por pedido usando ERP, produccion y normativa documental."
        ],
    }
    state["data"]["erp_orders"].append(
        {
            "order_id": 10301,
            "customer_id": "ANATR",
            "customer_name": "Ana Trujillo Emparedados",
            "erp_status": "pending",
        }
    )
    state["data"]["production_by_order"][10301] = {
        "order_id": 10301,
        "production_status": "delayed",
        "blocked_reason": None,
        "delay_reason": "Averia en linea de produccion",
    }
    state["data"]["rag"] = {
        "answer": (
            "No se aplican penalizaciones cuando el retraso procede de bloqueo "
            "de produccion, falta de material, falta de capacidad o averia de linea."
        ),
        "status": "completed",
        "chunks": [
            {
                "text": (
                    "No se aplican penalizaciones cuando el retraso procede de bloqueo "
                    "de produccion, falta de material, falta de capacidad o averia de linea."
                ),
                "metadata": {
                    "document_id": "doc_2",
                    "filename": "anexo_penalizaciones_sla.pdf",
                    "page": 1,
                    "chunk_id": "doc_2_p1_c1",
                    "uploaded_at": "2026-05-20T00:00:00Z",
                },
                "score": 0.89,
            }
        ],
    }
    state["sources"] = ["ERP", "Produccion", "Documentos"]
    return state
